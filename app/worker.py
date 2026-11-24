from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from arq.connections import RedisSettings

from app.config import (
    DATABASE_URL,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    ARQ_QUEUE_NAME,
    JOB_TIMEOUT_SECONDS,
    MAX_WORKER_JOBS,
)
from app.graph import build_graph
from app.tasks import run_chat


async def startup(ctx):
    # Chaque processus Worker possède son propre pool PostgreSQL.
    pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=5,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
        },
        open=False,
    )
    await pool.open(wait=True)

    checkpointer = AsyncPostgresSaver(pool)
    ctx["postgres_pool"] = pool
    ctx["graph"] = build_graph(checkpointer)


async def shutdown(ctx):
    pool = ctx.get("postgres_pool")
    if pool:
        await pool.close()


class WorkerSettings:
    functions = [run_chat]
    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings(
        host=REDIS_HOST,
        port=REDIS_PORT,
        database=REDIS_DB,
        password=REDIS_PASSWORD,
    )
    queue_name = ARQ_QUEUE_NAME
    max_jobs = MAX_WORKER_JOBS
    job_timeout = JOB_TIMEOUT_SECONDS
    keep_result = 3600
