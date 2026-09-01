"""
Tools for graph routing and document grading.
"""

import logging
from typing import Literal

from langchain_core.prompts import PromptTemplate

from src.config.settings import Config
from src.llms.chat_model import llm, get_structured_output_kwargs
from src.models.state import State
from src.models.verification_result import VerificationResult

config = Config()
logger = logging.getLogger(__name__)


def routing_tool(state: State) -> Literal["retriever", "general_llm", "web_search"]:
    """
    Route the graph to the appropriate node based on query classification.

    Args:
        state (State): The current state of the graph.

    Returns:
        The next node to execute: "retriever", "general_llm", or "web_search".
    """
    if state["route"] == "index":
        return "retriever"
    elif state["route"] == "general":
        return "general_llm"
    else:
        return "web_search"


def doc_tool(state: State) -> Literal["rewrite", "generate"]:
    """
    Determine whether the query needs rewriting based on grading score.

    Falls through to "generate" if the rewrite loop has already run
    MAX_REWRITES times, regardless of the grade — prevents infinite loops
    when the retriever consistently returns low-relevance results.

    Args:
        state (State): The current state of the graph.

    Returns:
        The next node: "generate" if score is "yes" or max rewrites reached,
        otherwise "rewrite".
    """
    MAX_REWRITES = 3
    score = state["binary_score"]
    rewrite_count = state.get("rewrite_count") or 0

    if score == "yes":
        logger.info("doc_tool: score=yes → generate")
        return "generate"

    if rewrite_count >= MAX_REWRITES:
        logger.warning(
            "doc_tool: max rewrites (%d) reached, proceeding to generate",
            MAX_REWRITES,
        )
        return "generate"

    logger.info("doc_tool: score=%s, rewrite %d/%d → rewrite", score, rewrite_count + 1, MAX_REWRITES)
    return "rewrite"


def verify_answer(state: State) -> dict:
    """
    Verify whether the final answer is faithful to the retrieved context.

    Runs as a graph node (not a conditional edge) so it can update
    ``verify_count`` in the state.  The routing decision is read by
    ``verify_route`` from the ``verify_score`` field this node sets.

    Skips verification for the "general" route (no retrieved context to
    verify against) and for web-search answers (external content is
    authoritative by definition).

    Caps the verify → generate loop at MAX_VERIFICATIONS attempts to
    prevent infinite regeneration when the LLM cannot produce a faithful
    answer (mirrors the MAX_REWRITES guard in doc_tool).

    Args:
        state (State): The current state of the graph.

    Returns:
        dict: State update with ``verify_count`` and ``verify_score``.
    """
    MAX_VERIFICATIONS = 2

    route = state.get("route")
    if route in ("general", "search"):
        return {"verify_score": "yes"}

    verify_count = state.get("verify_count") or 0

    if verify_count >= MAX_VERIFICATIONS:
        logger.warning(
            "verify_answer: max verifications (%d) reached, accepting answer",
            MAX_VERIFICATIONS,
        )
        return {"verify_count": verify_count, "verify_score": "yes"}

    context = state.get("context") or ""
    final_answer = state["messages"][-1].content
    question = state["latest_query"]

    if not context:
        logger.warning("verify_answer: no context in state, skipping")
        return {"verify_count": verify_count, "verify_score": "yes"}

    verify_prompt = PromptTemplate(
        template=config.prompt("verify_prompt"),
        input_variables=["question", "context", "final_answer"]
    )
    llm_with_verification = llm.with_structured_output(
        VerificationResult, **get_structured_output_kwargs()
    )

    verify_chain = verify_prompt | llm_with_verification

    result = verify_chain.invoke({
        "question": question,
        "context": context,
        "final_answer": final_answer,
    })

    logger.info(
        "verify_answer: faithful=%s verification=%d/%d explanation=%s",
        result.faithful, verify_count + 1, MAX_VERIFICATIONS, result.explanation,
    )

    if result.faithful:
        return {"verify_count": verify_count + 1, "verify_score": "yes"}
    else:
        logger.info("Answer not faithful — regenerating (attempt %d/%d)", verify_count + 1, MAX_VERIFICATIONS)
        return {"verify_count": verify_count + 1, "verify_score": "no"}


def verify_route(state: State) -> Literal["__end__", "generate"]:
    """
    Route after verification: end if faithful, regenerate otherwise.

    Args:
        state (State): The current state (verify_score set by verify_answer).

    Returns:
        ``"__end__"`` when the answer was accepted, ``"generate"`` to retry.
    """
    if state.get("verify_score") == "yes":
        return "__end__"
    return "generate"
