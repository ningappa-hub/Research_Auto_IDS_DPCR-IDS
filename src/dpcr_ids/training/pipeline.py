"""End-to-end command helpers for training, fusion, and evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dpcr_ids.config import load_config
from dpcr_ids.data.prepare import prepare_data
from dpcr_ids.export.onnx import export_model_to_onnx
from dpcr_ids.models import CanStudentTCN
from dpcr_ids.models import CanTeacherTransformer
from dpcr_ids.models import EthStudentCNN
from dpcr_ids.models import EthTeacherTransformer
from dpcr_ids.runtime.aggregator import DecisionAggregator
from dpcr_ids.runtime.router import ConfidenceRouter
from dpcr_ids.runtime.service import RuntimeIDSService
from dpcr_ids.training.calibration import TemperatureScaler
from dpcr_ids.training.calibration import fit_temperature_from_logits
from dpcr_ids.training.distillation import distillation_loss
from dpcr_ids.training.evaluate import evaluate_predictions
from dpcr_ids.training.fallback import ProtocolFallbackModel
from dpcr_ids.training.fusion_pipeline import FUSION_PROTOCOL
from dpcr_ids.training.fusion_pipeline import build_fusion_model
from dpcr_ids.training.fusion_pipeline import fusion_config
from dpcr_ids.training.fusion_pipeline import fusion_eval_extra
from dpcr_ids.training.fusion_pipeline import prepare_fusion_dataset
from dpcr_ids.training.fusion_pipeline import require_fusion_enabled
from dpcr_ids.training.metrics import sigmoid
from dpcr_ids.utils.deps import require_dependency
from dpcr_ids.utils.fs import ensure_dir
from dpcr_ids.utils.fs import read_jsonl
from dpcr_ids.utils.fs import write_json
from dpcr_ids.utils.seed import set_global_seed


MODEL_FILE_NAMES = {
    "student": "{protocol}_student.pt",
    "teacher": "{protocol}_teacher.pt",
    "distilled": "{protocol}_student_distilled.pt",
}


class JsonlTensorDataset:
    """Map-style dataset backed by random access into a prepared JSONL split."""

    def __init__(self, path: str | Path) -> None:
        self._torch = require_dependency("torch")
        self.path = Path(path)
        self._offsets = self._build_offsets()
        self._handle = None

    def _build_offsets(self) -> list[int]:
        offsets: list[int] = []
        with self.path.open("rb") as handle:
            while True:
                offset = handle.tell()
                line = handle.readline()
                if not line:
                    break
                if line.strip():
                    offsets.append(offset)
        return offsets

    def _file_handle(self):
        if self._handle is None or self._handle.closed:
            self._handle = self.path.open("r", encoding="utf-8")
        return self._handle

    def _load_row(self, index: int) -> dict[str, Any]:
        handle = self._file_handle()
        handle.seek(self._offsets[index])
        line = handle.readline()
        if not line:
            raise IndexError(f"JSONL row offset is invalid for {self.path}: {index}")
        return json.loads(line)

    def __len__(self) -> int:
        return len(self._offsets)

    def __getitem__(self, index: int):
        row = self._load_row(index)
        return (
            self._torch.tensor(row["features"], dtype=self._torch.float32),
            self._torch.tensor(float(row["label"]), dtype=self._torch.float32),
        )

    def close(self) -> None:
        if self._handle is not None and not self._handle.closed:
            self._handle.close()
        self._handle = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def _prepared_split_path(config: dict[str, Any], protocol: str, split: str) -> Path:
    return Path(config["artifacts_dir"]) / "prepared" / protocol / f"{split}.jsonl"


def _prepared_dataset(config: dict[str, Any], protocol: str, split: str) -> JsonlTensorDataset:
    return JsonlTensorDataset(_prepared_split_path(config, protocol, split))


def _close_dataset(dataset) -> None:
    close = getattr(dataset, "close", None)
    if callable(close):
        close()
    nested = getattr(dataset, "datasets", None)
    if nested is not None:
        for child in nested:
            _close_dataset(child)


def _build_model(config_or_protocol, protocol: str | None = None, teacher: bool = False):
    if protocol is None:
        config: dict[str, Any] = {}
        resolved_protocol = str(config_or_protocol)
    else:
        config = config_or_protocol
        resolved_protocol = protocol

    if resolved_protocol == "can":
        return CanTeacherTransformer() if teacher else CanStudentTCN()
    if resolved_protocol == "ethernet":
        return EthTeacherTransformer() if teacher else EthStudentCNN()
    if resolved_protocol == FUSION_PROTOCOL:
        if teacher:
            raise ValueError("Fusion does not define a teacher model in v1")
        return build_fusion_model(config)
    raise ValueError(f"Unsupported protocol: {resolved_protocol}")


def _model_path(config: dict[str, Any], protocol: str, kind: str) -> Path:
    models_dir = ensure_dir(Path(config["artifacts_dir"]) / "models")
    return models_dir / MODEL_FILE_NAMES[kind].format(protocol=protocol)


def _calibration_path(config: dict[str, Any], protocol: str) -> Path:
    return ensure_dir(Path(config["artifacts_dir"]) / "calibration") / f"{protocol}.json"


def _fallback_path(config: dict[str, Any], protocol: str) -> Path:
    return ensure_dir(Path(config["artifacts_dir"]) / "fallback") / f"{protocol}_rf.pkl"


def _artifact_is_current(model_path: Path, artifact_path: Path) -> bool:
    if not artifact_path.exists():
        return False
    return artifact_path.stat().st_mtime >= model_path.stat().st_mtime


def _artifact_matches_model(model_path: Path, metadata_path: Path) -> bool:
    if not metadata_path.exists():
        return False
    payload = load_config(str(metadata_path))
    return str(payload.get("source_model_path", "")) == str(model_path)


def _resolve_device(torch_module):
    return torch_module.device("cuda" if torch_module.cuda.is_available() else "cpu")


def _build_loader(dataset, batch_size: int, shuffle: bool, pin_memory: bool):
    dataset_mod = require_dependency("torch.utils.data")
    return dataset_mod.DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, pin_memory=pin_memory)


def _predict_dataset(
    model,
    dataset,
    protocol: str,
    batch_size: int = 256,
    device=None,
) -> tuple[list[int], list[float], list[float], list[list[float]]]:
    torch = require_dependency("torch")
    device = _resolve_device(torch) if device is None else device
    pin_memory = device.type == "cuda"
    loader = _build_loader(dataset, batch_size=batch_size, shuffle=False, pin_memory=pin_memory)
    model = model.to(device)
    model.eval()

    labels: list[int] = []
    logits: list[float] = []
    embeddings: list[list[float]] = []
    with torch.no_grad():
        for features, batch_labels in loader:
            features = features.to(device, non_blocking=pin_memory)
            batch_logits = model(features)
            batch_embeddings = model.forward_features(features)
            logits.extend(batch_logits.detach().cpu().tolist())
            embeddings.extend(batch_embeddings.detach().cpu().tolist())
            labels.extend(batch_labels.detach().cpu().int().tolist())

    probabilities = [float(sigmoid(logit)) for logit in logits]
    return labels, logits, probabilities, embeddings


def _collect_uncertain_embeddings(
    model,
    dataset,
    batch_size: int,
    device,
    tau_low: float,
    tau_high: float,
) -> tuple[list[list[float]], list[int]]:
    torch = require_dependency("torch")
    pin_memory = device.type == "cuda"
    loader = _build_loader(dataset, batch_size=batch_size, shuffle=False, pin_memory=pin_memory)
    model = model.to(device)
    model.eval()

    uncertain_features: list[list[float]] = []
    uncertain_labels: list[int] = []
    with torch.no_grad():
        for features, labels in loader:
            features = features.to(device, non_blocking=pin_memory)
            logits = model(features)
            embeddings = model.forward_features(features)
            probabilities = [float(sigmoid(logit)) for logit in logits.detach().cpu().tolist()]
            embedding_rows = embeddings.detach().cpu().tolist()
            label_rows = labels.detach().cpu().int().tolist()
            for probability, embedding, label in zip(probabilities, embedding_rows, label_rows):
                if tau_low < probability < tau_high:
                    uncertain_features.append(embedding)
                    uncertain_labels.append(label)

    return uncertain_features, uncertain_labels


def _load_exact_model(config: dict[str, Any], protocol: str, kind: str):
    torch = require_dependency("torch")
    path = _model_path(config, protocol, kind)
    if not path.exists():
        raise FileNotFoundError(f"Required checkpoint is missing for protocol {protocol}: {path}")
    checkpoint = torch.load(path, map_location="cpu")
    model = _build_model(config, protocol, teacher=(kind == "teacher"))
    model.load_state_dict(checkpoint["state_dict"])
    return model, path


def _load_trained_model(
    config: dict[str, Any],
    protocol: str,
    preferred_kind: str = "distilled",
    include_teacher: bool = False,
):
    torch = require_dependency("torch")
    if protocol == FUSION_PROTOCOL:
        candidate_kinds = ["student"]
    else:
        candidate_kinds: list[str] = []
        for kind in [preferred_kind, "student", "distilled"]:
            if kind not in candidate_kinds:
                candidate_kinds.append(kind)
        if include_teacher and "teacher" not in candidate_kinds:
            candidate_kinds.append("teacher")

    candidate_paths: list[tuple[float, int, str, Path]] = []
    for priority, kind in enumerate(candidate_kinds):
        path = _model_path(config, protocol, kind)
        if path.exists():
            candidate_paths.append((path.stat().st_mtime, -priority, kind, path))
    if not candidate_paths:
        raise FileNotFoundError(f"No trained model checkpoint found for protocol {protocol}")

    _, _, kind, path = max(candidate_paths)
    checkpoint = torch.load(path, map_location="cpu")
    model = _build_model(config, protocol, teacher=(kind == "teacher"))
    model.load_state_dict(checkpoint["state_dict"])
    return model, kind, path


def _prepare_fusion_if_needed(config: dict[str, Any], splits: tuple[str, ...]) -> None:
    prepare_fusion_dataset(
        config,
        splits,
        prepared_dataset=_prepared_dataset,
        load_exact_model=_load_exact_model,
        predict_dataset=_predict_dataset,
        resolve_device=_resolve_device,
        close_dataset=_close_dataset,
    )


def _train_binary_model(config: dict[str, Any], protocol: str, teacher: bool = False, distill_from=None) -> dict[str, Any]:
    torch = require_dependency("torch")
    set_global_seed(int(config.get("seed", 42)))
    device = _resolve_device(torch)
    pin_memory = device.type == "cuda"
    batch_size = int(config["training"]["batch_size"])
    epochs = int(config["training"]["epochs"])
    patience = int(config["training"].get("early_stopping_patience", epochs))
    patience = epochs if patience <= 0 else patience
    distill_cfg = config["training"].get("distillation", {"alpha": 0.5, "temperature": 4.0})

    if protocol == FUSION_PROTOCOL:
        if teacher:
            raise ValueError("Fusion does not support teacher training in v1")
        if distill_from is not None:
            raise ValueError("Fusion does not support distillation in v1")
        require_fusion_enabled(config)
        _prepare_fusion_if_needed(config, ("train", "val"))

    train_dataset = _prepared_dataset(config, protocol, "train")
    val_dataset = _prepared_dataset(config, protocol, "val")
    try:
        model = _build_model(config, protocol, teacher=teacher).to(device)
        if distill_from is not None:
            distill_from = distill_from.to(device)
            distill_from.eval()

        train_loader = _build_loader(train_dataset, batch_size=batch_size, shuffle=True, pin_memory=pin_memory)
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=float(config["training"]["learning_rate"]),
            weight_decay=float(config["training"]["weight_decay"]),
        )
        
        pos_weight = None
        if distill_from is None:
            num_positives = 0
            for _, batch_labels in train_loader:
                num_positives += int((batch_labels == 1).sum())
            num_negatives = len(train_dataset) - num_positives
            if num_positives > 0 and num_negatives > 0:
                weight_val = float(num_negatives) / float(num_positives)
                pos_weight = torch.tensor([weight_val], device=device)
                print(f"Applying BCE pos_weight={weight_val:.4f} for {protocol}")

        criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

        best_metric = -1.0
        best_state = None
        best_epoch = 0
        epochs_without_improvement = 0
        epochs_ran = 0

        for epoch in range(epochs):
            model.train()
            epoch_loss = 0.0
            batch_count = 0
            for features, labels in train_loader:
                features = features.to(device, non_blocking=pin_memory)
                labels = labels.to(device, non_blocking=pin_memory)
                optimizer.zero_grad(set_to_none=True)
                logits = model(features)
                if distill_from is None:
                    loss = criterion(logits, labels)
                else:
                    with torch.no_grad():
                        teacher_logits = distill_from(features)
                    loss = distillation_loss(
                        logits,
                        teacher_logits,
                        labels,
                        alpha=float(distill_cfg["alpha"]),
                        temperature=float(distill_cfg["temperature"]),
                    )
                loss.backward()
                optimizer.step()
                epoch_loss += float(loss.detach().cpu().item())
                batch_count += 1

            epochs_ran = epoch + 1
            val_labels, _, val_probs, _ = _predict_dataset(
                model,
                val_dataset,
                protocol,
                batch_size=max(batch_size, 256),
                device=device,
            )
            val_report = evaluate_predictions(val_labels, val_probs)
            val_metric = float(val_report.get("auc_pr", val_report.get("f1", 0.0)))
            if val_metric > best_metric + 1e-12:
                best_metric = val_metric
                best_epoch = epoch + 1
                epochs_without_improvement = 0
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            else:
                epochs_without_improvement += 1

            print(
                f"epoch={epoch + 1}/{epochs} device={device} protocol={protocol} "
                f"loss={epoch_loss / max(batch_count, 1):.6f} val_auc_pr={val_metric:.6f} "
                f"best_epoch={best_epoch} patience_used={epochs_without_improvement}/{patience}"
            )
            if epochs_without_improvement >= patience:
                print(
                    f"early_stop device={device} protocol={protocol} "
                    f"epoch={epoch + 1} best_epoch={best_epoch} best_auc_pr={best_metric:.6f}"
                )
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        kind = "teacher" if teacher else ("distilled" if distill_from is not None else "student")
        output_path = _model_path(config, protocol, kind)
        torch.save(
            {
                "protocol": protocol,
                "kind": kind,
                "state_dict": model.state_dict(),
                "best_epoch": best_epoch,
                "epochs_ran": epochs_ran,
            },
            output_path,
        )
        labels, _, probabilities, _ = _predict_dataset(
            model,
            val_dataset,
            protocol,
            batch_size=max(batch_size, 256),
            device=device,
        )
        report = evaluate_predictions(labels, probabilities)
        summary = {
            "protocol": protocol,
            "kind": kind,
            "checkpoint": str(output_path),
            "device": str(device),
            "epochs_configured": epochs,
            "epochs_ran": epochs_ran,
            "best_epoch": best_epoch,
            "early_stopped": epochs_ran < epochs,
            "validation": report,
        }
        write_json(output_path.with_suffix(".json"), summary)
        return summary
    finally:
        _close_dataset(train_dataset)
        _close_dataset(val_dataset)


def prepare_data_from_path(config_path: str, protocol: str | None = None) -> dict[str, Any]:
    return prepare_data(load_config(config_path), protocol=protocol)


def train_student_from_path(config_path: str, protocol: str) -> dict[str, Any]:
    return _train_binary_model(load_config(config_path), protocol=protocol, teacher=False, distill_from=None)


def train_teacher_from_path(config_path: str, protocol: str) -> dict[str, Any]:
    if protocol == FUSION_PROTOCOL:
        raise ValueError("Fusion does not support teacher training in v1")
    return _train_binary_model(load_config(config_path), protocol=protocol, teacher=True, distill_from=None)


def distill_from_path(config_path: str, protocol: str) -> dict[str, Any]:
    if protocol == FUSION_PROTOCOL:
        raise ValueError("Fusion does not support distillation in v1")
    config = load_config(config_path)
    teacher_model, _, _ = _load_trained_model(config, protocol, preferred_kind="teacher", include_teacher=True)
    teacher_model.eval()
    return _train_binary_model(config, protocol=protocol, teacher=False, distill_from=teacher_model)


def calibrate_from_path(config_path: str, protocol: str) -> dict[str, Any]:
    config = load_config(config_path)
    if protocol == FUSION_PROTOCOL:
        require_fusion_enabled(config)
        _prepare_fusion_if_needed(config, ("val",))
    model, model_kind, model_path = _load_trained_model(config, protocol)
    val_dataset = _prepared_dataset(config, protocol, "val")
    try:
        labels, logits, probabilities, _ = _predict_dataset(model, val_dataset, protocol)
        scaler, artifact = fit_temperature_from_logits(logits, labels)
        artifact.protocol = protocol
        calibration_path = _calibration_path(config, protocol)
        write_json(
            calibration_path,
            {
                "protocol": protocol,
                "temperature": scaler.temperature,
                "ece_before": artifact.ece_before,
                "ece_after": artifact.ece_after,
                "sample_count": len(labels),
                "model_kind": model_kind,
                "source_model_path": str(model_path),
            },
        )
        return {
            "protocol": protocol,
            "model_kind": model_kind,
            "temperature": scaler.temperature,
            "ece_before": artifact.ece_before,
            "ece_after": artifact.ece_after,
            "calibration_path": str(calibration_path),
            "baseline_validation": evaluate_predictions(labels, probabilities),
        }
    finally:
        _close_dataset(val_dataset)


def train_fallback_from_path(config_path: str, protocol: str) -> dict[str, Any]:
    if protocol == FUSION_PROTOCOL:
        raise ValueError("Fusion does not support RandomForest fallback training in v1")
    dataset_mod = require_dependency("torch.utils.data")
    config = load_config(config_path)
    model, model_kind, model_path = _load_trained_model(config, protocol)
    routing_cfg = config["routing"]
    device = _resolve_device(require_dependency("torch"))
    train_dataset = _prepared_dataset(config, protocol, "train")
    val_dataset = _prepared_dataset(config, protocol, "val")
    combined_dataset = dataset_mod.ConcatDataset([train_dataset, val_dataset])
    try:
        uncertain_features, uncertain_labels = _collect_uncertain_embeddings(
            model,
            combined_dataset,
            batch_size=max(int(config["training"]["batch_size"]), 256),
            device=device,
            tau_low=float(routing_cfg["tau_low"]),
            tau_high=float(routing_cfg["tau_high"]),
        )
        if not uncertain_features:
            raise ValueError("No uncertain samples were found for fallback training")
        fallback = ProtocolFallbackModel()
        fallback.fit(uncertain_features, uncertain_labels)
        output_path = _fallback_path(config, protocol)
        fallback.save(output_path)
        metadata = {
            "protocol": protocol,
            "model_kind": model_kind,
            "source_model_path": str(model_path),
            "fallback_path": str(output_path),
            "uncertain_sample_count": len(uncertain_features),
        }
        write_json(output_path.with_suffix(".json"), metadata)
        return metadata
    finally:
        _close_dataset(combined_dataset)


def evaluate_from_path(config_path: str, protocol: str) -> dict[str, Any]:
    config = load_config(config_path)
    if protocol == FUSION_PROTOCOL:
        require_fusion_enabled(config)
        _prepare_fusion_if_needed(config, ("test",))
    model, model_kind, model_path = _load_trained_model(config, protocol)
    test_dataset = _prepared_dataset(config, protocol, "test")
    try:
        labels, _, probabilities, embeddings = _predict_dataset(model, test_dataset, protocol)
        calibration_path = _calibration_path(config, protocol)
        calibration_used = False
        scaler = TemperatureScaler(1.0)
        if _artifact_is_current(model_path, calibration_path) and _artifact_matches_model(model_path, calibration_path):
            payload = load_config(calibration_path)
            scaler = TemperatureScaler(float(payload["temperature"]))
            calibration_used = True
        calibrated_probs = [scaler.transform_probability(probability) for probability in probabilities]

        if protocol == FUSION_PROTOCOL:
            report = evaluate_predictions(
                labels,
                calibrated_probs,
                extra={
                    **fusion_eval_extra(config, "test"),
                    "predicted_attack_count": sum(1 for probability in calibrated_probs if probability >= 0.5),
                },
            )
            output_path = ensure_dir(Path(config["artifacts_dir"]) / "evaluations") / f"{protocol}.json"
            write_json(output_path, report)
            return {
                "protocol": protocol,
                "model_kind": model_kind,
                "calibration_used": calibration_used,
                "evaluation_path": str(output_path),
                "report": report,
            }

        router = ConfidenceRouter(float(config["routing"]["tau_low"]), float(config["routing"]["tau_high"]))
        fallback_model = None
        fallback_path = _fallback_path(config, protocol)
        fallback_used = False
        fallback_meta_path = fallback_path.with_suffix(".json")
        if _artifact_is_current(model_path, fallback_path) and _artifact_matches_model(model_path, fallback_meta_path):
            fallback_model = ProtocolFallbackModel.load(fallback_path)
            fallback_used = True

        paths: list[str] = []
        final_probs: list[float] = []
        decisions: list[int] = []
        escalate_count = 0
        for raw_prob, cal_prob, embedding in zip(probabilities, calibrated_probs, embeddings):
            route = router.route(cal_prob, p_attack_raw=raw_prob)
            paths.append(route.path)
            if route.decision is not None:
                final_probs.append(cal_prob)
                decisions.append(1 if route.decision == "ATTACK" else 0)
                continue
            if fallback_model is None:
                final_probs.append(cal_prob)
                decisions.append(1)
                escalate_count += 1
                continue
            fallback_decision = fallback_model.predict_decision(
                embedding,
                low=float(config["routing"]["fallback_uncertainty_low"]),
                high=float(config["routing"]["fallback_uncertainty_high"]),
            )
            final_probs.append(fallback_decision.probability)
            decisions.append(1 if fallback_decision.decision in {"ATTACK", "ESCALATE"} else 0)
            if fallback_decision.escalate:
                escalate_count += 1

        report = evaluate_predictions(
            labels,
            final_probs,
            paths=paths,
            extra={"escalate_count": escalate_count, "predicted_attack_count": sum(decisions)},
        )
        output_path = ensure_dir(Path(config["artifacts_dir"]) / "evaluations") / f"{protocol}.json"
        write_json(output_path, report)
        return {
            "protocol": protocol,
            "model_kind": model_kind,
            "calibration_used": calibration_used,
            "fallback_used": fallback_used,
            "evaluation_path": str(output_path),
            "report": report,
        }
    finally:
        _close_dataset(test_dataset)


def export_onnx_from_path(config_path: str, protocol: str) -> dict[str, Any]:
    config = load_config(config_path)
    model, _, _ = _load_trained_model(config, protocol)
    if protocol == FUSION_PROTOCOL:
        payload = fusion_config(config)
        input_shape = (1, 2, int(payload["expert_dim"]))
    else:
        input_shape = (1, 16, 100) if protocol == "can" else (1, 4, 32, 32)
    output_path = ensure_dir(Path(config["artifacts_dir"]) / "export") / f"{protocol}_student.onnx"
    export_model_to_onnx(model, input_shape=input_shape, output_path=output_path)
    return {"protocol": protocol, "onnx_path": str(output_path), "input_shape": list(input_shape)}


def build_runtime_service(config_path: str) -> RuntimeIDSService:
    config = load_config(config_path)
    routing_cfg = config["routing"]
    runtime_cfg = config.get("runtime", {})
    routers = {
        "can": ConfidenceRouter(float(routing_cfg["tau_low"]), float(routing_cfg["tau_high"])),
        "ethernet": ConfidenceRouter(float(routing_cfg["tau_low"]), float(routing_cfg["tau_high"])),
    }
    aggregator = DecisionAggregator(bucket_ms=int(routing_cfg.get("bucket_ms", 250)))
    return RuntimeIDSService(
        routers=routers,
        aggregator=aggregator,
        deadline_ms=float(runtime_cfg.get("deadline_ms", 20.0)),
        fail_open=bool(runtime_cfg.get("fail_open", True)),
        health_log_path=runtime_cfg.get("health_log_path"),
    )


def serve_runtime_from_path(
    config_path: str,
    protocol: str | None = None,
    probability: float | None = None,
    timestamp: float | None = None,
) -> dict[str, Any]:
    service = build_runtime_service(config_path)
    if protocol is None or probability is None:
        return {"status": "ready", "protocols": sorted(service.routers.keys()), "deadline_ms": service.deadline_ms}
    alert = service.process_event(protocol=protocol, raw_probability=probability, calibrated_probability=probability, timestamp=timestamp)
    aggregated = [item.to_dict() for item in service.aggregator.flush()]
    return {"alert": alert.to_dict(), "aggregated": aggregated}
