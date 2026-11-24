async def run_chat(ctx, conversation_id: str, message: str) -> dict:
    """
    Fonction ARQ exécutée par un Worker.
    Le graph et son checkpointer sont initialisés au démarrage du Worker.
    """
    graph = ctx["graph"]

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config={
            "configurable": {
                "thread_id": conversation_id
            }
        },
    )

    response = result["messages"][-1].content

    return {
        "conversation_id": conversation_id,
        "response": response,
    }
