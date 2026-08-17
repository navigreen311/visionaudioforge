"""Transfer learning / fine-tuning service using PyTorch."""

import asyncio
import logging
import uuid
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, Dataset, TensorDataset

logger = logging.getLogger(__name__)

#: Input size expected by the torchvision ResNet backbones used here.
IMAGE_SIZE = 224


def _as_uuid(value: str | None) -> uuid.UUID | None:
    """Parse *value* as a UUID, or None if it is not one.

    Lets the existing ``dataset_path`` field carry a dataset id, so callers that
    already pass one get real data without an API change.
    """
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


class _AssetImageDataset(Dataset):
    """Torch dataset over dataset samples stored in object storage.

    Samples come from ``DatasetService.list_samples``; each carries a storage
    path and a label. Images are fetched and decoded lazily so a large dataset
    is never held in memory at once.
    """

    def __init__(
        self,
        samples: list[dict],
        class_to_idx: dict[str, int],
        storage,
    ) -> None:
        self.samples = samples
        self.class_to_idx = class_to_idx
        self.storage = storage

        from torchvision import transforms

        self.transform = transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.ToTensor(),
                # ImageNet statistics — the backbones are pretrained on it.
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ]
        )

    def __len__(self) -> int:
        return len(self.samples)

    def _read_bytes(self, storage_path: str) -> bytes:
        """Fetch one object, accepting either 'bucket/key' or a bare key."""
        from app.services.data.dataset_manager import BUCKET

        path = str(storage_path)
        bucket, key = BUCKET, path
        if path.startswith(f"{BUCKET}/"):
            key = path[len(BUCKET) + 1 :]

        # DataLoader workers are synchronous, so drive the async client here.
        return asyncio.run(self.storage.download_file(bucket, key))

    def __getitem__(self, index: int):
        import io

        from PIL import Image

        sample = self.samples[index]
        label = self.class_to_idx[str(sample["label"])]

        raw = self._read_bytes(sample["storage_path"])
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        return self.transform(image), torch.tensor(label, dtype=torch.long)


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
    gradient_accumulation_steps: int = 1
    lr_scheduler_patience: int = 3
    lr_scheduler_factor: float = 0.5
    lora_config: dict | None = None
    quantize_after: bool = False

    #: Dataset to fine-tune on, loaded through DatasetService. When set, the
    #: uploaded samples are used and num_classes is derived from their labels.
    dataset_id: str | None = None
    #: Opt in to synthetic tensors explicitly. Required for a run with no
    #: dataset_id, so a job never silently trains on noise while appearing to
    #: have trained on the user's data.
    use_synthetic_data: bool = False
    #: Fraction of samples held out for validation when the dataset carries no
    #: explicit train/val split in its asset metadata.
    val_split: float = 0.2


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

    async def _build_dataloaders(
        self, config: FinetuneConfig
    ) -> tuple[DataLoader, DataLoader]:
        """Build train/val dataloaders for a fine-tune run.

        Loads the uploaded samples for ``config.dataset_id`` via DatasetService.
        Synthetic tensors are only used when ``use_synthetic_data`` is set
        explicitly, so a job cannot quietly train on noise.
        """
        dataset_id = config.dataset_id or _as_uuid(config.dataset_path)
        if dataset_id:
            return await self._load_dataset(config, dataset_id)

        if config.use_synthetic_data:
            logger.warning(
                "Fine-tune running on SYNTHETIC data — no dataset_id supplied. "
                "Resulting metrics describe random tensors, not real samples."
            )
            return self._create_synthetic_data(config)

        raise ValueError(
            f"No dataset to train on: dataset_id is unset and dataset_path "
            f"({config.dataset_path!r}) is not a dataset id. Supply a "
            "dataset_id, or set use_synthetic_data=True to deliberately train "
            "on synthetic tensors."
        )

    async def _load_dataset(
        self, config: FinetuneConfig, dataset_id: uuid.UUID
    ) -> tuple[DataLoader, DataLoader]:
        """Load a real dataset's samples into train/val dataloaders."""
        from app.database import async_session_factory
        from app.services.data.dataset_manager import DatasetService
        from app.services.data.storage import MinIOStorageService

        storage = MinIOStorageService()

        async with async_session_factory() as db:
            samples = await DatasetService.list_samples(db, dataset_id)

        if not samples:
            raise ValueError(
                f"Dataset {dataset_id} has no samples to train on."
            )

        labelled = [s for s in samples if s.get("label")]
        if not labelled:
            raise ValueError(
                f"Dataset {dataset_id} has samples but none carry a "
                "label; supervised fine-tuning needs labelled data."
            )

        classes = sorted({str(s["label"]) for s in labelled})
        class_to_idx = {name: i for i, name in enumerate(classes)}
        # The dataset defines the head size — trust it over the config default.
        config.num_classes = len(classes)

        explicit = [s for s in labelled if s.get("split") in ("train", "val")]
        if explicit:
            train_samples = [s for s in explicit if s["split"] == "train"]
            val_samples = [s for s in explicit if s["split"] == "val"]
        else:
            cut = max(1, int(len(labelled) * (1 - config.val_split)))
            train_samples, val_samples = labelled[:cut], labelled[cut:]

        if not val_samples:  # tiny dataset — validate on the training split
            val_samples = train_samples

        logger.info(
            "Fine-tuning dataset %s: %d train / %d val samples across %d classes",
            dataset_id,
            len(train_samples),
            len(val_samples),
            len(classes),
        )

        train_ds = _AssetImageDataset(train_samples, class_to_idx, storage)
        val_ds = _AssetImageDataset(val_samples, class_to_idx, storage)

        return (
            DataLoader(train_ds, batch_size=config.batch_size, shuffle=True),
            DataLoader(val_ds, batch_size=config.batch_size, shuffle=False),
        )

    def _create_synthetic_data(
        self, config: FinetuneConfig
    ) -> tuple[DataLoader, DataLoader]:
        """Create synthetic train/val dataloaders (tests and smoke runs only)."""
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

        # Build the data first: loading a real dataset sets config.num_classes
        # from its labels, and the classifier head is sized from that.
        train_loader, val_loader = await self._build_dataloaders(config)

        model = self._build_model(config)
        model = model.to(device)

        # Apply LoRA if configured
        if config.lora_config is not None:
            from app.services.models.peft_training import PEFTTrainer

            peft = PEFTTrainer()
            lora_cfg = peft.create_lora_config(**config.lora_config)
            model = peft.apply_lora(model, lora_cfg)
            logger.info(
                "LoRA applied: %s", peft.count_trainable_params(model)
            )

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=config.learning_rate,
        )

        # Learning-rate scheduler: reduce on plateau
        scheduler = ReduceLROnPlateau(
            optimizer,
            mode="min",
            patience=config.lr_scheduler_patience,
            factor=config.lr_scheduler_factor,
        )

        best_val_loss = float("inf")
        best_model_state = None
        patience_counter = 0
        accum_steps = max(1, config.gradient_accumulation_steps)

        try:
            for epoch in range(1, config.num_epochs + 1):
                # --- Training phase ---
                model.train()
                running_loss = 0.0
                correct = 0
                total = 0

                optimizer.zero_grad()
                for step, (batch_x, batch_y) in enumerate(train_loader, 1):
                    batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                    outputs = model(batch_x)
                    loss = criterion(outputs, batch_y)
                    # Scale loss for gradient accumulation
                    (loss / accum_steps).backward()

                    if step % accum_steps == 0 or step == len(train_loader):
                        # Gradient clipping
                        if config.gradient_clip_value is not None:
                            torch.nn.utils.clip_grad_norm_(
                                model.parameters(), config.gradient_clip_value
                            )

                        optimizer.step()
                        optimizer.zero_grad()

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

                # Step the LR scheduler
                scheduler.step(val_loss)

                # Log epoch to experiment service
                current_lr = optimizer.param_groups[0]["lr"]
                metrics = {
                    "loss": round(train_loss, 6),
                    "val_loss": round(val_loss, 6),
                    "accuracy": round(train_accuracy, 6),
                    "val_accuracy": round(val_accuracy, 6),
                    "learning_rate": current_lr,
                }

                async with async_session_factory() as db:
                    await ExperimentService.log_epoch(db, experiment_id, epoch, metrics)

                logger.info(
                    "Epoch %d/%d — loss=%.4f val_loss=%.4f acc=%.4f val_acc=%.4f lr=%.2e",
                    epoch, config.num_epochs,
                    train_loss, val_loss, train_accuracy, val_accuracy, current_lr,
                )

                # Early stopping check with best-checkpoint restore
                if config.early_stopping_patience is not None:
                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        patience_counter = 0
                        import copy
                        best_model_state = copy.deepcopy(model.state_dict())
                    else:
                        patience_counter += 1
                        if patience_counter >= config.early_stopping_patience:
                            logger.info(
                                "Early stopping triggered at epoch %d", epoch
                            )
                            if best_model_state is not None:
                                model.load_state_dict(best_model_state)
                                logger.info("Restored best checkpoint")
                            break

            # Post-training quantization
            if config.quantize_after:
                from app.services.models.quantization import ModelQuantizer

                quantizer = ModelQuantizer()
                model = quantizer.quantize_dynamic(model, dtype="int8")
                logger.info("Post-training quantization applied")

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
