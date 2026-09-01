"""
Graph builder module for the adaptive RAG system.
"""

import logging

from langchain_community.tools import TavilySearchResults
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langgraph.constants import START, END
from langgraph.graph.state import StateGraph

from src.config.settings import Config
from src.core.config import settings
from src.db.document_registry import get_document, list_documents
from src.llms.chat_model import llm, get_structured_output_kwargs
from src.models.grade import Grade
from src.models.route_identifier import RouteIdentifier
from src.models.state import State
from src.rag.reAct_agent import build_agent_executor, build_scoped_retriever_tool
from src.tools.graph_tools import routing_tool, doc_tool, verify_answer, verify_route

config = Config()
logger = logging.getLogger(__name__)

MAX_DESCRIPTION_CHARS_IN_PROMPT = 200


def format_document_list(documents: list[dict]) -> str:
    """
    Format the user's registered documents for the classifier prompt.

    Args:
        documents: Registry records for the requesting user.

    Returns:
        Numbered "id | filename | description" lines, or an empty marker.
    """
    if not documents:
        return "(no documents indexed)"
    return "\n".join(
        f"{index}. id={doc['doc_id']} | {doc['filename']} | "
        f"{(doc.get('description') or '')[:MAX_DESCRIPTION_CHARS_IN_PROMPT]}"
        for index, doc in enumerate(documents, start=1)
    )


# Node implementations
def query_classifier(state: State):
    """
    Classify the query and select which of the user's documents are relevant.

    Args:
        state (State): The current state of the graph.

    Returns:
        dict: Updated state with route, latest_query and doc_ids.
    """
    question = state["messages"][-1].content
    user_id = state.get("user_id") or ""

    documents = list_documents(user_id)
    classify_prompt = PromptTemplate(
        template=config.prompt("classify_prompt"),
        input_variables=["question", "documents"]
    )
    chain = classify_prompt | llm.with_structured_output(
        RouteIdentifier, **get_structured_output_kwargs()
    )
    result = chain.invoke({
        "question": question,
        "documents": format_document_list(documents),
    })

    # Only trust doc IDs that exist in this user's registry
    valid_ids = {doc["doc_id"] for doc in documents}
    doc_ids = [
        doc_id for doc_id in result.doc_ids if doc_id in valid_ids
    ][:settings.MAX_DOCS_PER_QUERY]

    route = result.route
    if route != "index":
        # Invariant: doc_ids are only meaningful for the index branch
        doc_ids = []
    elif not documents:
        # Nothing indexed: cannot answer from the index at all
        route = "search"
        doc_ids = []
    elif not doc_ids:
        # Classifier said "index" but named no valid doc; search all of
        # the user's docs so the grader still gets real material.
        doc_ids = [doc["doc_id"] for doc in documents][:settings.MAX_DOCS_PER_QUERY]

    logger.info("route=%s doc_ids=%s", route, doc_ids)
    return {
        "messages": state["messages"],
        "route": route,
        "latest_query": question,
        "doc_ids": doc_ids,
    }


def general_llm(state: State):
    """
    Fetch general common knowledge result from the LLM.

    Args:
        state (State): The current state of the graph.

    Returns:
        dict: Updated messages from LLM.
    """
    result = llm.invoke(state["messages"])
    logger.debug("general_llm response: %s", result)
    return {"messages": result}


def retriever_node(state: State):
    """
    Retrieve results from the user's selected documents via a fresh ReAct agent.

    Extracts chunk metadata from intermediate tool-call steps so the graph
    can carry source citations through to the frontend.

    Args:
        state (State): The current state of the graph.

    Returns:
        dict: Updated messages with tool calls and sources.
    """
    doc_ids = state.get("doc_ids") or []
    user_id = state.get("user_id") or ""

    if not doc_ids:
        return {
            "messages": [AIMessage(
                content="No relevant documents are indexed for your account yet."
            )]
        }

    descriptions = [
        (get_document(doc_id) or {}).get("description") or ""
        for doc_id in doc_ids
    ]

    try:
        tool = build_scoped_retriever_tool(user_id, doc_ids, descriptions)
        executor = build_agent_executor([tool])
        result = executor.invoke({"input": state["latest_query"]})
    except Exception as e:
        # Degrade gracefully instead of crashing the graph on Qdrant outages
        logger.exception("Document retrieval failed: %s", e)
        return {
            "messages": [AIMessage(
                content="Document retrieval is temporarily unavailable. "
                        "Please try again shortly."
            )]
        }

    # Extract tool calls and chunk metadata for source citations
    intermediate_steps = result.get("intermediate_steps", [])
    tool_calls = []
    sources = []
    seen_sources = set()

    if intermediate_steps:
        for action, tool_result in intermediate_steps:
            tool_calls.append({
                "tool": action.tool,
                "input": action.tool_input,
            })
            # tool_result is either a string or a list of Documents
            if isinstance(tool_result, list):
                for doc in tool_result:
                    if hasattr(doc, "metadata"):
                        meta = doc.metadata
                        # Deduplicate by (filename, page)
                        key = (meta.get("source", ""), meta.get("page"))
                        if key not in seen_sources:
                            seen_sources.add(key)
                            sources.append({
                                "filename": meta.get("source", "Unknown"),
                                "page": meta.get("page"),
                                "doc_id": meta.get("doc_id", ""),
                                "snippet": doc.page_content[:150] if doc.page_content else "",
                            })

    new_message = AIMessage(
        content=result["output"],
        additional_kwargs={"tool_calls": tool_calls},
    )

    return {
        "messages": [new_message],
        "sources": sources,
    }


def grade(state: State):
    """
    Grade the results retrieved from vector stores.

    Args:
        state (State): The current state of the graph.

    Returns:
        dict: Updated state with binary_score.
    """
    grading_prompt = PromptTemplate(
        template=config.prompt("grading_prompt"),
        input_variables=["question", "context"]
    )
    context = state["messages"][-1].content
    question = state["latest_query"]

    llm_with_grade = llm.with_structured_output(
        Grade, **get_structured_output_kwargs()
    )

    chain_graded = grading_prompt | llm_with_grade
    result = chain_graded.invoke({"question": question, "context": context})

    logger.debug("grade result: %s", result)
    return {"messages": state["messages"], "binary_score": result.binary_score}


def rewrite_query(state: State):
    """
    Rewrite the query to get better retrieval results.

    Args:
        state (State): State of the question.

    Returns:
        dict: Updated latest_query and incremented rewrite_count.
    """
    query = state["latest_query"]
    rewrite_count = state.get("rewrite_count") or 0

    rewrite_prompt = PromptTemplate(
        template=config.prompt("rewrite_prompt"),
        input_variables=["query"]
    )
    chain = rewrite_prompt | llm
    result = chain.invoke({"query": query})
    logger.debug("rewritten query: %s", result.content)

    return {
        "latest_query": result.content,
        "rewrite_count": rewrite_count + 1,
    }


def generate(state: State):
    """
    Generate the final answer for the user.

    Args:
        state (State): State of the question.

    Returns:
        dict: Generated response.
    """
    context = state["messages"][-1].content

    generate_prompt = PromptTemplate(
        template=config.prompt("generate_prompt"),
        input_variables=["context"]
    )

    generate_chain = generate_prompt | llm
    result = generate_chain.invoke({"context": context})

    return {
        "messages": [AIMessage(content=result.content)],
        "context": context,
    }


def web_search(state: State):
    """
    Search the web for the rewritten query.

    Args:
        state (State): The current state of the graph.

    Returns:
        dict: Search results as messages.
    """
    # Initialize the Tavily tool
    search_tool = TavilySearchResults()

    # Search a query
    result = search_tool.invoke(state["latest_query"])

    contents = [item["content"] for item in result if "content" in item]
    logger.debug("web_search results: %s", len(contents))

    return {
        "messages": [{"role": "assistant", "content": "\n\n".join(contents)}]
    }


# Build the graph
graph = StateGraph(State)

graph.add_node("query_analysis", query_classifier)
graph.add_node("retriever", retriever_node)
graph.add_node("grade", grade)
graph.add_node("generate", generate)
graph.add_node("rewrite", rewrite_query)
graph.add_node("web_search", web_search)
graph.add_node("general_llm", general_llm)

graph.add_node("verify", verify_answer)

graph.add_edge(START, "query_analysis")
graph.add_edge("web_search", "generate")
graph.add_edge("retriever", "grade")
graph.add_edge("rewrite", "retriever")
graph.add_conditional_edges("query_analysis", routing_tool)
graph.add_conditional_edges("grade", doc_tool)
graph.add_edge("generate", "verify")
graph.add_conditional_edges("verify", verify_route)
graph.add_edge("general_llm", END)

builder = graph.compile()
