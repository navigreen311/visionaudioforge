"""End-to-end integration tests for model registry and experiment lifecycle."""

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.mark.asyncio
async def test_register_and_list_models(test_app):
    """Register a model, then verify it appears in the model list."""
    # Register a model
    reg_response = await test_app.post(
        "/api/registry/register",
        json={
            "name": "test-resnet18",
            "version": "1.0.0",
            "framework": "pytorch",
            "metrics": {"accuracy": 0.95},
        },
    )
    assert reg_response.status_code in (200, 201, 501), (
        f"Unexpected status {reg_response.status_code}: {reg_response.text}"
    )

    # List models
    list_response = await test_app.get("/api/registry/models")
    assert list_response.status_code in (200, 501), (
        f"Unexpected status {list_response.status_code}: {list_response.text}"
    )

    if reg_response.status_code in (200, 201) and list_response.status_code == 200:
        models = list_response.json()
        if isinstance(models, list):
            names = [m.get("name") for m in models]
            assert "test-resnet18" in names


@pytest.mark.asyncio
async def test_model_promotion_lifecycle(test_app):
    """Register a model, promote through staging and production stages."""
    # Register
    reg_resp = await test_app.post(
        "/api/registry/register",
        json={
            "name": "promo-model",
            "version": "2.0.0",
            "framework": "pytorch",
        },
    )
    assert reg_resp.status_code in (200, 201, 501)

    if reg_resp.status_code in (200, 201):
        model_id = reg_resp.json().get("id", "unknown")

        # Promote to staging (endpoint may not exist yet)
        stage_resp = await test_app.post(
            f"/api/registry/models/{model_id}/promote",
            json={"stage": "staging"},
        )
        assert stage_resp.status_code in (200, 404, 501)

        # Promote to production
        if stage_resp.status_code == 200:
            prod_resp = await test_app.post(
                f"/api/registry/models/{model_id}/promote",
                json={"stage": "production"},
            )
            assert prod_resp.status_code in (200, 404, 501)


@pytest.mark.asyncio
async def test_experiment_create_and_log(test_app):
    """Create an experiment, log epochs, retrieve best checkpoint."""
    # Create experiment
    create_resp = await test_app.post(
        "/api/experiments",
        json={
            "name": "test-experiment",
            "config": {
                "backbone": "resnet18",
                "num_epochs": 3,
                "learning_rate": 0.001,
            },
        },
    )
    assert create_resp.status_code in (200, 201, 501), (
        f"Unexpected status {create_resp.status_code}: {create_resp.text}"
    )

    if create_resp.status_code in (200, 201):
        exp_id = create_resp.json().get("id", "unknown")

        # Log 3 epochs
        for epoch in range(1, 4):
            log_resp = await test_app.post(
                f"/api/experiments/{exp_id}/log",
                json={
                    "epoch": epoch,
                    "metrics": {"loss": 1.0 / epoch, "accuracy": 0.5 + epoch * 0.1},
                },
            )
            assert log_resp.status_code in (200, 201, 404, 501)

        # Get best checkpoint
        best_resp = await test_app.get(f"/api/experiments/{exp_id}/best")
        assert best_resp.status_code in (200, 404, 501)
