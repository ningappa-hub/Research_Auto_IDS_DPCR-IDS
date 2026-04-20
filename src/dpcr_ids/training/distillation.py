"""Knowledge distillation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from dpcr_ids.exceptions import DependencyUnavailableError

try:
    import torch
    import torch.nn.functional as F
except ModuleNotFoundError:
    torch = None
    F = None


@dataclass(slots=True)
class DistillationConfig:
    alpha: float = 0.5
    temperature: float = 4.0


if torch is not None and F is not None:
    def distillation_loss(student_logits, teacher_logits, labels, alpha: float = 0.5, temperature: float = 4.0):
        hard_loss = F.binary_cross_entropy_with_logits(student_logits, labels.float())
        teacher_probs = torch.sigmoid(teacher_logits / temperature).clamp(1e-7, 1 - 1e-7)
        student_probs = torch.sigmoid(student_logits / temperature).clamp(1e-7, 1 - 1e-7)
        soft_loss = (
            teacher_probs * (torch.log(teacher_probs) - torch.log(student_probs))
            + (1 - teacher_probs) * (torch.log(1 - teacher_probs) - torch.log(1 - student_probs))
        ).mean() * (temperature ** 2)
        return alpha * hard_loss + (1 - alpha) * soft_loss
else:
    def distillation_loss(*args, **kwargs):  # type: ignore[no-redef]
        raise DependencyUnavailableError(
            "torch is required to compute distillation loss. Install with `pip install -e .[ml]`."
        )
