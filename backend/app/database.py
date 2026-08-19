from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.tenancy import install_workspace_filter

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Confine every ORM read to the caller's workspace. Registered here rather than
# in main.py so that Celery workers and scripts get it too - anything that builds
# a session from this factory is scoped, not just HTTP requests.
# See app/core/tenancy.py for what it does and does not cover.
install_workspace_filter(AsyncSession.sync_session_class)


async def get_async_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


def get_pool_stats() -> dict:
    """Return current connection pool statistics.

    Not every pool implementation reports these — NullPool, which holds no
    connections at all, has none of them. Report null rather than raising, so a
    diagnostics endpoint does not 500 because of how the engine is configured.
    """
    pool = engine.pool

    def _stat(name: str):
        getter = getattr(pool, name, None)
        if getter is None:
            return None
        try:
            return getter()
        except Exception:
            return None

    return {
        "pool_size": _stat("size"),
        "checked_out": _stat("checkedout"),
        "overflow": _stat("overflow"),
    }
