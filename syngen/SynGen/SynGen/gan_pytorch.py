import os
import ast
import numpy as np
import pandas as pd
import wfdb
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# ─────────────────────────────────────────────
# CONFIG — edit these paths before running
# ─────────────────────────────────────────────
PTBXL_CSV = r"D:/SynGen/dataset/ptbxl_database.csv"
SCP_CSV   = r"D:/SynGen/dataset/scp_statements.csv"
DATA_ROOT = r"D:/SynGen/dataset"         # folder that contains records100/
SAMPLING       = "lr"          # lr = 100Hz, hr = 500Hz
BATCH_SIZE     = 32
NOISE_DIM      = 100
N_LEADS        = 12
N_TIMESTEPS    = 1000
N_EPOCHS       = 200
LR             = 0.0002
DEVICE         = "cuda" if torch.cuda.is_available() else "cpu"
THRESHOLD      = 50.0          # min confidence to count a label
TARGET_CLASS   = "NORM"        # which superclass to train this GAN on
                               # run once per class: NORM MI STTC CD HYP


# ═══════════════════════════════════════════════
# STEP 1 — LABEL BUILDER
# Maps every ecg_id to its diagnostic superclass(es)
# ═══════════════════════════════════════════════

def build_label_map(ptbxl_csv, scp_csv, threshold=50.0):
    """
    Returns a dict:
      { ecg_id -> { 'superclasses': [...], 'filename_lr': '...', 'filename_hr': '...' } }

    scp_codes column looks like: "{'NORM': 100.0, 'SR': 0.0}"
    We parse it, join with scp_statements to get diagnostic_class,
    then keep only codes with confidence >= threshold.
    """
    df   = pd.read_csv(ptbxl_csv, index_col="ecg_id")
    scp  = pd.read_csv(scp_csv, index_col=0)

    # keep only diagnostic codes that have a superclass
    diag = scp[(scp["diagnostic"] == 1) & scp["diagnostic_class"].notna()]
    sub_to_super = diag["diagnostic_class"].to_dict()   # e.g. "NORM"->"NORM", "IMI"->"MI"

    # parse scp_codes from string to dict
    df["scp_codes"] = df["scp_codes"].apply(ast.literal_eval)

    label_map = {}
    for ecg_id, row in df.iterrows():
        superclasses = set()
        for code, conf in row["scp_codes"].items():
            if conf >= threshold and code in sub_to_super:
                superclasses.add(sub_to_super[code])

        label_map[int(ecg_id)] = {
            "superclasses" : list(superclasses),
            "filename_lr"  : row["filename_lr"],
            "filename_hr"  : row["filename_hr"],
            "strat_fold"   : int(row["strat_fold"]),
        }

    return label_map


# ═══════════════════════════════════════════════
# STEP 2 — DATASET
# Loads the binary .dat file via wfdb and returns
# a normalised (1000, 12) float32 tensor
# ═══════════════════════════════════════════════

class PTBXLDataset(Dataset):
    """
    Filters label_map to records whose superclasses contain target_class.
    Optionally restricts to specific strat_folds (e.g. 1-8 for training).

    File loading path:
      DATA_ROOT / filename_lr  (no extension — wfdb adds .dat/.hea itself)

    Signal shape after loading:  (1000, 12)  float64
    After normalisation:         (1000, 12)  float32  in range [-1, 1]
    """

    def __init__(self, label_map, data_root, target_class,
                 sampling="lr", folds=None):
        self.data_root    = data_root
        self.sampling     = sampling   # "lr" or "hr"

        # filter to target class and requested folds
        self.records = []
        for ecg_id, meta in label_map.items():
            if target_class not in meta["superclasses"]:
                continue
            if folds is not None and meta["strat_fold"] not in folds:
                continue
            fname = meta["filename_lr"] if sampling == "lr" else meta["filename_hr"]
            self.records.append({
                "ecg_id"   : ecg_id,
                "filepath" : os.path.join(data_root, fname),
            })

        print(f"[Dataset] class={target_class} | folds={folds} | records={len(self.records)}")

    def __len__(self):
        return len(self.records)

    def _load_signal(self, filepath):
        """
        wfdb.rdrecord expects the path WITHOUT extension.
        .dat and .hea must sit in the same folder.
        Returns numpy array (1000, 12) float64.
        """
        rec = wfdb.rdrecord(filepath)
        sig = rec.p_signal                    # (1000, 12) float64 in mV
        # handle any NaN from bad leads
        sig = np.nan_to_num(sig, nan=0.0)
        return sig

    def _normalise(self, sig):
        """
        Per-lead z-score then clip to [-1, 1].
        Each lead normalised independently so amplitude scale
        differences between leads are preserved in relative terms.
        """
        mean = sig.mean(axis=0, keepdims=True)      # (1, 12)
        std  = sig.std(axis=0, keepdims=True)        # (1, 12)
        std  = np.where(std == 0, 1.0, std)          # avoid divide-by-zero
        sig  = (sig - mean) / std
        sig  = np.clip(sig, -1.0, 1.0)
        return sig.astype(np.float32)

    def __getitem__(self, idx):
        record   = self.records[idx]
        sig      = self._load_signal(record["filepath"])
        sig      = self._normalise(sig)
        tensor   = torch.from_numpy(sig)             # (1000, 12)
        return tensor


# ═══════════════════════════════════════════════
# STEP 3 — GENERATOR
#
# Input:  noise (batch, 100)
# Output: fake ECG signal (batch, 1000, 12)
#
# Architecture:
#   Dense block:  100 → 256 → 512 → 64000
#   Reshape:      64000 → (512, 125)
#   Upsample ×3:  (512,125) → (256,250) → (128,500) → (12,1000)
#   Permute:      (batch,12,1000) → (batch,1000,12)
# ═══════════════════════════════════════════════

class Generator(nn.Module):
    def __init__(self, noise_dim=100, n_leads=12):
        super().__init__()

        # dense block — stretches noise into rich feature map
        self.dense = nn.Sequential(
            nn.Linear(noise_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),

            nn.Linear(256, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),

            nn.Linear(512, 512 * 125),   # 64000
            nn.BatchNorm1d(512 * 125),
            nn.ReLU(),
        )

        # upsample block — expands time axis from 125 → 1000
        self.upsample = nn.Sequential(

            # (batch, 512, 125) → (batch, 256, 250)
            nn.ConvTranspose1d(512, 256,
                               kernel_size=4, stride=2, padding=1),
            nn.BatchNorm1d(256),
            nn.ReLU(),

            # (batch, 256, 250) → (batch, 128, 500)
            nn.ConvTranspose1d(256, 128,
                               kernel_size=4, stride=2, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),

            # (batch, 128, 500) → (batch, 12, 1000)
            nn.ConvTranspose1d(128, n_leads,
                               kernel_size=4, stride=2, padding=1),
            nn.Tanh(),          # output in [-1, 1] matches normalised signal
        )

    def forward(self, noise):
        # noise: (batch, 100)
        x = self.dense(noise)               # (batch, 64000)
        x = x.view(-1, 512, 125)            # (batch, 512, 125)
        x = self.upsample(x)                # (batch, 12, 1000)
        x = x.permute(0, 2, 1)             # (batch, 1000, 12)
        return x


# ═══════════════════════════════════════════════
# STEP 4 — DISCRIMINATOR
#
# Input:  signal (batch, 1000, 12) — real or fake
# Output: score  (batch, 1)        — 1=real, 0=fake
#
# Architecture:
#   Permute:       (batch,1000,12) → (batch,12,1000)
#   Conv ×4:       compress time 1000→500→250→125→62
#                  expand channels 12→64→128→256→512
#   Flatten:       (batch,512,62) → (batch,31744)
#   Linear+Sigmoid: 31744 → 1
# ═══════════════════════════════════════════════

class Discriminator(nn.Module):
    def __init__(self, n_leads=12):
        super().__init__()

        self.conv_blocks = nn.Sequential(

            # block 1 — detect local patterns: QRS spikes, P waves
            # (batch, 12, 1000) → (batch, 64, 500)
            nn.Conv1d(n_leads, 64,
                      kernel_size=4, stride=2, padding=1),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),

            # block 2 — detect beat rhythm, ST segment flatness
            # (batch, 64, 500) → (batch, 128, 250)
            nn.Conv1d(64, 128,
                      kernel_size=4, stride=2, padding=1),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),

            # block 3 — detect multi-beat consistency, amplitude ratios
            # (batch, 128, 250) → (batch, 256, 125)
            nn.Conv1d(128, 256,
                      kernel_size=4, stride=2, padding=1),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),

            # block 4 — detect overall signal plausibility
            # (batch, 256, 125) → (batch, 512, 62)
            nn.Conv1d(256, 512,
                      kernel_size=4, stride=2, padding=1),
            nn.BatchNorm1d(512),
            nn.LeakyReLU(0.2),
        )

        # classifier head
        self.classifier = nn.Sequential(
            nn.Flatten(),                   # (batch, 512*62) = (batch, 31744)
            nn.Linear(512 * 62, 1),         # (batch, 1)
            nn.Sigmoid(),                   # squash to [0, 1]
        )

    def forward(self, signal):
        # signal: (batch, 1000, 12)
        x = signal.permute(0, 2, 1)        # (batch, 12, 1000)
        x = self.conv_blocks(x)             # (batch, 512, 62)
        score = self.classifier(x)          # (batch, 1)
        return score


# ═══════════════════════════════════════════════
# STEP 5 — TRAINING LOOP
# ═══════════════════════════════════════════════

def train_gan(target_class, label_map, data_root,
              n_epochs=N_EPOCHS, batch_size=BATCH_SIZE,
              noise_dim=NOISE_DIM, lr=LR, device=DEVICE):

    # ── dataset & loader ──────────────────────
    dataset = PTBXLDataset(
        label_map  = label_map,
        data_root  = data_root,
        target_class = target_class,
        sampling   = "lr",
        folds      = list(range(1, 9)),     # folds 1-8 = training only
    )
    loader = DataLoader(dataset, batch_size=batch_size,
                        shuffle=True, drop_last=True, num_workers=2)

    # ── models ────────────────────────────────
    G = Generator(noise_dim=noise_dim, n_leads=N_LEADS).to(device)
    D = Discriminator(n_leads=N_LEADS).to(device)

    # ── optimisers ────────────────────────────
    g_opt = torch.optim.Adam(G.parameters(), lr=lr, betas=(0.5, 0.999))
    d_opt = torch.optim.Adam(D.parameters(), lr=lr, betas=(0.5, 0.999))

    # betas=(0.5, 0.999) is standard for GANs — more responsive
    # than default (0.9, 0.999) — prevents D from overpowering G

    criterion = nn.BCELoss()

    print(f"\n{'='*50}")
    print(f"Training GAN for class: {target_class}")
    print(f"Device: {device} | Epochs: {n_epochs} | Batch: {batch_size}")
    print(f"{'='*50}\n")

    for epoch in range(1, n_epochs + 1):

        
        d_loss_epoch = 0.0
        g_loss_epoch = 0.0

        for real_signals in loader:
            # real_signals: (batch, 1000, 12)
            real_signals = real_signals.to(device)
            bs = real_signals.size(0)

            real_labels = torch.ones(bs, 1).to(device)
            fake_labels = torch.zeros(bs, 1).to(device)

            # ── Train Discriminator ───────────────
            # D sees real signals → should output 1
            # D sees fake signals → should output 0

            noise        = torch.randn(bs, noise_dim).to(device)
            fake_signals = G(noise)                        # (bs, 1000, 12)

            real_pred = D(real_signals)                    # (bs, 1)
            fake_pred = D(fake_signals.detach())           # detach: D trains independently
            # .detach() stops gradient flowing back into G during D step

            d_real_loss = criterion(real_pred, real_labels)
            d_fake_loss = criterion(fake_pred, fake_labels)
            d_loss      = d_real_loss + d_fake_loss

            d_opt.zero_grad()
            d_loss.backward()
            d_opt.step()

            # ── Train Generator ───────────────────
            # G wants D to say "real" (1) for its fake signals
            # So G loss = how far D's score on fakes is from 1

            noise        = torch.randn(bs, noise_dim).to(device)
            fake_signals = G(noise)
            fake_pred    = D(fake_signals)                 # no detach: gradient flows to G

            g_loss = criterion(fake_pred, real_labels)    # G wants D to say 1

            g_opt.zero_grad()
            g_loss.backward()
            g_opt.step()

            d_loss_epoch += d_loss.item()
            g_loss_epoch += g_loss.item()

        # ── epoch log ─────────────────────────────
        n_batches = len(loader)
        d_avg = d_loss_epoch / n_batches
        g_avg = g_loss_epoch / n_batches

        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch [{epoch:>4}/{n_epochs}] "
                  f"D_loss: {d_avg:.4f}  G_loss: {g_avg:.4f}")

            # convergence check:
            # D_loss near 1.386 (= 2 * ln2) → balanced, neither winning
            # G_loss near 0.693 (= ln2)      → generator fooling D ~50%

    # ── save generator ────────────────────────────
    save_path = f"generator_{target_class}.pt"
    torch.save(G.state_dict(), save_path)
    print(f"\nGenerator saved → {save_path}")
    return G


# ═══════════════════════════════════════════════
# STEP 6 — GENERATION
# Use trained generator to produce synthetic signals
# ═══════════════════════════════════════════════

def generate_synthetic(generator, n_samples, noise_dim=NOISE_DIM, device=DEVICE):
    """
    Returns numpy array of shape (n_samples, 1000, 12)
    Values are in normalised range [-1, 1]
    """
    generator.eval()
    all_signals = []

    batch_size = 64
    generated  = 0

    with torch.no_grad():
        while generated < n_samples:
            bs    = min(batch_size, n_samples - generated)
            noise = torch.randn(bs, noise_dim).to(device)
            fake  = generator(noise)                   # (bs, 1000, 12)
            all_signals.append(fake.cpu().numpy())
            generated += bs

    return np.concatenate(all_signals, axis=0)        # (n_samples, 1000, 12)


# ═══════════════════════════════════════════════
# STEP 7 — VARIANCE CHECK (mode collapse detector)
# ═══════════════════════════════════════════════

def check_mode_collapse(generator, n_samples=200,
                        noise_dim=NOISE_DIM, device=DEVICE):
    """
    Generates n_samples signals and checks variance across them.
    Low variance = mode collapse (all signals look the same).
    """
    fake_signals = generate_synthetic(generator, n_samples,
                                      noise_dim, device)
    variance = np.var(fake_signals, axis=0).mean()
    print(f"\nMode collapse check — mean variance across {n_samples} samples: {variance:.6f}")
    if variance < 0.01:
        print("WARNING: Very low variance — likely mode collapse!")
    elif variance < 0.05:
        print("WARNING: Low variance — possible partial mode collapse.")
    else:
        print("Variance looks healthy — good diversity in outputs.")
    return variance


# ═══════════════════════════════════════════════
# STEP 8 — CLASS BALANCE CALCULATOR
# How many synthetic samples to generate per class
# ═══════════════════════════════════════════════

def compute_generation_targets(label_map, folds=range(1, 9)):
    """
    Counts real records per superclass in training folds,
    then computes how many synthetic records to generate
    to reach the count of the dominant class.
    """
    from collections import Counter
    counts = Counter()

    for ecg_id, meta in label_map.items():
        if meta["strat_fold"] not in folds:
            continue
        for sc in meta["superclasses"]:
            counts[sc] += 1

    dominant = max(counts.values())
    print("\nReal record counts per superclass (training folds):")
    targets = {}
    for cls, cnt in sorted(counts.items()):
        needed = max(0, dominant - cnt)
        targets[cls] = needed
        print(f"  {cls:<8} real={cnt:<6} generate={needed}")

    return targets


# ═══════════════════════════════════════════════
# MAIN — runs when you execute this file directly
# ═══════════════════════════════════════════════

if __name__ == "__main__":

    print("Loading label map...")
    label_map = build_label_map(PTBXL_CSV, SCP_CSV, threshold=THRESHOLD)
    print(f"Total records in label map: {len(label_map)}")

    # show generation targets
    targets = compute_generation_targets(label_map)

    # train one GAN for TARGET_CLASS (set at top of file)
    # to train all classes, loop:
    #   for cls in ['NORM','MI','STTC','CD','HYP']:
    #       train_gan(cls, label_map, DATA_ROOT)

    G = train_gan(
        target_class = TARGET_CLASS,
        label_map    = label_map,
        data_root    = DATA_ROOT,
    )

    # check quality
    check_mode_collapse(G)

    # generate the needed synthetic signals
    n_needed = targets.get(TARGET_CLASS, 0)
    if n_needed > 0:
        print(f"\nGenerating {n_needed} synthetic signals for class {TARGET_CLASS}...")
        synthetic = generate_synthetic(G, n_needed)
        np.save(f"synthetic_{TARGET_CLASS}.npy", synthetic)
        print(f"Saved → synthetic_{TARGET_CLASS}.npy  shape: {synthetic.shape}")
    else:
        print(f"\nClass {TARGET_CLASS} is already dominant — no generation needed.")