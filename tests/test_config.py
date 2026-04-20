from __future__ import annotations

import unittest
from pathlib import Path

from dpcr_ids.config import deep_merge
from dpcr_ids.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_json_compatible_yaml(self) -> None:
        config = load_config(Path("configs/research_pipeline.yaml"))
        self.assertEqual(config["experiment_name"], "dpcr_ids_research_v1")
        self.assertEqual(config["splits"]["train"], 0.7)

    def test_deep_merge(self) -> None:
        merged = deep_merge({"a": {"b": 1, "c": 2}}, {"a": {"c": 3}, "d": 4})
        self.assertEqual(merged, {"a": {"b": 1, "c": 3}, "d": 4})


if __name__ == "__main__":
    unittest.main()
