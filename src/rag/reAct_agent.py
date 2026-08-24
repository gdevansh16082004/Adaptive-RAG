"""
Tool-calling agent factory for document retrieval.

The executor is built per query inside retriever_node because the retriever
tool is scoped to the documents selected during query classification.

Uses native LLM tool calling (create_tool_calling_agent) rather than the
legacy text-format ReAct loop: models like gpt-oss on Groq follow the
Thought/Action/Action Input text protocol unreliably, and Groq aborts
streams whose content resembles an unregistered tool call.
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

from src.config.settings import Config
from src.llms.chat_model import llm

config = Config()

AGENT_MAX_ITERATIONS = 2
MAX_TOOL_DESCRIPTION_CHARS = 200

prompt = ChatPromptTemplate.from_messages([
    ("system", config.prompt("system_prompt")),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])


def build_tool_description(descriptions: list[str]) -> str:
    """
    Build the retriever tool instruction from the in-scope documents.

    Args:
        descriptions: Enhanced descriptions of the selected documents.

    Returns:
        Instruction string, truncated per document to bound prompt size.
    """
    trimmed = [
        f"- {(description or '')[:MAX_TOOL_DESCRIPTION_CHARS]}"
        for description in descriptions
    ]
    joined = "\n".join(trimmed) if trimmed else "- the user's uploaded documents"
    return (
        "Use this tool **only** to answer questions about the user's "
        f"indexed documents:\n{joined}\n"
    )


def build_scoped_retriever_tool(
    user_id: str,
    doc_ids: list[str],
    descriptions: list[str],
) -> BaseTool:
    """
    Build a retriever tool filtered to a user's selected documents.

    Args:
        user_id: Owning user applied as a payload filter.
        doc_ids: Document IDs applied as a MatchAny payload filter.
        descriptions: Descriptions used in the tool instruction.

    Returns:
        A LangChain Tool wrapping the scoped retriever.
    """
    from src.rag.retriever_setup import build_retriever, build_retriever_tool

    retriever = build_retriever(user_id, doc_ids)
    return build_retriever_tool(retriever, build_tool_description(descriptions))


def build_agent_executor(tools: list[BaseTool]) -> AgentExecutor:
    """
    Create a tool-calling AgentExecutor over the provided tools.

    Args:
        tools: Tools available to the agent (exactly one retrieval tool today).

    Returns:
        A configured AgentExecutor instance.
    """
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        handle_parsing_errors=True,
        max_iterations=AGENT_MAX_ITERATIONS,
        verbose=True,
        return_intermediate_steps=True,
    )
