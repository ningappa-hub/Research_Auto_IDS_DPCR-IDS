from dpcr_ids.training.pipeline import _resolve_training_cfg
from dpcr_ids.config import load_config

cfg = load_config('configs/research_pipeline.yaml')
can = _resolve_training_cfg(cfg, 'can')
eth = _resolve_training_cfg(cfg, 'ethernet')

print("CAN resolved config:")
print("  epochs   =", can["epochs"])
print("  patience =", can["early_stopping_patience"])
print("  lr       =", can["learning_rate"])
print("  smoothing=", can["label_smoothing"])

print("ETH resolved config:")
print("  epochs   =", eth["epochs"])
print("  patience =", eth["early_stopping_patience"])
print("  lr       =", eth["learning_rate"])
print("  smoothing=", eth["label_smoothing"])
print("  scheduler=", eth["lr_scheduler"])

assert can["epochs"] == 75,  f"CAN epochs wrong: {can['epochs']}"
assert can["early_stopping_patience"] == 12, f"CAN patience wrong"
assert eth["epochs"] == 50,  f"ETH epochs wrong: {eth['epochs']}"
assert eth["lr_scheduler"] == "cosine", f"ETH scheduler wrong"
print("\nAll config assertions PASSED.")

# Also verify boundary_gap fix in common.py
from dpcr_ids.data.common import temporal_split
items = list(range(100))
result = temporal_split(items, 0.7, 0.15, 0.15, boundary_gap=2)
# train ends at index 70, val starts at 72 (gap of 2), val ends at 85, test starts at 87
assert result["val"][0] == 72,  f"val start wrong: {result['val'][0]}"
assert result["test"][0] == 87, f"test start wrong: {result['test'][0]}"
print("temporal_split boundary_gap=2 PASSED.")
print("  val[0]  =", result["val"][0], "(expected 72)")
print("  test[0] =", result["test"][0], "(expected 87)")
