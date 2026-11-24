from contextlib import asynccontextmanager
from uuid import uuid4, UUID

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import (
    APP_NAME,
    DATABASE_URL,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    ARQ_QUEUE_NAME,
)
from app.graph import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = await create_pool(
        RedisSettings(
            host=REDIS_HOST,
            port=REDIS_PORT,
            database=REDIS_DB,
            password=REDIS_PASSWORD,
        ),
        default_queue_name=ARQ_QUEUE_NAME,
    )

    postgres_pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=5,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
        },
        open=False,
    )
    await postgres_pool.open(wait=True)

    # Initialise les tables de checkpoint LangGraph.
    # L'API démarre avant le Worker (voir depends_on dans compose.yaml).
    checkpointer = AsyncPostgresSaver(postgres_pool)
    await checkpointer.setup()

    app.state.redis = redis
    app.state.postgres_pool = postgres_pool
    app.state.graph = build_graph(checkpointer)

    try:
        yield
    finally:
        await redis.aclose()
        await postgres_pool.close()


app = FastAPI(title=APP_NAME, lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    conversation_id: UUID | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "service": APP_NAME}


@app.post("/chat", status_code=202)
async def chat(request: ChatRequest):
    conversation_id = str(request.conversation_id or uuid4())

    job = await app.state.redis.enqueue_job(
        "run_chat",
        conversation_id,
        request.message,
        _queue_name=ARQ_QUEUE_NAME,
    )

    if job is None:
        raise HTTPException(
            status_code=409,
            detail="Un job avec cet identifiant existe déjà.",
        )

    return {
        "job_id": job.job_id,
        "conversation_id": conversation_id,
        "status": "queued",
    }


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = Job(
        job_id=job_id,
        redis=app.state.redis,
        _queue_name=ARQ_QUEUE_NAME,
    )

    status = await job.status()

    if status.value == "not_found":
        raise HTTPException(status_code=404, detail="Job introuvable")

    response = {"job_id": job_id, "status": status.value}

    if status.value == "complete":
        response["result"] = await job.result(timeout=1)

    return response


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: UUID):
    config = {
        "configurable": {
            "thread_id": str(conversation_id)
        }
    }

    snapshot = await app.state.graph.aget_state(config)

    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail="Conversation introuvable",
        )

    messages = [
        {
            "type": message.type,
            "content": message.content,
        }
        for message in snapshot.values.get("messages", [])
    ]

    return {
        "conversation_id": str(conversation_id),
        "messages": messages,
    }
