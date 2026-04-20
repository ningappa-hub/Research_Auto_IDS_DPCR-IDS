"""Global reproducibility helpers."""

from __future__ import annotations

import os
import random


def set_global_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)

    try:
        import numpy as np  # type: ignore
    except ModuleNotFoundError:
        pass
    else:
        np.random.seed(seed)

    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        pass
    else:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
