"""Tiny late-fusion meta-models for cross-protocol edge IDS."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dpcr_ids.exceptions import DependencyUnavailableError

try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError:
    torch = None
    nn = None


if TYPE_CHECKING:
    from torch import Tensor
else:
    Tensor = Any


if nn is not None:
    def stack_expert_outputs(
        logits_or_probs: list[Tensor],
        embeddings: list[Tensor] | None = None,
    ) -> Tensor:
        """Pack CAN and Ethernet expert outputs into a fixed [batch, 2, 129] tensor."""

        if len(logits_or_probs) != 2:
            raise ValueError("Late fusion expects exactly two experts in the fixed order [can, ethernet]")
        if embeddings is None or len(embeddings) != 2:
            raise ValueError("Late fusion requires one embedding tensor per expert in the fixed order [can, ethernet]")

        batch_size = int(logits_or_probs[0].shape[0])
        packed: list[Tensor] = []
        for index, score in enumerate(logits_or_probs):
            score_column = score.reshape(batch_size, 1)
            embedding = embeddings[index]
            if int(embedding.shape[0]) != batch_size:
                raise ValueError("All expert embeddings must use the same batch dimension")
            packed.append(torch.cat([score_column, embedding], dim=1))

        feature_dim = int(packed[0].shape[1])
        if any(int(item.shape[1]) != feature_dim for item in packed):
            raise ValueError("All expert outputs must have the same feature dimension after packing")
        if feature_dim != 129:
            raise ValueError(f"Late-fusion expert_dim must be 129 (1 logit + 128 embedding), got {feature_dim}")
        return torch.stack(packed, dim=1)


    class TinyLateFusionMetaModel(nn.Module):
        """Small gated late-fusion head for one CAN expert and one Ethernet expert."""

        def __init__(
            self,
            num_experts: int = 2,
            expert_dim: int = 129,
            hidden_dim: int = 8,
            fusion_dim: int = 16,
        ) -> None:
            super().__init__()
            if num_experts != 2:
                raise ValueError("TinyLateFusionMetaModel expects exactly two experts in the fixed order [can, ethernet]")
            if expert_dim != 129:
                raise ValueError("TinyLateFusionMetaModel expects expert_dim=129 (1 raw logit + 128 embedding)")
            if hidden_dim <= 0 or fusion_dim <= 0:
                raise ValueError("hidden_dim and fusion_dim must be positive")

            self.num_experts = num_experts
            self.expert_dim = expert_dim
            self.hidden_dim = hidden_dim
            self.expert_proj = nn.Linear(expert_dim, hidden_dim)
            self.expert_gate = nn.Linear(expert_dim, 1)
            self.activation = nn.ReLU()
            self.classifier = nn.Sequential(
                nn.Linear(num_experts * hidden_dim, fusion_dim),
                nn.ReLU(),
                nn.Linear(fusion_dim, 1),
            )

        def forward_features(self, x: Tensor) -> Tensor:
            if x.ndim != 3:
                raise ValueError("Late-fusion input must have shape [batch, experts, channels]")
            if not torch.jit.is_tracing() and not torch.onnx.is_in_onnx_export():
                if x.shape[1] != self.num_experts or x.shape[2] != self.expert_dim:
                    raise ValueError(
                        f"Expected input shape [batch, {self.num_experts}, {self.expert_dim}], got {tuple(x.shape)}"
                    )
            projected = self.activation(self.expert_proj(x))
            gates = torch.sigmoid(self.expert_gate(x))
            weighted = projected * gates
            return weighted.flatten(start_dim=1)

        def forward(self, x: Tensor) -> Tensor:
            features = self.forward_features(x)
            return self.classifier(features).squeeze(-1)
else:
    def stack_expert_outputs(*args, **kwargs):  # type: ignore[no-redef]
        raise DependencyUnavailableError(
            "torch is required to pack expert outputs for late fusion. Install with `pip install -e .[ml]`."
        )


    class TinyLateFusionMetaModel:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            raise DependencyUnavailableError(
                "torch is required to instantiate TinyLateFusionMetaModel. Install with `pip install -e .[ml]`."
            )
