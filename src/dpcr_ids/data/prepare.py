"""Top-level dataset preparation entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dpcr_ids.config import require_keys
from dpcr_ids.data.can import prepare_can_dataset
from dpcr_ids.data.ethernet import prepare_ethernet_dataset
from dpcr_ids.utils.fs import ensure_dir
from dpcr_ids.utils.fs import write_json
from dpcr_ids.utils.seed import set_global_seed


_SPLITS = ("train", "val", "test")


def _is_prepared(prepared_dir: Path, protocol: str, source_roots: list[Path]) -> bool:
    """Return True if all split JSONL files exist and are newer than every source file.

    This prevents redundant re-preparation when the raw datasets have not changed.
    Re-preparation is still triggered automatically when:
      - Any split file is missing
      - Any source file is newer than the prepared files (dataset updated)
    """
    split_files = [prepared_dir / protocol / f"{split}.jsonl" for split in _SPLITS]
    if not all(f.exists() for f in split_files):
        return False
    oldest_prepared = min(f.stat().st_mtime for f in split_files)
    for root in source_roots:
        if not root.exists():
            continue
        for src in root.rglob("*"):
            if src.is_file() and src.stat().st_mtime > oldest_prepared:
                print(f"prepare_data: source newer than prepared — re-preparing {protocol} (changed: {src.name})")
                return False
    return True


def prepare_data(config: dict[str, Any], protocol: str | None = None) -> dict[str, Any]:
    require_keys(config, ["experiment_name", "artifacts_dir", "splits", "can", "ethernet"])
    if protocol not in {None, "can", "ethernet"}:
        raise ValueError("prepare-data protocol must be one of: can, ethernet, or omitted for all")
    set_global_seed(int(config.get("seed", 42)))
    artifacts_dir = ensure_dir(config["artifacts_dir"])
    prepared_dir = ensure_dir(Path(artifacts_dir) / "prepared")

    can_cfg = config["can"]
    eth_cfg = config["ethernet"]
    splits = config["splits"]

    report: dict[str, Any] = {
        "experiment_name": config["experiment_name"],
        "artifacts_dir": str(artifacts_dir),
        "prepared_dir": str(prepared_dir),
    }

    if protocol in {None, "can"}:
        can_sources = [Path(can_cfg["dataset_root"])]
        if _is_prepared(prepared_dir, "can", can_sources):
            print("prepare_data: CAN data already up-to-date — skipping.")
            report["can"] = {"skipped": True, "prepared_dir": str(prepared_dir / "can")}
        else:
            report["can"] = prepare_can_dataset(
                dataset_root=can_cfg["dataset_root"],
                files=can_cfg["files"],
                output_dir=prepared_dir,
                split_cfg=splits,
                window_size=int(can_cfg["window_size"]),
                stride=int(can_cfg["stride"]),
            )

    if protocol in {None, "ethernet"}:
        eth_sources = [
            Path(eth_cfg["primary_dataset_root"]),
            Path(eth_cfg["smoke_dataset_root"]),
        ]
        if _is_prepared(prepared_dir, "ethernet", eth_sources):
            print("prepare_data: Ethernet data already up-to-date — skipping.")
            report["ethernet"] = {"skipped": True, "prepared_dir": str(prepared_dir / "ethernet")}
        else:
            report["ethernet"] = prepare_ethernet_dataset(
                primary_dataset_root=eth_cfg["primary_dataset_root"],
                smoke_dataset_root=eth_cfg["smoke_dataset_root"],
                output_dir=prepared_dir,
                split_cfg=splits,
                payload_bytes=int(eth_cfg["payload_bytes"]),
                frame_height=int(eth_cfg["frame_height"]),
                frame_width=int(eth_cfg["frame_width"]),
                label_csv_glob=str(eth_cfg.get("label_csv_glob", "*.csv")),
            )

    write_json(Path(artifacts_dir) / "prepare_data_report.json", report)
    return report
