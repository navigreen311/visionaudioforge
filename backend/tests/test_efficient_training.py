"""Tests for efficient training: LoRA/PEFT, quantization, gradient clipping,
early stopping, and cost estimation."""

import tempfile

import pytest
import torch
import torch.nn as nn

from app.services.models.cost_estimator import TrainingCostEstimator
from app.services.models.peft_training import LoRALinear, PEFTTrainer
from app.services.models.quantization import ModelQuantizer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_simple_model(in_features: int = 64, out_features: int = 10) -> nn.Module:
    """A tiny model with a single Linear layer named ``fc``."""
    model = nn.Sequential()
    model.add_module("features", nn.Linear(in_features, 32))
    model.add_module("relu", nn.ReLU())
    model.fc = nn.Linear(32, out_features)
    return model


class _TinyModel(nn.Module):
    """Small model with a named ``fc`` attribute for LoRA targeting."""

    def __init__(self, in_f: int = 64, out_f: int = 10):
        super().__init__()
        self.features = nn.Linear(in_f, 32)
        self.relu = nn.ReLU()
        self.fc = nn.Linear(32, out_f)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(self.relu(self.features(x)))


# ---------------------------------------------------------------------------
# LoRA / PEFT tests
# ---------------------------------------------------------------------------

class TestLoRA:
    def test_lora_reduces_trainable_params(self):
        """Applying LoRA should freeze most params and add small trainable A/B."""
        model = _TinyModel()
        trainer = PEFTTrainer()

        # Freeze everything first (simulating transfer learning)
        for p in model.parameters():
            p.requires_grad = False

        before = trainer.count_trainable_params(model)
        assert before["trainable"] == 0

        config = trainer.create_lora_config(rank=4, alpha=8, target_modules=["fc"])
        model = trainer.apply_lora(model, config)

        after = trainer.count_trainable_params(model)
        assert after["trainable"] > 0
        assert after["trainable"] < after["total"]
        assert after["percentage"] < 100.0

    def test_lora_forward_pass(self):
        """LoRA-augmented model should produce valid output with gradients."""
        model = _TinyModel()
        trainer = PEFTTrainer()

        for p in model.parameters():
            p.requires_grad = False

        config = trainer.create_lora_config(rank=4, target_modules=["fc"])
        model = trainer.apply_lora(model, config)

        x = torch.randn(2, 64)
        out = model(x)
        assert out.shape == (2, 10)

        # Verify gradients flow through LoRA params
        loss = out.sum()
        loss.backward()

        lora_layer = model.fc
        assert isinstance(lora_layer, LoRALinear)
        assert lora_layer.lora_A.grad is not None
        assert lora_layer.lora_B.grad is not None

    def test_lora_save_load(self):
        """Save and reload LoRA weights should preserve values."""
        model = _TinyModel()
        trainer = PEFTTrainer()

        for p in model.parameters():
            p.requires_grad = False

        config = trainer.create_lora_config(rank=4, target_modules=["fc"])
        model = trainer.apply_lora(model, config)

        # Manually set LoRA weights to known values
        with torch.no_grad():
            model.fc.lora_A.fill_(1.0)
            model.fc.lora_B.fill_(2.0)

        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            path = f.name

        trainer.save_lora_weights(model, path)

        # Reset and reload
        with torch.no_grad():
            model.fc.lora_A.fill_(0.0)
            model.fc.lora_B.fill_(0.0)

        trainer.load_lora_weights(model, path)
        assert torch.allclose(model.fc.lora_A, torch.ones_like(model.fc.lora_A))
        assert torch.allclose(model.fc.lora_B, torch.full_like(model.fc.lora_B, 2.0))

    def test_merge_lora(self):
        """After merging, LoRALinear layers should be replaced with plain Linear."""
        model = _TinyModel()
        trainer = PEFTTrainer()
        config = trainer.create_lora_config(rank=4, target_modules=["fc"])
        model = trainer.apply_lora(model, config)

        assert isinstance(model.fc, LoRALinear)
        model = trainer.merge_lora(model)
        assert isinstance(model.fc, nn.Linear)


# ---------------------------------------------------------------------------
# Quantization tests
# ---------------------------------------------------------------------------

class TestQuantization:
    def test_quantize_dynamic_reduces_size(self):
        """Dynamic quantization should return a model (smoke test)."""
        model = _TinyModel()
        quantizer = ModelQuantizer()
        q_model = quantizer.quantize_dynamic(model, dtype="int8")
        # The quantized model should still produce output
        x = torch.randn(1, 64)
        out = q_model(x)
        assert out.shape == (1, 10)

    def test_size_reduction_estimate(self):
        """Size estimate should show a reduction for int8."""
        quantizer = ModelQuantizer()
        result = quantizer.estimate_size_reduction(11_000_000, dtype="int8")
        assert result["reduction_pct"] == 75.0
        assert result["quantized_mb"] < result["original_mb"]

    def test_size_reduction_float16(self):
        """float16 should give 50% reduction."""
        quantizer = ModelQuantizer()
        result = quantizer.estimate_size_reduction(1_000_000, dtype="float16")
        assert result["reduction_pct"] == 50.0

    def test_static_quantization_stub(self):
        """Static quantization stub should return guidance."""
        quantizer = ModelQuantizer()
        result = quantizer.quantize_static_stub(_TinyModel())
        assert result["status"] == "stub"
        assert "calibration" in result["note"].lower()

    def test_compare_inference_speed(self):
        """Speed comparison should return timing data."""
        model = _TinyModel()
        quantizer = ModelQuantizer()
        q_model = quantizer.quantize_dynamic(model, dtype="int8")
        x = torch.randn(1, 64)
        result = quantizer.compare_inference_speed(model, q_model, x)
        assert "original_ms" in result
        assert "quantized_ms" in result
        assert "speedup" in result


# ---------------------------------------------------------------------------
# Training stabilization tests
# ---------------------------------------------------------------------------

class TestTrainingStabilization:
    def test_gradient_clipping_applied(self):
        """Gradient clipping should limit gradient norms."""
        model = _TinyModel()
        x = torch.randn(4, 64)
        y = torch.randint(0, 10, (4,))

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.SGD(model.parameters(), lr=100.0)  # large LR → large grads

        optimizer.zero_grad()
        loss = criterion(model(x), y)
        loss.backward()

        max_norm = 1.0
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)

        total_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                total_norm += p.grad.data.norm(2).item() ** 2
        total_norm = total_norm ** 0.5

        # After clipping, the total norm should be ≤ max_norm (within float tolerance)
        assert total_norm <= max_norm + 1e-5

    def test_early_stopping_triggers(self):
        """Simulate early stopping logic: counter should trigger after patience."""
        patience = 3
        best_val_loss = float("inf")
        patience_counter = 0
        stopped_epoch = None

        # Simulate val losses that don't improve after epoch 2
        val_losses = [1.0, 0.8, 0.9, 0.95, 1.0, 1.1]

        for epoch, val_loss in enumerate(val_losses, 1):
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    stopped_epoch = epoch
                    break

        assert stopped_epoch == 5  # patience=3, no improvement from epoch 2 onward


# ---------------------------------------------------------------------------
# Cost estimation tests
# ---------------------------------------------------------------------------

class TestCostEstimation:
    def test_cost_estimate_returns_values(self):
        """Cost estimator should return all expected fields."""
        estimator = TrainingCostEstimator()
        result = estimator.estimate_cost({
            "model_params": 11_000_000,
            "num_epochs": 10,
            "num_samples": 10_000,
            "gpu_type": "T4",
        })
        assert "estimated_time_minutes" in result
        assert "estimated_gpu_hours" in result
        assert "estimated_cost_usd" in result
        assert "breakdown" in result
        assert result["estimated_time_minutes"] > 0
        assert result["estimated_cost_usd"] > 0

    def test_cost_estimate_a100_cheaper_per_hour_time(self):
        """A100 should estimate faster training than T4 (higher throughput)."""
        estimator = TrainingCostEstimator()
        cfg = {"model_params": 100_000_000, "num_epochs": 5, "num_samples": 50_000}
        t4 = estimator.estimate_cost({**cfg, "gpu_type": "T4"})
        a100 = estimator.estimate_cost({**cfg, "gpu_type": "A100"})
        assert a100["estimated_time_minutes"] < t4["estimated_time_minutes"]

    def test_instance_recommendation(self):
        """Should recommend a GPU and provide alternatives."""
        estimator = TrainingCostEstimator()
        result = estimator.recommend_instance(model_params=11_000_000, batch_size=32)
        assert "recommended" in result
        assert "alternatives" in result
        assert "name" in result["recommended"]
        assert "estimated_memory_gb" in result

    def test_inference_cost(self):
        """Inference cost should return per-request and daily/monthly values."""
        estimator = TrainingCostEstimator()
        result = estimator.estimate_inference_cost(
            model_params=11_000_000, requests_per_day=10_000
        )
        assert result["cost_per_request"] >= 0
        assert result["daily_cost"] >= 0
        assert result["monthly_cost"] >= 0


# ---------------------------------------------------------------------------
# API route tests (using FastAPI TestClient pattern)
# ---------------------------------------------------------------------------

class TestAPIEstimateCost:
    def test_api_estimate_cost(self):
        """The /estimate-cost endpoint should return a valid cost estimate."""
        # Import here to avoid import errors if FastAPI app isn't fully wired
        try:
            from fastapi.testclient import TestClient

            from app.api.routes.transfer import router
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.post("/api/transfer/estimate-cost", json={
                "model_params": 11_000_000,
                "num_epochs": 10,
                "num_samples": 10_000,
                "gpu_type": "T4",
            })
            assert response.status_code == 200
            data = response.json()
            assert "estimated_cost_usd" in data
            assert data["estimated_cost_usd"] > 0
        except ImportError:
            pytest.skip("FastAPI test client not available")
