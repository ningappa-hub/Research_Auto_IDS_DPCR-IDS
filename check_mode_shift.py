import torch
import numpy as np
from dpcr_ids.config import load_config
from dpcr_ids.training.pipeline import _load_trained_model, _prepared_dataset
from dpcr_ids.training.metrics import sigmoid

config = load_config('configs/research_pipeline.yaml')
model, kind, path = _load_trained_model(config, 'ethernet', preferred_kind='teacher')
val_dataset = _prepared_dataset(config, 'ethernet', 'val')

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)

# Take 2000 samples
loader = torch.utils.data.DataLoader(val_dataset, batch_size=2000, shuffle=True)
features, labels = next(iter(loader))
features = features.to(device)

# EVAL MODE
model.eval()
with torch.no_grad():
    logits_eval = model(features).cpu().numpy()

# TRAIN MODE
model.train()
with torch.no_grad():
    logits_train = model(features).cpu().numpy()

labels = labels.cpu().numpy()

print(f"--- EVAL MODE ---")
pos_eval = logits_eval[labels == 1]
neg_eval = logits_eval[labels == 0]
if len(pos_eval) > 0: print(f"Pos logits: mean={pos_eval.mean():.4f}, prob={sigmoid(pos_eval.mean()):.4f}")
if len(neg_eval) > 0: print(f"Neg logits: mean={neg_eval.mean():.4f}, prob={sigmoid(neg_eval.mean()):.4f}")

print(f"\n--- TRAIN MODE ---")
pos_train = logits_train[labels == 1]
neg_train = logits_train[labels == 0]
if len(pos_train) > 0: print(f"Pos logits: mean={pos_train.mean():.4f}, prob={sigmoid(pos_train.mean()):.4f}")
if len(neg_train) > 0: print(f"Neg logits: mean={neg_train.mean():.4f}, prob={sigmoid(neg_train.mean()):.4f}")
