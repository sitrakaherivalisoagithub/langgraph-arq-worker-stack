from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, AnyMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    # add_messages ajoute les nouveaux messages à l'historique du thread.
    messages: Annotated[list[AnyMessage], add_messages]
    user_text: str


async def prepare_message(state: ChatState) -> dict:
    """Récupère le dernier message utilisateur."""
    last_message = state["messages"][-1]
    return {"user_text": str(last_message.content)}


async def generate_response(state: ChatState) -> dict:
    """Réponse fictive : aucun appel à un LLM."""
    return {
        "messages": [
            AIMessage(content=f"Bien reçu : {state['user_text']}")
        ]
    }


def build_graph(checkpointer):
    builder = StateGraph(ChatState)

    builder.add_node("prepare_message", prepare_message)
    builder.add_node("generate_response", generate_response)

    builder.add_edge(START, "prepare_message")
    builder.add_edge("prepare_message", "generate_response")
    builder.add_edge("generate_response", END)

    return builder.compile(checkpointer=checkpointer)
