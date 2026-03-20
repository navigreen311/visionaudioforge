"""Transfer learning / fine-tuning service using PyTorch."""

import asyncio
import logging
import uuid
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)


@dataclass
class FinetuneConfig:
    """Configuration for a fine-tuning job."""

    backbone: str  # "resnet18" or "resnet50"
    dataset_path: str
    num_epochs: int = 10
    learning_rate: float = 1e-3
    batch_size: int = 32
    freeze_layers: bool = True
    gradient_clip_value: float | None = None
    early_stopping_patience: int | None = None
    num_classes: int = 10  # default for synthetic data


class TransferLearningService:
    """Manages fine-tuning of pretrained vision models."""

    async def start_finetune(self, config: FinetuneConfig) -> str:
        """Queue a fine-tune job and return the job_id."""
        job_id = str(uuid.uuid4())
        logger.info("Queued fine-tune job %s with backbone=%s", job_id, config.backbone)
        return job_id

    def _build_model(self, config: FinetuneConfig) -> nn.Module:
        """Load a pretrained backbone and replace the classifier head."""
        import torchvision.models as models

        if config.backbone == "resnet50":
            model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        else:
            model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)

        if config.freeze_layers:
            for param in model.parameters():
                param.requires_grad = False

        # Replace final classifier for target num_classes
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, config.num_classes)

        return model

    def _create_synthetic_data(
        self, config: FinetuneConfig
    ) -> tuple[DataLoader, DataLoader]:
        """Create synthetic train/val dataloaders for V1 (no real dataset required)."""
        num_train = 256
        num_val = 64

        # Synthetic image tensors (3x224x224) and random labels
        train_x = torch.randn(num_train, 3, 224, 224)
        train_y = torch.randint(0, config.num_classes, (num_train,))
        val_x = torch.randn(num_val, 3, 224, 224)
        val_y = torch.randint(0, config.num_classes, (num_val,))

        train_loader = DataLoader(
            TensorDataset(train_x, train_y),
            batch_size=config.batch_size,
            shuffle=True,
        )
        val_loader = DataLoader(
            TensorDataset(val_x, val_y),
            batch_size=config.batch_size,
            shuffle=False,
        )
        return train_loader, val_loader

    async def _run_training(
        self,
        config: FinetuneConfig,
        experiment_id: uuid.UUID,
    ) -> None:
        """Execute the training loop (real PyTorch, synthetic data for V1).

        Logs each epoch to ExperimentService and marks experiment complete/failed.
        """
        from app.database import async_session_factory
        from app.services.models.experiments import ExperimentService

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = self._build_model(config)
        model = model.to(device)

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=config.learning_rate,
        )

        train_loader, val_loader = self._create_synthetic_data(config)

        best_val_loss = float("inf")
        patience_counter = 0

        try:
            for epoch in range(1, config.num_epochs + 1):
                # --- Training phase ---
                model.train()
                running_loss = 0.0
                correct = 0
                total = 0

                for batch_x, batch_y in train_loader:
                    batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                    optimizer.zero_grad()
                    outputs = model(batch_x)
                    loss = criterion(outputs, batch_y)
                    loss.backward()

                    if config.gradient_clip_value is not None:
                        torch.nn.utils.clip_grad_norm_(
                            model.parameters(), config.gradient_clip_value
                        )

                    optimizer.step()

                    running_loss += loss.item() * batch_x.size(0)
                    _, predicted = outputs.max(1)
                    total += batch_y.size(0)
                    correct += predicted.eq(batch_y).sum().item()

                train_loss = running_loss / total
                train_accuracy = correct / total

                # --- Validation phase ---
                model.eval()
                val_running_loss = 0.0
                val_correct = 0
                val_total = 0

                with torch.no_grad():
                    for batch_x, batch_y in val_loader:
                        batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                        outputs = model(batch_x)
                        loss = criterion(outputs, batch_y)

                        val_running_loss += loss.item() * batch_x.size(0)
                        _, predicted = outputs.max(1)
                        val_total += batch_y.size(0)
                        val_correct += predicted.eq(batch_y).sum().item()

                val_loss = val_running_loss / val_total
                val_accuracy = val_correct / val_total

                # Log epoch to experiment service
                metrics = {
                    "loss": round(train_loss, 6),
                    "val_loss": round(val_loss, 6),
                    "accuracy": round(train_accuracy, 6),
                    "val_accuracy": round(val_accuracy, 6),
                }

                async with async_session_factory() as db:
                    await ExperimentService.log_epoch(db, experiment_id, epoch, metrics)

                logger.info(
                    "Epoch %d/%d — loss=%.4f val_loss=%.4f acc=%.4f val_acc=%.4f",
                    epoch, config.num_epochs,
                    train_loss, val_loss, train_accuracy, val_accuracy,
                )

                # Early stopping check
                if config.early_stopping_patience is not None:
                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        patience_counter = 0
                    else:
                        patience_counter += 1
                        if patience_counter >= config.early_stopping_patience:
                            logger.info(
                                "Early stopping triggered at epoch %d", epoch
                            )
                            break

            # Mark experiment as completed
            async with async_session_factory() as db:
                await ExperimentService.complete_experiment(db, experiment_id)

        except Exception as exc:
            logger.exception("Training failed for experiment %s", experiment_id)
            async with async_session_factory() as db:
                await ExperimentService.fail_experiment(
                    db, experiment_id, str(exc)
                )
            raise
