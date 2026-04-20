"""Ethernet student CNN implementation with dependency guards."""

from __future__ import annotations

from dpcr_ids.exceptions import DependencyUnavailableError

try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError:
    torch = None
    nn = None


if nn is not None:
    class EthStudentCNN(nn.Module):
        def __init__(self, in_channels: int = 3, embedding_dim: int = 128) -> None:
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
                nn.BatchNorm2d(32),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(32, 64, kernel_size=3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(),
                nn.MaxPool2d(2),
            )
            self.pool = nn.AdaptiveAvgPool2d((1, 1))
            self.proj = nn.Linear(64, embedding_dim)
            self.classifier = nn.Linear(embedding_dim, 1)

        def forward_features(self, x):
            x = self.encoder(x)
            x = self.pool(x).flatten(1)
            return self.proj(x)

        def forward(self, x):
            features = self.forward_features(x)
            return self.classifier(features).squeeze(-1)
else:
    class EthStudentCNN:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            raise DependencyUnavailableError(
                "torch is required to instantiate EthStudentCNN. Install with `pip install -e .[ml]`."
            )
