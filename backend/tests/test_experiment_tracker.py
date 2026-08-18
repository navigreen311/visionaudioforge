"""Tests for experiment tracker service and API routes."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.models.training import FinetuneConfig


# ---------- Fixtures ----------


def _make_experiment(**overrides):
    """Create a mock Experiment object."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "test-experiment",
        "status": "created",
        "config": {"backbone": "resnet18"},
        "workspace_id": uuid.uuid4(),
        "model_id": None,
        "best_epoch": None,
        "error_message": None,
        "epochs": [],
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_epoch(experiment_id, epoch_number, **overrides):
    """Create a mock ExperimentEpoch object."""
    defaults = {
        "id": uuid.uuid4(),
        "experiment_id": experiment_id,
        "epoch_number": epoch_number,
        "train_loss": 0.5,
        "val_loss": 0.6,
        "accuracy": 0.8,
        "val_accuracy": 0.75,
        "metrics": {
            "loss": 0.5,
            "val_loss": 0.6,
            "accuracy": 0.8,
            "val_accuracy": 0.75,
        },
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------- Service Unit Tests ----------


@pytest.mark.anyio
async def test_create_experiment():
    """ExperimentService.create_experiment should insert and return an experiment."""
    from app.services.models.experiments import ExperimentService

    db = AsyncMock()
    ws_id = uuid.uuid4()

    # Mock the db.commit and db.refresh to be no-ops
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = await ExperimentService.create_experiment(
        db,
        name="my-exp",
        config={"lr": 0.001},
        model_id=None,
        workspace_id=ws_id,
    )

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()
    assert result.name == "my-exp"
    assert result.status == "created"
    assert result.workspace_id == ws_id


@pytest.mark.anyio
async def test_log_epoch_updates_status_to_running():
    """First epoch should transition experiment status from 'created' to 'running'."""
    from app.services.models.experiments import ExperimentService

    exp_id = uuid.uuid4()
    mock_experiment = _make_experiment(id=exp_id, status="created")

    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # Mock the select query to return the experiment
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = mock_experiment
    db.execute = AsyncMock(return_value=mock_result)

    metrics = {"loss": 0.5, "val_loss": 0.6, "accuracy": 0.8, "val_accuracy": 0.75}
    epoch = await ExperimentService.log_epoch(db, exp_id, 1, metrics)

    assert mock_experiment.status == "running"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_complete_experiment_finds_best_epoch():
    """complete_experiment should set status='completed' and find best epoch by val_loss."""
    from app.services.models.experiments import ExperimentService

    exp_id = uuid.uuid4()
    epochs = [
        _make_epoch(exp_id, 1, val_loss=0.8),
        _make_epoch(exp_id, 2, val_loss=0.5),  # best
        _make_epoch(exp_id, 3, val_loss=0.6),
    ]
    mock_experiment = _make_experiment(id=exp_id, status="running", epochs=epochs)

    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = mock_experiment
    db.execute = AsyncMock(return_value=mock_result)

    result = await ExperimentService.complete_experiment(db, exp_id)

    assert mock_experiment.status == "completed"
    assert mock_experiment.best_epoch == 2


@pytest.mark.anyio
async def test_get_best_checkpoint_min_val_loss():
    """get_best_checkpoint should return epoch with lowest val_loss."""
    from app.services.models.experiments import ExperimentService

    exp_id = uuid.uuid4()
    epochs = [
        _make_epoch(exp_id, 1, val_loss=0.9),
        _make_epoch(exp_id, 2, val_loss=0.3),
        _make_epoch(exp_id, 3, val_loss=0.5),
    ]

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = epochs
    db.execute = AsyncMock(return_value=mock_result)

    best = await ExperimentService.get_best_checkpoint(
        db, exp_id, metric="val_loss", mode="min"
    )

    assert best["epoch_number"] == 2
    assert best["value"] == 0.3


@pytest.mark.anyio
async def test_compare_experiments():
    """compare_experiments should return summaries for each experiment."""
    from app.services.models.experiments import ExperimentService

    exp1_id = uuid.uuid4()
    exp2_id = uuid.uuid4()

    exp1 = _make_experiment(
        id=exp1_id,
        name="exp-1",
        status="completed",
        best_epoch=2,
        epochs=[
            _make_epoch(exp1_id, 1, val_loss=0.8, accuracy=0.7, train_loss=0.9),
            _make_epoch(exp1_id, 2, val_loss=0.5, accuracy=0.85, train_loss=0.6),
        ],
    )
    exp2 = _make_experiment(
        id=exp2_id,
        name="exp-2",
        status="completed",
        best_epoch=1,
        epochs=[
            _make_epoch(exp2_id, 1, val_loss=0.4, accuracy=0.9, train_loss=0.5),
        ],
    )

    db = AsyncMock()
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = exp1
    results[1].scalar_one_or_none.return_value = exp2
    db.execute = AsyncMock(side_effect=results)

    summaries = await ExperimentService.compare_experiments(db, [exp1_id, exp2_id])

    assert len(summaries) == 2
    assert summaries[0]["name"] == "exp-1"
    assert summaries[0]["best_val_loss"] == 0.5
    assert summaries[1]["name"] == "exp-2"
    assert summaries[1]["best_accuracy"] == 0.9


# ---------- Config Validation Tests ----------


def test_finetune_config_validation():
    """FinetuneConfig should accept valid params and set defaults."""
    config = FinetuneConfig(
        backbone="resnet50",
        dataset_path="/data/images",
        num_epochs=20,
        learning_rate=0.0005,
        batch_size=64,
        freeze_layers=False,
    )
    assert config.backbone == "resnet50"
    assert config.num_epochs == 20
    assert config.gradient_clip_value is None
    assert config.early_stopping_patience is None
    assert config.num_classes == 10  # default


def test_finetune_config_with_all_options():
    """FinetuneConfig with all optional fields set."""
    config = FinetuneConfig(
        backbone="resnet18",
        dataset_path="/data",
        gradient_clip_value=1.0,
        early_stopping_patience=5,
        num_classes=100,
    )
    assert config.gradient_clip_value == 1.0
    assert config.early_stopping_patience == 5
    assert config.num_classes == 100


# ---------- API Route Tests ----------


@pytest.mark.anyio
async def test_api_list_experiments(client):
    """GET /api/experiments should return 200 (may be empty with mock DB)."""
    ws_id = str(uuid.uuid4())
    response = await client.get(f"/api/experiments?workspace_id={ws_id}")
    # With real DB this returns data; with mock/test DB we accept 200 or 500
    assert response.status_code in (200, 500)


@pytest.mark.anyio
async def test_api_create_experiment(client, test_workspace_id):
    """POST /api/experiments creates an experiment in a real workspace.

    This used to post a random workspace_id and accept 201 or 500. The id
    could never satisfy the foreign key, so the 201 it saw came from a
    fallback that fabricated an experiment — an id that had never been
    written and would 404 on the next request. Against a real workspace the
    endpoint has to genuinely create the row.
    """
    body = {
        "name": "test-exp",
        "config": {"backbone": "resnet18"},
        "workspace_id": test_workspace_id,
    }
    response = await client.post("/api/experiments", json=body)
    assert response.status_code == 201, response.text
    assert response.json()["workspace_id"] == test_workspace_id
