"""PEFT/LoRA training service — manual LoRA implementation for parameter-efficient fine-tuning."""

import copy
import logging
import math
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class LoRALinear(nn.Module):
    """Drop-in replacement for nn.Linear that adds low-rank A*B adaptation matrices.

    forward(x) = original_linear(x) + (B @ A @ x^T)^T * (alpha / rank)
    Only A and B are trainable; the original weight is frozen.
    """

    def __init__(
        self,
        original: nn.Linear,
        rank: int = 8,
        alpha: float = 16.0,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.original = original
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank

        in_features = original.in_features
        out_features = original.out_features

        # Freeze the original weight
        self.original.weight.requires_grad = False
        if self.original.bias is not None:
            self.original.bias.requires_grad = False

        # Low-rank matrices: A (rank x in_features), B (out_features x rank)
        self.lora_A = nn.Parameter(torch.empty(rank, in_features))
        self.lora_B = nn.Parameter(torch.zeros(out_features, rank))

        # Kaiming init for A, zero init for B so LoRA starts as identity
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))

        self.lora_dropout = nn.Dropout(p=dropout) if dropout > 0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        original_out = self.original(x)
        # LoRA path: x @ A^T @ B^T * scaling
        lora_out = self.lora_dropout(x) @ self.lora_A.T @ self.lora_B.T * self.scaling
        return original_out + lora_out


class PEFTTrainer:
    """Parameter-Efficient Fine-Tuning via manual LoRA adapters."""

    def create_lora_config(
        self,
        rank: int = 8,
        alpha: float = 16.0,
        target_modules: list[str] | None = None,
        dropout: float = 0.1,
    ) -> dict[str, Any]:
        """Build a LoRA configuration dictionary."""
        return {
            "rank": rank,
            "alpha": alpha,
            "target_modules": target_modules or ["fc"],
            "dropout": dropout,
        }

    def apply_lora(
        self, model: nn.Module, config: dict[str, Any]
    ) -> nn.Module:
        """Replace target linear layers with LoRALinear wrappers.

        Walks the module tree and replaces any nn.Linear whose name (or parent
        attribute name) matches one of the *target_modules* patterns.
        """
        rank = config["rank"]
        alpha = config["alpha"]
        dropout = config["dropout"]
        targets = config["target_modules"]

        replaced = 0
        for target_name in targets:
            replaced += self._replace_module(model, target_name, rank, alpha, dropout)

        logger.info("Applied LoRA to %d layer(s) with rank=%d", replaced, rank)
        return model

    # ------------------------------------------------------------------
    def _replace_module(
        self,
        module: nn.Module,
        target_name: str,
        rank: int,
        alpha: float,
        dropout: float,
    ) -> int:
        """Recursively replace Linear layers matching *target_name*."""
        replaced = 0
        for name, child in list(module.named_children()):
            if name == target_name and isinstance(child, nn.Linear):
                lora_layer = LoRALinear(child, rank=rank, alpha=alpha, dropout=dropout)
                setattr(module, name, lora_layer)
                replaced += 1
            else:
                replaced += self._replace_module(child, target_name, rank, alpha, dropout)
        return replaced

    # ------------------------------------------------------------------

    def merge_lora(self, model: nn.Module) -> nn.Module:
        """Merge LoRA weights back into the original linear layers (irreversible).

        After merging, the model behaves identically but no longer has separate
        LoRA parameters.
        """
        for name, module in list(model.named_modules()):
            if isinstance(module, LoRALinear):
                # Merge: W' = W + B @ A * scaling
                with torch.no_grad():
                    module.original.weight.add_(
                        (module.lora_B @ module.lora_A) * module.scaling
                    )
                # Replace LoRALinear with the merged original
                parent = model
                parts = name.split(".")
                for part in parts[:-1]:
                    parent = getattr(parent, part)
                setattr(parent, parts[-1], module.original)

        logger.info("Merged LoRA weights into base model")
        return model

    def count_trainable_params(
        self, model: nn.Module
    ) -> dict[str, int | float]:
        """Return total, trainable, frozen parameter counts and trainable %."""
        total = sum(p.numel() for p in model.parameters())
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        frozen = total - trainable
        percentage = (trainable / total * 100) if total > 0 else 0.0
        return {
            "total": total,
            "trainable": trainable,
            "frozen": frozen,
            "percentage": round(percentage, 4),
        }

    def save_lora_weights(self, model: nn.Module, path: str) -> None:
        """Save only the LoRA A and B matrices to *path*."""
        lora_state: dict[str, torch.Tensor] = {}
        for name, module in model.named_modules():
            if isinstance(module, LoRALinear):
                lora_state[f"{name}.lora_A"] = module.lora_A.data.clone()
                lora_state[f"{name}.lora_B"] = module.lora_B.data.clone()

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(lora_state, path)
        logger.info("Saved LoRA weights (%d tensors) to %s", len(lora_state), path)

    def load_lora_weights(self, model: nn.Module, path: str) -> nn.Module:
        """Load previously saved LoRA weights into matching LoRALinear layers."""
        lora_state = torch.load(path, weights_only=True)
        for name, module in model.named_modules():
            if isinstance(module, LoRALinear):
                a_key = f"{name}.lora_A"
                b_key = f"{name}.lora_B"
                if a_key in lora_state:
                    module.lora_A.data.copy_(lora_state[a_key])
                if b_key in lora_state:
                    module.lora_B.data.copy_(lora_state[b_key])

        logger.info("Loaded LoRA weights from %s", path)
        return model
