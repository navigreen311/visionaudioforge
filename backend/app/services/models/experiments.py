"""Experiment tracking service for managing training experiments and epochs."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.experiment import Experiment, ExperimentEpoch


class ExperimentService:
    """Service for creating, tracking, and comparing ML experiments."""

    @staticmethod
    async def create_experiment(
        db: AsyncSession,
        name: str,
        config: dict[str, Any],
        model_id: uuid.UUID | None,
        workspace_id: uuid.UUID,
    ) -> Experiment:
        """Create a new experiment with status='created'."""
        experiment = Experiment(
            name=name,
            config=config or {},
            model_id=model_id,
            workspace_id=workspace_id,
            status="created",
        )
        db.add(experiment)
        await db.commit()
        await db.refresh(experiment)

        from app.models.notification import NotificationType
        from app.services.notifications.service import NotificationService

        await NotificationService.emit(
            db,
            experiment.workspace_id,
            NotificationType.model,
            title="Model training complete",
            description=(
                f"{experiment.name} finished"
                + (f" — best epoch {experiment.best_epoch}" if experiment.best_epoch else "")
            ),
            action_url="/train",
        )

        return experiment

    @staticmethod
    async def log_epoch(
        db: AsyncSession,
        experiment_id: uuid.UUID,
        epoch: int,
        metrics: dict[str, float],
    ) -> ExperimentEpoch:
        """Log metrics for a training epoch.

        On the first epoch, transitions experiment status to 'running'.
        Expected metrics keys: loss, val_loss, accuracy, val_accuracy.
        """
        epoch_record = ExperimentEpoch(
            experiment_id=experiment_id,
            epoch_number=epoch,
            train_loss=metrics.get("loss"),
            val_loss=metrics.get("val_loss"),
            accuracy=metrics.get("accuracy"),
            val_accuracy=metrics.get("val_accuracy"),
            metrics=metrics,
        )
        db.add(epoch_record)

        # Update experiment status to 'running' on first epoch
        result = await db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one()
        if experiment.status == "created":
            experiment.status = "running"

        await db.commit()
        await db.refresh(epoch_record)
        return epoch_record

    @staticmethod
    async def complete_experiment(
        db: AsyncSession,
        experiment_id: uuid.UUID,
    ) -> Experiment:
        """Mark experiment as completed and compute best epoch (lowest val_loss)."""
        result = await db.execute(
            select(Experiment)
            .options(selectinload(Experiment.epochs))
            .where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one()
        experiment.status = "completed"

        # Find best epoch by lowest val_loss
        epochs_with_val = [e for e in experiment.epochs if e.val_loss is not None]
        if epochs_with_val:
            best = min(epochs_with_val, key=lambda e: e.val_loss)
            experiment.best_epoch = best.epoch_number

        await db.commit()
        await db.refresh(experiment)
        return experiment

    @staticmethod
    async def fail_experiment(
        db: AsyncSession,
        experiment_id: uuid.UUID,
        error_msg: str,
    ) -> Experiment:
        """Mark experiment as failed with an error message."""
        result = await db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one()
        experiment.status = "failed"
        experiment.error_message = error_msg

        await db.commit()
        await db.refresh(experiment)
        return experiment

    @staticmethod
    async def get_experiment(
        db: AsyncSession,
        experiment_id: uuid.UUID,
    ) -> Experiment:
        """Get experiment with all epochs ordered by epoch number."""
        result = await db.execute(
            select(Experiment)
            .options(selectinload(Experiment.epochs))
            .where(Experiment.id == experiment_id)
        )
        return result.scalar_one()

    @staticmethod
    async def list_experiments(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        model_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Experiment], int]:
        """List experiments with optional model filter and pagination."""
        query = select(Experiment).where(Experiment.workspace_id == workspace_id)
        count_query = select(func.count()).select_from(Experiment).where(
            Experiment.workspace_id == workspace_id
        )

        if model_id is not None:
            query = query.where(Experiment.model_id == model_id)
            count_query = count_query.where(Experiment.model_id == model_id)

        query = query.order_by(Experiment.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        experiments = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return experiments, total

    @staticmethod
    async def get_best_checkpoint(
        db: AsyncSession,
        experiment_id: uuid.UUID,
        metric: str = "val_loss",
        mode: str = "min",
    ) -> dict[str, Any]:
        """Return the epoch data dict for the best checkpoint by a given metric."""
        result = await db.execute(
            select(ExperimentEpoch)
            .where(ExperimentEpoch.experiment_id == experiment_id)
        )
        epochs = list(result.scalars().all())

        if not epochs:
            return {}

        # Filter to epochs that have the metric
        valid_epochs = []
        for ep in epochs:
            value = getattr(ep, metric, None)
            if value is None and ep.metrics:
                value = ep.metrics.get(metric)
            if value is not None:
                valid_epochs.append((ep, value))

        if not valid_epochs:
            return {}

        if mode == "min":
            best_ep, best_val = min(valid_epochs, key=lambda x: x[1])
        else:
            best_ep, best_val = max(valid_epochs, key=lambda x: x[1])

        return {
            "epoch_number": best_ep.epoch_number,
            "metric": metric,
            "value": best_val,
            "train_loss": best_ep.train_loss,
            "val_loss": best_ep.val_loss,
            "accuracy": best_ep.accuracy,
            "val_accuracy": best_ep.val_accuracy,
            "metrics": best_ep.metrics,
        }

    @staticmethod
    async def compare_experiments(
        db: AsyncSession,
        experiment_ids: list[uuid.UUID],
    ) -> list[dict[str, Any]]:
        """Compare multiple experiments side-by-side with their best metrics."""
        summaries = []
        for exp_id in experiment_ids:
            result = await db.execute(
                select(Experiment)
                .options(selectinload(Experiment.epochs))
                .where(Experiment.id == exp_id)
            )
            experiment = result.scalar_one_or_none()
            if experiment is None:
                continue

            best_metrics: dict[str, Any] = {}
            if experiment.epochs:
                val_losses = [e.val_loss for e in experiment.epochs if e.val_loss is not None]
                accuracies = [e.accuracy for e in experiment.epochs if e.accuracy is not None]
                best_metrics["best_val_loss"] = min(val_losses) if val_losses else None
                best_metrics["best_accuracy"] = max(accuracies) if accuracies else None
                best_metrics["final_train_loss"] = experiment.epochs[-1].train_loss

            summaries.append({
                "id": str(experiment.id),
                "name": experiment.name,
                "status": experiment.status,
                "config": experiment.config,
                "total_epochs": len(experiment.epochs),
                "best_epoch": experiment.best_epoch,
                **best_metrics,
                "epochs": [
                    {
                        "epoch_number": e.epoch_number,
                        "train_loss": e.train_loss,
                        "val_loss": e.val_loss,
                        "accuracy": e.accuracy,
                        "val_accuracy": e.val_accuracy,
                    }
                    for e in experiment.epochs
                ],
            })

        return summaries
