"""CAN student TCN implementation with dependency guards."""

from __future__ import annotations

from dpcr_ids.exceptions import DependencyUnavailableError

try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError:
    torch = None
    nn = None


if nn is not None:
    class DepthwiseSeparableTemporalBlock(nn.Module):
        def __init__(self, in_channels: int, out_channels: int, dilation: int) -> None:
            super().__init__()
            padding = dilation
            self.depthwise = nn.Conv1d(
                in_channels,
                in_channels,
                kernel_size=3,
                padding=padding,
                dilation=dilation,
                groups=in_channels,
            )
            self.pointwise = nn.Conv1d(in_channels, out_channels, kernel_size=1)
            self.norm = nn.BatchNorm1d(out_channels)
            self.activation = nn.GELU()
            self.residual = nn.Identity() if in_channels == out_channels else nn.Conv1d(in_channels, out_channels, kernel_size=1)

        def forward(self, x):
            residual = self.residual(x)
            out = self.depthwise(x)
            out = self.pointwise(out)
            out = self.norm(out)
            out = self.activation(out)
            return out + residual


    class CanStudentTCN(nn.Module):
        def __init__(self, in_channels: int = 16, embedding_dim: int = 128) -> None:
            super().__init__()
            self.block1 = DepthwiseSeparableTemporalBlock(in_channels, 32, dilation=1)
            self.block2 = DepthwiseSeparableTemporalBlock(32, 64, dilation=2)
            self.block3 = DepthwiseSeparableTemporalBlock(64, embedding_dim, dilation=4)
            self.pool = nn.AdaptiveAvgPool1d(1)
            self.classifier = nn.Linear(embedding_dim, 1)

        def forward_features(self, x):
            x = self.block1(x)
            x = self.block2(x)
            x = self.block3(x)
            x = self.pool(x).squeeze(-1)
            return x

        def forward(self, x):
            features = self.forward_features(x)
            return self.classifier(features).squeeze(-1)
else:
    class CanStudentTCN:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            raise DependencyUnavailableError(
                "torch is required to instantiate CanStudentTCN. Install with `pip install -e .[ml]`."
            )
