"""Celery tasks for model training / fine-tuning.

The task owns the experiment's terminal state. Previously a crash re-raised
into Celery and the experiment row stayed ``running`` forever, so the console
showed a job that would never finish and never failed.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.config import settings
from app.models.experiment import Experiment
from app.services.models.training import FinetuneConfig, TransferLearningService

logger = logging.getLogger(__name__)


def _session_factory() -> async_sessionmaker[AsyncSession]:
    """Build a session factory for this worker process."""
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(bind=True)
def run_finetune_task(self, config_dict: dict, experiment_id: str):
    """Run a fine-tuning job as a Celery background task.

    Parameters
    ----------
    config_dict : dict
        Serialized FinetuneConfig fields.
    experiment_id : str
        UUID string of the experiment to log epochs against.
    """
    logger.info(
        "Starting fine-tune task %s for experiment %s",
        self.request.id,
        experiment_id,
    )

    config = FinetuneConfig(**config_dict)
    service = TransferLearningService()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            service._run_training(config, uuid.UUID(experiment_id))
        )
    except Exception as exc:
        logger.exception("Fine-tune task failed: %s", exc)
        # Record the failure on the experiment before re-raising, so the row
        # the console polls reaches a terminal state instead of hanging at
        # "running" for good.
        try:
            loop.run_until_complete(_mark_failed(experiment_id, str(exc)))
        except Exception:  # noqa: BLE001
            logger.exception(
                "Could not mark experiment %s failed", experiment_id
            )
        raise
    finally:
        loop.close()

    logger.info("Fine-tune task %s completed", self.request.id)
    return {"status": "completed", "experiment_id": experiment_id}


async def _mark_failed(experiment_id: str, error: str) -> None:
    factory = _session_factory()
    async with factory() as db:
        result = await db.execute(
            select(Experiment).where(Experiment.id == uuid.UUID(experiment_id))
        )
        experiment = result.scalar_one_or_none()
        if experiment is None:
            return

        experiment.status = "failed"
        experiment.error_message = error[:1000]
        await db.commit()
