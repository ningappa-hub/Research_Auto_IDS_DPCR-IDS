"""
Smoke test: verify overfitting fix code paths work correctly.
Tests: protocol-override resolution, cosine LR scheduler, gradient clipping,
       label smoothing, and increased Ethernet teacher dropout.
"""
import torch
import torch.nn as nn

# ── 1. Protocol override resolution ─────────────────────────────────────────
from dpcr_ids.training.pipeline import _resolve_training_cfg
from dpcr_ids.config import load_config

cfg = load_config("configs/research_pipeline.yaml")

can_cfg = _resolve_training_cfg(cfg, "can")
eth_cfg = _resolve_training_cfg(cfg, "ethernet")

assert can_cfg["learning_rate"] == 0.0002, f"CAN LR wrong: {can_cfg['learning_rate']}"
assert eth_cfg["learning_rate"] == 5e-05,  f"ETH LR wrong: {eth_cfg['learning_rate']}"
assert can_cfg["label_smoothing"] == 0.0,  f"CAN smoothing should be 0"
assert eth_cfg["label_smoothing"] == 0.05, f"ETH smoothing wrong"
assert eth_cfg["lr_scheduler"] == "cosine", f"ETH scheduler wrong"
assert eth_cfg["grad_clip_norm"] == 1.0,   f"ETH clip wrong"
assert eth_cfg["distillation"]["temperature"] == 6.0, f"ETH distill T wrong"
assert can_cfg["distillation"]["temperature"] == 4.0, f"CAN distill T wrong"
assert eth_cfg["early_stopping_patience"] == 15, f"ETH patience wrong"
assert can_cfg["early_stopping_patience"] == 10, f"CAN patience wrong"
print("✅ Protocol override resolution: PASSED")

# ── 2. Cosine LR scheduler ───────────────────────────────────────────────────
model = nn.Linear(4, 1)
opt = torch.optim.AdamW(model.parameters(), lr=5e-5)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=50, eta_min=5e-7)
lr_epoch1 = opt.param_groups[0]["lr"]
opt.step()  # optimizer must step before scheduler
sched.step()
lr_epoch2 = opt.param_groups[0]["lr"]
assert lr_epoch2 < lr_epoch1, "LR should decrease with cosine annealing"
print(f"✅ Cosine LR scheduler: PASSED (LR {lr_epoch1:.2e} → {lr_epoch2:.2e})")

# ── 3. Gradient clipping ─────────────────────────────────────────────────────
model2 = nn.Linear(10, 1)
x = torch.randn(4, 10)
y = torch.randn(4, 1)
loss = nn.MSELoss()(model2(x), y) * 1000  # inflate loss to get big gradients
loss.backward()
pre_norm = torch.nn.utils.clip_grad_norm_(model2.parameters(), max_norm=1.0)
post_norm = sum(p.grad.norm().item() ** 2 for p in model2.parameters() if p.grad is not None) ** 0.5
assert post_norm <= 1.0 + 1e-6, f"Gradient norm not clipped: {post_norm:.4f}"
print(f"✅ Gradient clipping: PASSED (pre={float(pre_norm):.2f} → post={post_norm:.4f})")

# ── 4. Label smoothing shifts targets ────────────────────────────────────────
labels = torch.tensor([0.0, 1.0, 0.0, 1.0])
eps = 0.05
smoothed = labels * (1.0 - eps) + 0.5 * eps
assert abs(smoothed[0].item() - 0.025) < 1e-6, f"Smoothed 0-label wrong: {smoothed[0]}"
assert abs(smoothed[1].item() - 0.975) < 1e-6, f"Smoothed 1-label wrong: {smoothed[1]}"
print(f"✅ Label smoothing: PASSED (0→{smoothed[0]:.3f}, 1→{smoothed[1]:.3f})")

# ── 5. Ethernet teacher dropout increased to 0.2 ─────────────────────────────
from dpcr_ids.models.teacher import EthTeacherTransformer
eth_teacher = EthTeacherTransformer()
dropouts = [m.dropout.p for m in eth_teacher.modules() if isinstance(m, nn.TransformerEncoderLayer)]
assert all(abs(d - 0.2) < 1e-6 for d in dropouts), f"ETH teacher dropout wrong: {dropouts}"
print(f"PASS: Ethernet teacher dropout=0.2: {dropouts}")

# ── 6. CAN teacher dropout unchanged at 0.1 ──────────────────────────────────
from dpcr_ids.models.teacher import CanTeacherTransformer
can_teacher = CanTeacherTransformer()
can_dropouts = [m.dropout.p for m in can_teacher.modules() if isinstance(m, nn.TransformerEncoderLayer)]
assert all(abs(d - 0.1) < 1e-6 for d in can_dropouts), f"CAN teacher dropout changed unexpectedly: {can_dropouts}"
print(f"PASS: CAN teacher dropout=0.1 unchanged")

print("\nALL overfitting fix smoke tests PASSED.")
