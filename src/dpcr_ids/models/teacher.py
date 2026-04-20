"""Protocol-specific teacher models."""

from __future__ import annotations

from dpcr_ids.exceptions import DependencyUnavailableError

try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError:
    torch = None
    nn = None


if nn is not None:
    class CanTeacherTransformer(nn.Module):
        def __init__(self, in_channels: int = 16, d_model: int = 128, nhead: int = 8, num_layers: int = 4) -> None:
            super().__init__()
            self.input_proj = nn.Linear(in_channels, d_model)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=d_model * 4,
                batch_first=True,
                dropout=0.1,
                activation="gelu",
            )
            self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
            self.classifier = nn.Linear(d_model, 1)

        def forward_features(self, x):
            x = x.transpose(1, 2)
            x = self.input_proj(x)
            x = self.encoder(x)
            return x.mean(dim=1)

        def forward(self, x):
            return self.classifier(self.forward_features(x)).squeeze(-1)


    class EthTeacherTransformer(nn.Module):
        def __init__(self, in_channels: int = 3, d_model: int = 128, nhead: int = 8, num_layers: int = 4) -> None:
            super().__init__()
            self.patch_embed = nn.Conv2d(in_channels, d_model, kernel_size=4, stride=4)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=d_model * 4,
                batch_first=True,
                dropout=0.1,
                activation="gelu",
            )
            self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
            self.classifier = nn.Linear(d_model, 1)

        def forward_features(self, x):
            x = self.patch_embed(x)
            x = x.flatten(2).transpose(1, 2)
            x = self.encoder(x)
            return x.mean(dim=1)

        def forward(self, x):
            return self.classifier(self.forward_features(x)).squeeze(-1)
else:
    class CanTeacherTransformer:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            raise DependencyUnavailableError(
                "torch is required to instantiate CanTeacherTransformer. Install with `pip install -e .[ml]`."
            )


    class EthTeacherTransformer:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            raise DependencyUnavailableError(
                "torch is required to instantiate EthTeacherTransformer. Install with `pip install -e .[ml]`."
            )
