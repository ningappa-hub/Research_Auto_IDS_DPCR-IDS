"""Allow dpcr_ids to be invoked as a module: python -m dpcr_ids"""

from __future__ import annotations

from dpcr_ids.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
