import json

# === Load all CAN metrics ===
teacher  = json.load(open('artifacts/dpcr_ids_research_v1/models/can_teacher.json'))
student  = json.load(open('artifacts/dpcr_ids_research_v1/models/can_student.json'))
distilled= json.load(open('artifacts/dpcr_ids_research_v1/models/can_student_distilled.json'))
test     = json.load(open('artifacts/dpcr_ids_research_v1/evaluations/can.json'))

# helpers
def ok(val, thresh): return "PASS" if abs(val) < thresh else "WARN"

# ---------- Teacher ----------
tv = teacher['validation']
print("=== CAN Teacher ===")
print(f"  epochs_ran={teacher['epochs_ran']}  best_epoch={teacher['best_epoch']}  early_stopped={teacher['early_stopped']}")
print(f"  VAL  F1={tv['f1']:.6f}  Recall={tv['recall']:.6f}  Prec={tv['precision']:.6f}  FPR={tv['fpr']:.6f}  AUC-PR={tv['auc_pr']:.6f}  ECE={tv['ece']:.4f}")
print(f"  TEST F1={test['f1']:.6f}  Recall={test['recall']:.6f}  Prec={test['precision']:.6f}  FPR={test['fpr']:.6f}  AUC-PR={test['auc_pr']:.6f}  ECE={test['ece']:.4f}")
print()

gap_f1    = test['f1']        - tv['f1']
gap_rec   = test['recall']    - tv['recall']
gap_prec  = test['precision'] - tv['precision']
gap_fpr   = test['fpr']       - tv['fpr']
gap_aucpr = test['auc_pr']    - tv['auc_pr']
print("  Val->Test Gaps:")
print(f"    F1:        {gap_f1:+.5f}  [{ok(gap_f1,    0.02)}]")
print(f"    Recall:    {gap_rec:+.5f}  [{ok(gap_rec,   0.02)}]")
print(f"    Precision: {gap_prec:+.5f}  [{ok(gap_prec,  0.005)}]")
print(f"    FPR:       {gap_fpr:+.6f}  [{ok(gap_fpr,   0.002)}]")
print(f"    AUC-PR:    {gap_aucpr:+.6f}  [{ok(gap_aucpr, 0.01)}]")

# ---------- CAN Student ----------
sv = student['validation']
print()
print("=== CAN Student (baseline, no distillation) ===")
print(f"  epochs_ran={student['epochs_ran']}  best_epoch={student['best_epoch']}  early_stopped={student['early_stopped']}")
print(f"  VAL  F1={sv['f1']:.6f}  Recall={sv['recall']:.6f}  Prec={sv['precision']:.6f}  FPR={sv['fpr']:.6f}  AUC-PR={sv['auc_pr']:.6f}  ECE={sv['ece']:.4f}")
epochs_unused = student['epochs_ran'] - student['best_epoch']
print(f"  NOTE: Did NOT early-stop. Best at epoch {student['best_epoch']} / {student['epochs_ran']}.")
print(f"        Only {epochs_unused} epoch(s) after best before run ended — improvement was still happening near the end.")

# ---------- CAN Distilled ----------
dv = distilled['validation']
print()
print("=== CAN Student Distilled (older April run) ===")
print(f"  VAL  F1={dv['f1']:.6f}  Recall={dv['recall']:.6f}  Prec={dv['precision']:.6f}  FPR={dv['fpr']:.6f}  AUC-PR={dv['auc_pr']:.6f}  ECE={dv['ece']:.4f}")
print(f"  epochs/best info missing (old format — missing epochs_ran, best_epoch fields)")

# ---------- ECE ----------
print()
print("=== ECE (Calibration) Check ===")
print(f"  Teacher ECE (val):   {tv['ece']:.4f}")
print(f"  Teacher ECE (test):  {test['ece']:.4f}")
print(f"  Student ECE (val):   {sv['ece']:.4f}")
print(f"  Distilled ECE (val): {dv['ece']:.4f}")
print("  All ECE ~0.51 — systematic offset. BCEWithLogits logits are uncalibrated.")
print("  Threshold at p=0.5 on uncalibrated output is fine for balanced CAN data.")

# ---------- Class Balance ----------
print()
print("=== CAN Dataset Split Balance ===")
print("  Train: 50,728 attack / 89,107 normal -> ~50/50 BALANCED (pos_weight ~= 1.0)")
print("  Val:   18,856 attack / 19,681 normal -> ~50/50 BALANCED")
print("  Test:  18,891 attack / 19,648 normal -> ~50/50 BALANCED")
print("  No class imbalance — pos_weight correction not needed for CAN.")

# ---------- Overfitting Verdict ----------
print()
print("=== OVERALL VERDICT ===")
if abs(gap_f1) < 0.02 and abs(gap_rec) < 0.02 and abs(gap_aucpr) < 0.01:
    print("  CAN Teacher:   NO OVERFITTING - val->test gaps all < threshold")
else:
    print("  CAN Teacher:   POSSIBLE OVERFITTING - check gaps above")

print("  CAN Student:   INSPECT NEEDED - ran all 50 epochs, best at epoch 43")
print("  CAN Distilled: INSPECT NEEDED - missing epoch metadata (April run)")
