"""
train_all_classes.py

Trains one GAN per diagnostic superclass (NORM, MI, STTC, CD, HYP)
sequentially, then generates the synthetic samples needed to balance
each class against the dominant one.

Just update the three paths at the top and run:
    python train_all_classes.py

Checkpoints:   checkpoints/generator_<CLASS>.pt
Synthetic:     synthetic_data/<CLASS>_synthetic.npy
"""

import os
import numpy as np
from gan_pytorch import (
    build_label_map,
    train_gan,
    generate_synthetic,
    check_mode_collapse,
    compute_generation_targets,
)

# ─────────────────────────────────────────────
# EDIT THESE PATHS
# ─────────────────────────────────────────────
PTBXL_CSV  = r"D:/SynGen/dataset/ptbxl_database.csv"
SCP_CSV    = r"D:/SynGen/dataset/scp_statements.csv"
DATA_ROOT  = r"D:/SynGen/dataset"

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
ALL_CLASSES      = ["NORM", "MI", "STTC", "CD", "HYP"]
CHECKPOINT_DIR   = "./checkpoints"
SYNTHETIC_DIR    = "./synthetic_data"
N_EPOCHS         = 200
BATCH_SIZE       = 32
LR               = 0.0002
THRESHOLD        = 50.0

os.makedirs(CHECKPOINT_DIR, exist_ok=True)
os.makedirs(SYNTHETIC_DIR,  exist_ok=True)


def main():
    # ── Step 1: build label map once ──────────────────────────────────
    print("Loading label map...")
    label_map = build_label_map(PTBXL_CSV, SCP_CSV, threshold=THRESHOLD)
    print(f"Total records: {len(label_map)}\n")

    # ── Step 2: compute how many synthetic samples needed per class ───
    targets = compute_generation_targets(label_map)

    # ── Step 3: train one GAN per class ───────────────────────────────
    trained_generators = {}

    for cls in ALL_CLASSES:
        ckpt_path = os.path.join(CHECKPOINT_DIR, f"generator_{cls}.pt")

        # skip training if checkpoint already exists
        if os.path.exists(ckpt_path):
            print(f"\n[{cls}] Checkpoint found at {ckpt_path} — skipping training.")
            from gan_pytorch import Generator, NOISE_DIM, N_LEADS
            import torch
            DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
            G = Generator(noise_dim=NOISE_DIM, n_leads=N_LEADS).to(DEVICE)
            G.load_state_dict(torch.load(ckpt_path, map_location=DEVICE))
            trained_generators[cls] = G
            continue

        print(f"\n{'='*55}")
        print(f"  Training GAN for class: {cls}")
        print(f"{'='*55}")

        G = train_gan(
            target_class = cls,
            label_map    = label_map,
            data_root    = DATA_ROOT,
            n_epochs     = N_EPOCHS,
            batch_size   = BATCH_SIZE,
            lr           = LR,
        )

        # move checkpoint into organised folder
        src = f"generator_{cls}.pt"
        if os.path.exists(src):
            os.rename(src, ckpt_path)
            print(f"Checkpoint moved → {ckpt_path}")

        trained_generators[cls] = G

    # ── Step 4: mode collapse check + generate synthetic data ─────────
    print(f"\n{'='*55}")
    print("  Generation + Quality Check")
    print(f"{'='*55}")

    for cls in ALL_CLASSES:
        G = trained_generators.get(cls)
        if G is None:
            print(f"\n[{cls}] No trained generator found — skipping.")
            continue

        print(f"\n── {cls} ──────────────────────────────────")

        # mode collapse check
        variance = check_mode_collapse(G)

        # generate synthetic samples
        n_needed = 500

        print(f"[{cls}] Generating {n_needed} synthetic samples...")
        synthetic = generate_synthetic(G, n_needed)

        save_path = os.path.join(SYNTHETIC_DIR, f"{cls}_synthetic.npy")
        np.save(save_path, synthetic)
        print(f"[{cls}] Saved → {save_path}  shape: {synthetic.shape}")

    # ── Step 5: combine all into one dataset ──────────────────────────
    print(f"\n{'='*55}")
    print("  Building combined dataset")
    print(f"{'='*55}")

    all_signals = []
    all_labels  = []

    for cls in ALL_CLASSES:
        path = os.path.join(SYNTHETIC_DIR, f"{cls}_synthetic.npy")
        if not os.path.exists(path):
            print(f"[{cls}] File not found — skipping from combined.")
            continue
        data = np.load(path)
        all_signals.append(data)
        all_labels.extend([cls] * len(data))
        print(f"  {cls}: {len(data)} samples loaded")

    all_signals = np.concatenate(all_signals, axis=0)
    all_labels  = np.array(all_labels)

    np.save(os.path.join(SYNTHETIC_DIR, "all_classes_combined.npy"), all_signals)
    np.save(os.path.join(SYNTHETIC_DIR, "all_classes_labels.npy"),   all_labels)

    print(f"\nCombined dataset saved:")
    print(f"  Signals → {SYNTHETIC_DIR}/all_classes_combined.npy  shape: {all_signals.shape}")
    print(f"  Labels  → {SYNTHETIC_DIR}/all_classes_labels.npy    shape: {all_labels.shape}")
    print(f"\nAll done.")


if __name__ == "__main__":
    main()