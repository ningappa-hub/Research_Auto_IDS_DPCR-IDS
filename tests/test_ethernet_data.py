from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dpcr_ids.data.ethernet import build_ethernet_samples
from dpcr_ids.data.ethernet import bytes_to_byte_image
from dpcr_ids.data.ethernet import infer_dataset_variant
from dpcr_ids.data.ethernet import paired_smoke_adapter
from dpcr_ids.data.ethernet import prepare_ethernet_dataset
from dpcr_ids.data.ethernet import read_label_csv
from dpcr_ids.data.ethernet import resolve_pcap_for_label_csv

LABELS = Path("tests/fixtures/ethernet/labels.csv")
SURROGATE_LABELS = Path("tests/fixtures/ethernet/tow_like.csv")
PAIRED = Path("tests/fixtures/ethernet/paired")


class EthernetDataTests(unittest.TestCase):
    def test_read_label_csv(self) -> None:
        labels = read_label_csv(LABELS)
        self.assertEqual(len(labels), 3)
        self.assertEqual(labels[1].label, 1)
        self.assertEqual(labels[1].attack_type, "injection")

    def test_read_surrogate_label_csv(self) -> None:
        labels = read_label_csv(SURROGATE_LABELS)
        self.assertEqual(len(labels), 3)
        self.assertEqual(labels[0].frame_idx, 0)
        self.assertEqual(labels[0].label, 0)
        self.assertEqual(labels[1].protocol, "avtp")
        self.assertEqual(labels[1].attack_type, "avtp_background")
        self.assertEqual(labels[2].label, 1)
        self.assertEqual(labels[2].protocol, "avtp")
        self.assertEqual(labels[2].attack_type, "frame_injection")

    def test_read_official_tow_ids_label_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            label_file = root / "y_train.csv"
            label_file.write_text("1,Normal,Normal\n2,Abnormal,C_D\n3,Abnormal,P_I\n", encoding="utf-8")

            labels = read_label_csv(label_file)
            self.assertEqual(len(labels), 3)
            self.assertEqual(labels[0].frame_idx, 0)
            self.assertEqual(labels[0].label, 0)
            self.assertEqual(labels[0].attack_type, "normal")
            self.assertEqual(labels[1].frame_idx, 1)
            self.assertEqual(labels[1].label, 1)
            self.assertEqual(labels[1].protocol, "udp")
            self.assertEqual(labels[1].attack_type, "can_dos_tunneled")
            self.assertEqual(labels[1].raw_label, "c_d")
            self.assertEqual(labels[2].protocol, "gptp")
            self.assertEqual(labels[2].attack_type, "ptp_injection")

    def test_official_tow_ids_path_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dataset_dir = root / "TOW-IDS_DATASET"
            dataset_dir.mkdir()
            train_label = dataset_dir / "y_train.csv"
            test_label = dataset_dir / "y_test.csv"
            train_pcap = dataset_dir / "Automotive_Ethernet_with_Attack_original_10_17_19_50_training.pcap"
            test_pcap = dataset_dir / "Automotive_Ethernet_with_Attack_original_10_17_20_04_test.pcap"
            train_label.write_text("1,Normal,Normal\n", encoding="utf-8")
            test_label.write_text("1,Normal,Normal\n", encoding="utf-8")
            train_pcap.write_bytes(b"")
            test_pcap.write_bytes(b"")

            self.assertEqual(resolve_pcap_for_label_csv(train_label, root), train_pcap)
            self.assertEqual(resolve_pcap_for_label_csv(test_label, root), test_pcap)
            self.assertEqual(infer_dataset_variant(train_label), "official_tow_ids")

    def test_prepare_official_tow_ids_streams_splits(self) -> None:
        try:
            from scapy.all import Ether, Raw, wrpcap
        except ModuleNotFoundError:
            self.skipTest("scapy is required for Ethernet PCAP tests")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dataset_dir = root / "TOW-IDS_DATASET"
            output_dir = root / "prepared"
            smoke_dir = root / "smoke"
            dataset_dir.mkdir()
            smoke_dir.mkdir()
            train_label = dataset_dir / "y_train.csv"
            test_label = dataset_dir / "y_test.csv"
            train_pcap = dataset_dir / "Automotive_Ethernet_with_Attack_original_10_17_19_50_training.pcap"
            test_pcap = dataset_dir / "Automotive_Ethernet_with_Attack_original_10_17_20_04_test.pcap"
            train_label.write_text(
                "1,Normal,Normal\n2,Abnormal,C_D\n3,Normal,Normal\n4,Abnormal,P_I\n",
                encoding="utf-8",
            )
            test_label.write_text("1,Normal,Normal\n2,Abnormal,F_I\n", encoding="utf-8")
            train_packets = [Ether() / Raw(bytes([idx, idx + 1, idx + 2])) for idx in range(4)]
            test_packets = [Ether() / Raw(bytes([idx, idx + 1, idx + 2])) for idx in range(2)]
            wrpcap(str(train_pcap), train_packets)
            wrpcap(str(test_pcap), test_packets)

            report = prepare_ethernet_dataset(
                primary_dataset_root=root,
                smoke_dataset_root=smoke_dir,
                output_dir=output_dir,
                split_cfg={"train": 0.5, "val": 0.25, "test": 0.25},
                payload_bytes=16,
                frame_height=4,
                frame_width=4,
            )

            self.assertFalse(report["qa"]["surrogate_only"])
            self.assertEqual(report["qa"]["storage_mode"], "streamed_jsonl")
            self.assertEqual(report["qa"]["totals"], {"train": 2, "val": 2, "test": 2})
            self.assertEqual(report["manifests"]["train"]["feature_shape"], [3, 4, 4])
            self.assertEqual(report["manifests"]["test"]["labels"], {"0": 1, "1": 1})

    def test_byte_image_encoding_shape(self) -> None:
        payload = bytes([0, 255, 10, 20])
        prev = bytes([0, 0, 5, 10])
        image = bytes_to_byte_image(payload, prev_payload=prev, payload_bytes=16, frame_height=4, frame_width=4)
        self.assertEqual(len(image), 3)
        self.assertEqual(len(image[0]), 4)
        self.assertEqual(len(image[0][0]), 4)
        self.assertAlmostEqual(image[0][0][1], 1.0)
        self.assertGreater(image[1][0][2], 0.0)

    def test_build_samples_and_smoke_pairs(self) -> None:
        labels = read_label_csv(LABELS)
        frames = [
            {"frame_idx": 0, "payload": bytes([1, 2, 3]), "protocol": "avtp"},
            {"frame_idx": 1, "payload": bytes([1, 3, 4]), "protocol": "avtp"},
            {"frame_idx": 2, "payload": bytes([9, 8, 7]), "protocol": "gptp"},
        ]
        samples = build_ethernet_samples(frames, labels, payload_bytes=16, frame_height=4, frame_width=4)
        self.assertEqual(len(samples), 3)
        self.assertEqual(samples[1].label, 1)

        pairs = paired_smoke_adapter(PAIRED)
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0]["original"].endswith("_original.pcap"))

    def test_variant_and_path_resolution(self) -> None:
        root = Path('datasets/tow-ids')
        label_file = root / 'data' / 'features' / 'tow_like.csv'
        pcap_file = resolve_pcap_for_label_csv(label_file, root)
        self.assertIsNotNone(pcap_file)
        self.assertTrue(str(pcap_file).endswith('tow_like.pcap'))
        self.assertEqual(infer_dataset_variant(label_file), 'surrogate_tow_like')


if __name__ == "__main__":
    unittest.main()
