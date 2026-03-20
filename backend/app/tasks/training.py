"""Celery tasks for model training / fine-tuning."""

import asyncio
import logging

from app.celery_app import celery_app
from app.services.models.training import FinetuneConfig, TransferLearningService

logger = logging.getLogger(__name__)


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
    import uuid

    logger.info("Starting fine-tune task %s for experiment %s", self.request.id, experiment_id)

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
        raise
    finally:
        loop.close()

    logger.info("Fine-tune task %s completed", self.request.id)
    return {"status": "completed", "experiment_id": experiment_id}
