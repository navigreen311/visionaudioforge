"""Tests for Auto-ML, few-shot, zero-shot, and continuous learning services."""

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.services.models.automl import TRAINING_RECIPES, AutoMLService
from app.services.models.continuous_learning import ContinuousLearningService
from app.services.models.fewshot import FewShotClassifier
from app.services.models.zeroshot import ZeroShotClassifier


# ======================================================================
# AutoML
# ======================================================================


class TestAutoML:
    def test_hyperparameter_sweep_returns_ranked(self):
        results = AutoMLService.hyperparameter_sweep(
            base_config={"backbone": "resnet18"},
            param_grid={
                "learning_rate": [0.001, 0.01, 0.1],
                "batch_size": [16, 32],
            },
            num_trials=6,
        )
        assert len(results) <= 6
        assert all("config" in r and "metrics" in r and "rank" in r for r in results)
        # Ranks are 1-based consecutive
        ranks = [r["rank"] for r in results]
        assert ranks == list(range(1, len(results) + 1))
        # val_loss should be non-decreasing (ranked ascending)
        val_losses = [r["metrics"]["val_loss"] for r in results]
        assert val_losses == sorted(val_losses)

    def test_recommend_backbone_small_dataset(self):
        rec = AutoMLService.recommend_backbone({"num_samples": 500, "modality": "image"})
        assert rec["recommended"] == "resnet18"
        assert "reason" in rec
        assert isinstance(rec["alternatives"], list)

    def test_recommend_backbone_medium_dataset(self):
        rec = AutoMLService.recommend_backbone({"num_samples": 5000})
        assert rec["recommended"] == "resnet50"

    def test_recommend_backbone_large_dataset(self):
        rec = AutoMLService.recommend_backbone({"num_samples": 50000})
        assert rec["recommended"] == "clip-vit"

    def test_recommend_backbone_audio(self):
        rec = AutoMLService.recommend_backbone({"num_samples": 5000, "modality": "audio"})
        assert rec["recommended"] == "resnet18"

    def test_recommend_backbone_multimodal(self):
        rec = AutoMLService.recommend_backbone({"num_samples": 5000, "modality": "multimodal"})
        assert rec["recommended"] == "clip"

    def test_training_recipes_all_valid(self):
        for use_case in TRAINING_RECIPES:
            recipe = AutoMLService.training_recipe(use_case)
            assert "backbone" in recipe
            assert "use_case" in recipe
            assert recipe["use_case"] == use_case

    def test_training_recipe_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown use_case"):
            AutoMLService.training_recipe("nonexistent")

    def test_auto_augmentation_search(self):
        result = AutoMLService.auto_augmentation_search("dataset-123", num_trials=3)
        assert "best_config" in result
        assert "all_trials" in result
        assert len(result["all_trials"]) == 3


# ======================================================================
# Few-Shot Classifier
# ======================================================================


class TestFewShot:
    def _make_examples(self, num_classes: int = 3, per_class: int = 5):
        """Create synthetic example images for testing."""
        rng = np.random.RandomState(42)
        examples: dict[str, list[np.ndarray]] = {}
        for i in range(num_classes):
            cls_name = f"class_{i}"
            # Each "class" has a distinct mean so centroids separate well
            images = [rng.randn(64).astype(np.float32) + i * 5 for _ in range(per_class)]
            examples[cls_name] = images
        return examples

    def test_few_shot_build_centroids(self):
        examples = self._make_examples()
        clf = FewShotClassifier()
        result = clf.build_classifier(examples)
        assert result["num_classes"] == 3
        assert len(result["class_centroids"]) == 3
        assert all(v == 5 for v in result["examples_per_class"].values())

    def test_few_shot_predict_returns_class(self):
        examples = self._make_examples()
        clf = FewShotClassifier()
        built = clf.build_classifier(examples)
        centroids = built["class_centroids"]

        # Predict with an image close to class_1
        rng = np.random.RandomState(99)
        test_img = (rng.randn(64).astype(np.float32) + 1 * 5)
        pred = clf.predict(test_img, centroids)
        assert "predicted_class" in pred
        assert "confidence" in pred
        assert pred["predicted_class"] in centroids
        assert 0.0 <= pred["confidence"] <= 1.0

    def test_few_shot_evaluate(self):
        examples = self._make_examples()
        clf = FewShotClassifier()
        built = clf.build_classifier(examples)
        centroids = built["class_centroids"]
        # Use same examples as test set (overfitting-style, just for structure)
        result = clf.evaluate(examples, centroids)
        assert "accuracy" in result
        assert "per_class" in result
        assert "confusion_matrix" in result

    def test_min_examples_recommendation(self):
        rec = FewShotClassifier.min_examples_recommendation(10)
        assert rec["minimum"] == 3
        assert rec["recommended"] == 20  # max(5, 10*2)


# ======================================================================
# Zero-Shot Classifier
# ======================================================================


class TestZeroShot:
    def test_zero_shot_returns_scores(self):
        zs = ZeroShotClassifier()
        img = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
        result = zs.classify(img, ["cat", "dog", "bird"])
        assert "predicted_label" in result
        assert "confidence" in result
        assert "all_scores" in result
        assert len(result["all_scores"]) == 3

    def test_zero_shot_empty_labels_raises(self):
        zs = ZeroShotClassifier()
        img = np.zeros((8, 8, 3), dtype=np.uint8)
        with pytest.raises(ValueError):
            zs.classify(img, [])

    def test_compare_with_fewshot(self):
        zs = ZeroShotClassifier()
        clf = FewShotClassifier()

        rng = np.random.RandomState(42)
        examples = {
            "cat": [rng.randn(64).astype(np.float32) for _ in range(3)],
            "dog": [rng.randn(64).astype(np.float32) + 3 for _ in range(3)],
        }
        built = clf.build_classifier(examples)

        img = rng.randn(64).astype(np.float32)
        result = zs.compare_with_fewshot(img, ["cat", "dog"], built["class_centroids"])
        assert "zero_shot" in result
        assert "few_shot" in result
        assert isinstance(result["agreement"], bool)


# ======================================================================
# Continuous Learning
# ======================================================================


class TestContinuousLearning:
    def test_feedback_capture(self):
        svc = ContinuousLearningService()
        event = svc.capture_feedback(
            model_id="model-1",
            input_data={"image": "test.png"},
            predicted="cat",
            corrected="dog",
            user_id="user-42",
        )
        assert event["model_id"] == "model-1"
        assert event["predicted"] == "cat"
        assert event["corrected"] == "dog"
        assert event["is_correction"] is True
        assert "event_id" in event

    def test_feedback_no_correction(self):
        svc = ContinuousLearningService()
        event = svc.capture_feedback(
            model_id="model-1",
            input_data=None,
            predicted="cat",
            corrected="cat",
        )
        assert event["is_correction"] is False

    def test_feedback_queue(self):
        svc = ContinuousLearningService()
        for i in range(60):
            svc.capture_feedback("model-1", None, "cat", "dog" if i % 3 == 0 else "cat")
        queue = svc.get_feedback_queue("model-1", min_count=50)
        assert queue["ready_to_retrain"] is True
        assert queue["feedback_count"] == 60
        assert 0 <= queue["correction_rate"] <= 1.0
        assert isinstance(queue["class_distribution"], dict)

    def test_forgetting_check_safe(self):
        old = {"cat": 0.95, "dog": 0.90}
        new = {"cat": 0.94, "dog": 0.89}
        result = ContinuousLearningService.catastrophic_forgetting_check(old, new, threshold=0.05)
        assert result["safe_to_deploy"] is True
        assert result["degraded_classes"] == []

    def test_forgetting_check_degraded(self):
        old = {"cat": 0.95, "dog": 0.90}
        new = {"cat": 0.80, "dog": 0.88}
        result = ContinuousLearningService.catastrophic_forgetting_check(old, new, threshold=0.05)
        assert result["safe_to_deploy"] is False
        assert "cat" in result["degraded_classes"]
        assert result["max_degradation"] >= 0.1

    def test_trigger_retraining(self):
        svc = ContinuousLearningService()
        result = svc.trigger_retraining("model-1", [{"corrected": "dog"}])
        assert "job_id" in result
        assert result["strategy"] == "incremental_finetune"


# ======================================================================
# API Route Tests
# ======================================================================


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def test_app():
    """Create a minimal FastAPI app with only the transfer router for testing."""
    from fastapi import FastAPI

    from app.api.routes.transfer import router

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.anyio
async def test_api_sweep(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/transfer/automl/sweep",
            json={
                "base_config": {"backbone": "resnet18"},
                "param_grid": {"learning_rate": [0.001, 0.01], "batch_size": [16, 32]},
                "num_trials": 4,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) <= 4


@pytest.mark.anyio
async def test_api_recipes(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/transfer/recipes")
    assert resp.status_code == 200
    data = resp.json()
    assert "recipes" in data
    assert "image_classification" in data["recipes"]


@pytest.mark.anyio
async def test_api_recipe_detail(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/transfer/recipes/quick_prototype")
    assert resp.status_code == 200
    data = resp.json()
    assert data["backbone"] == "resnet18"


@pytest.mark.anyio
async def test_api_recommend_backbone(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/transfer/automl/recommend-backbone",
            json={"dataset_stats": {"num_samples": 500}},
        )
    assert resp.status_code == 200
    assert resp.json()["recommended"] == "resnet18"


@pytest.mark.anyio
async def test_api_feedback(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/transfer/feedback",
            json={"model_id": "m1", "predicted": "cat", "corrected": "dog"},
        )
    assert resp.status_code == 200
    assert resp.json()["is_correction"] is True


@pytest.mark.anyio
async def test_api_feedback_queue(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/transfer/feedback/some-model")
    assert resp.status_code == 200
    assert "feedback_count" in resp.json()
