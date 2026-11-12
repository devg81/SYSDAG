"""
evaluate_gan.py
───────────────
Complete evaluation suite for the PTB-XL GAN.

HOW TO USE:
  1. Make sure ptbxl_gan.py is in the same folder as this file
  2. Edit the CONFIG section below (paths, class name)
  3. Run:  python evaluate_gan.py

WHAT IT PRODUCES:
  Console report with all metrics + 7 plot files:

  eval_real_vs_fake_<CLASS>.png     → Lead II real vs fake side by side
  eval_multilead_<CLASS>.png        → 4 leads (I, II, V1, V6) real vs fake
  eval_distributions_<CLASS>.png    → amplitude histograms all 12 leads
  eval_12leads_<CLASS>.png          → all 12 leads of one generated signal
  eval_beat_overlay_<CLASS>.png     → average beat shape real vs fake
  eval_loss_curve_<CLASS>.png       → D loss and G loss over training epochs
  eval_psd_<CLASS>.png              → power spectral density real vs fake
"""

import os
import ast
import numpy as np
import pandas as pd
import torch
import matplotlib
matplotlib.use("Agg")          # no display needed — saves to file
import matplotlib.pyplot as plt
from scipy.stats import ks_2samp, entropy
from scipy.signal import welch
from sklearn.metrics import mean_squared_error

# ── import from your existing training file ──────────────────────
from gan_pytorch import (
    Generator,
    PTBXLDataset,
    build_label_map,
    generate_synthetic,
    NOISE_DIM,
    N_LEADS,
    N_TIMESTEPS,
)

# ═══════════════════════════════════════════════
# CONFIG — match these to your training file
# ═══════════════════════════════════════════════
PTBXL_CSV      = r"D:/SynGen/dataset/ptbxl_database.csv"
SCP_CSV        = r"D:/SynGen/dataset/scp_statements.csv"
DATA_ROOT      = r"D:/SynGen/dataset"
TARGET_CLASS   = "NORM"          # class whose generator you want to evaluate
N_EVAL_SAMPLES = 200             # how many fake signals to generate for evaluation
DEVICE         = "cuda" if torch.cuda.is_available() else "cpu"


# ═══════════════════════════════════════════════
# STEP 1 — LOAD TRAINED GENERATOR
# ═══════════════════════════════════════════════

def load_generator(target_class, device=DEVICE):
    """
    Loads the saved generator weights from generator_<CLASS>.pt
    and sets the model to eval mode (no gradient tracking).
    """
    path = f"generator_{target_class}.pt"

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No saved generator found at '{path}'\n"
            f"Train the GAN first by running ptbxl_gan.py"
        )

    G = Generator(noise_dim=NOISE_DIM, n_leads=N_LEADS).to(device)
    G.load_state_dict(torch.load(path, map_location=device, weights_only=True))
    G.eval()
    print(f"Generator loaded from: {path}")
    return G


# ═══════════════════════════════════════════════
# STEP 2 — LOAD REAL SIGNALS FOR COMPARISON
# Uses fold 9 (validation fold — never seen during training)
# ═══════════════════════════════════════════════

def load_real_signals(target_class, n_samples=N_EVAL_SAMPLES):
    """
    Loads real ECG signals from validation fold (fold 9).
    Returns numpy array shape (n_samples, 1000, 12).
    Fold 9 is used because it was never seen during GAN training.
    """
    label_map = build_label_map(PTBXL_CSV, SCP_CSV)

    dataset = PTBXLDataset(
        label_map    = label_map,
        data_root    = DATA_ROOT,
        target_class = target_class,
        sampling     = "lr",
        folds        = [9],          # validation fold only
    )

    # take up to n_samples records
    indices = np.random.choice(len(dataset),
                               size=min(n_samples, len(dataset)),
                               replace=False)

    signals = []
    for idx in indices:
        sig = dataset[idx].numpy()   # (1000, 12)
        signals.append(sig)

    real = np.stack(signals, axis=0) # (n_samples, 1000, 12)
    print(f"Real signals loaded: {real.shape}")
    return real


# ═══════════════════════════════════════════════
# METRIC 1 — VARIANCE  (mode collapse check)
# ═══════════════════════════════════════════════

def metric_variance(fake):
    """
    Computes variance ACROSS generated samples at each position.
    Low variance = mode collapse (all signals look the same).
    High variance = good diversity.

    fake: (n_samples, 1000, 12)
    Returns: mean variance across all positions
    """
    # axis=0 → compare across samples, not within one sample
    var_map = np.var(fake, axis=0)    # (1000, 12)
    mean_var = var_map.mean()

    status = (
        "CRITICAL — Mode collapse likely"   if mean_var < 0.01 else
        "WARNING  — Possible partial collapse" if mean_var < 0.05 else
        "GOOD     — Healthy diversity"
    )
    return mean_var, status


# ═══════════════════════════════════════════════
# METRIC 2 — MEAN & STD COMPARISON
# ═══════════════════════════════════════════════

def metric_stats(real, fake):
    """
    Compares basic statistics between real and fake signals.
    If the GAN learned well, mean and std should be similar.

    Expected after normalisation:
      mean ≈ 0.0  (signals are zero-centred)
      std  ≈ 0.3 – 0.6  (typical for clipped z-score signals)
    """
    return {
        "real_mean" : float(np.mean(real)),
        "fake_mean" : float(np.mean(fake)),
        "real_std"  : float(np.std(real)),
        "fake_std"  : float(np.std(fake)),
        "real_min"  : float(np.min(real)),
        "fake_min"  : float(np.min(fake)),
        "real_max"  : float(np.max(real)),
        "fake_max"  : float(np.max(fake)),
    }


# ═══════════════════════════════════════════════
# METRIC 3 — KS TEST  (distribution similarity)
# ═══════════════════════════════════════════════

def metric_ks_test(real, fake):
    """
    Kolmogorov-Smirnov test compares the full amplitude distributions
    of real and fake signals.

    H0 (null hypothesis): real and fake come from the same distribution
    p > 0.05 → cannot reject H0 → distributions are similar ✅
    p < 0.05 → distributions are significantly different ❌

    ks_stat: distance between the two distributions (0 = identical)
    """
    real_flat = real.flatten()
    fake_flat = fake.flatten()

    # subsample if very large (KS test is slow on millions of points)
    max_pts = 50000
    if len(real_flat) > max_pts:
        real_flat = np.random.choice(real_flat, max_pts, replace=False)
        fake_flat = np.random.choice(fake_flat, max_pts, replace=False)

    ks_stat, p_value = ks_2samp(real_flat, fake_flat)

    status = (
        "GOOD — distributions are similar (p > 0.05)"
        if p_value > 0.05 else
        "POOR — distributions differ significantly (p < 0.05)"
    )
    return ks_stat, p_value, status


# ═══════════════════════════════════════════════
# METRIC 4 — KL DIVERGENCE  (information overlap)
# ═══════════════════════════════════════════════

def metric_kl_divergence(real, fake, bins=100):
    """
    KL Divergence measures how much information is lost when using
    the fake distribution to represent the real distribution.

    KL = 0     → identical distributions ✅
    KL < 0.1   → very similar ✅
    KL 0.1-0.5 → moderate difference ⚠️
    KL > 0.5   → significantly different ❌

    Computed per-lead then averaged.
    """
    kl_per_lead = []

    for lead in range(real.shape[2]):     # 12 leads
        r = real[:, :, lead].flatten()
        f = fake[:, :, lead].flatten()

        # build histograms over the same range
        combined_min = min(r.min(), f.min())
        combined_max = max(r.max(), f.max())
        bin_edges = np.linspace(combined_min, combined_max, bins + 1)

        r_hist, _ = np.histogram(r, bins=bin_edges, density=True)
        f_hist, _ = np.histogram(f, bins=bin_edges, density=True)

        # add small epsilon to avoid log(0)
        r_hist = r_hist + 1e-8
        f_hist = f_hist + 1e-8

        kl = entropy(r_hist, f_hist)     # KL(real || fake)
        kl_per_lead.append(kl)

    mean_kl = float(np.mean(kl_per_lead))
    status = (
        "GOOD     — distributions very similar"   if mean_kl < 0.1  else
        "MODERATE — some distribution gap"         if mean_kl < 0.5  else
        "POOR     — large distribution gap"
    )
    return mean_kl, kl_per_lead, status


# ═══════════════════════════════════════════════
# METRIC 5 — MSE  (average signal distance)
# ═══════════════════════════════════════════════

def metric_mse(real, fake):
    """
    Compares the AVERAGE real signal shape to the AVERAGE fake signal shape.

    This checks: does the GAN produce the right overall waveform shape?
    It does NOT check per-sample similarity (we don't expect fake[i] ≈ real[i]).

    Low MSE  → average waveform shape is similar ✅
    High MSE → GAN producing wrong overall shape ❌
    """
    real_mean_signal = real.mean(axis=0)    # (1000, 12) average real signal
    fake_mean_signal = fake.mean(axis=0)    # (1000, 12) average fake signal

    mse = mean_squared_error(
        real_mean_signal.flatten(),
        fake_mean_signal.flatten()
    )
    return float(mse)


# ═══════════════════════════════════════════════
# METRIC 6 — PER-LEAD AMPLITUDE RANGE CHECK
# ═══════════════════════════════════════════════

def metric_lead_ranges(real, fake):
    """
    Checks if each of the 12 leads has a similar amplitude range
    between real and fake signals.

    A GAN that ignores certain leads will show very different ranges
    for those leads compared to real data.
    """
    lead_names = ['I','II','III','AVR','AVL','AVF','V1','V2','V3','V4','V5','V6']
    results = []

    for i, name in enumerate(lead_names):
        r_std = float(np.std(real[:, :, i]))
        f_std = float(np.std(fake[:, :, i]))
        ratio = f_std / r_std if r_std > 0 else float('inf')
        status = "✅" if 0.7 <= ratio <= 1.3 else "⚠️"
        results.append({
            "lead"   : name,
            "real_std": r_std,
            "fake_std": f_std,
            "ratio"  : ratio,
            "status" : status,
        })

    return results


# ═══════════════════════════════════════════════
# PLOTS — 3 visualisations saved to disk
# ═══════════════════════════════════════════════

def plot_real_vs_fake(real, fake, target_class, lead_idx=1):
    """
    Plot 1: Real ECG vs Fake ECG side by side (Lead II)
    This is the visual inspection check.
    """
    fig, axes = plt.subplots(2, 1, figsize=(15, 6), sharex=True)
    time = np.arange(N_TIMESTEPS) / 100.0    # seconds

    # pick one real and one fake at random
    r_idx = np.random.randint(0, len(real))
    f_idx = np.random.randint(0, len(fake))

    axes[0].plot(time, real[r_idx, :, lead_idx], color='black', linewidth=0.8)
    axes[0].set_title(f"Real ECG — {target_class} — Lead II", fontsize=11)
    axes[0].set_ylabel("Amplitude (normalised)")
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim(-1.1, 1.1)

    axes[1].plot(time, fake[f_idx, :, lead_idx], color='black', linewidth=0.8, linestyle='--')
    axes[1].set_title(f"Fake ECG — {target_class} — Lead II", fontsize=11)
    axes[1].set_ylabel("Amplitude (normalised)")
    axes[1].set_xlabel("Time (seconds)")
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim(-1.1, 1.1)

    plt.tight_layout()
    path = f"eval_real_vs_fake_{target_class}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved: {path}")


def plot_amplitude_distributions(real, fake, target_class):
    """
    Plot 2: Amplitude distribution histograms — real vs fake
    Shows how well the GAN learned the overall value distribution.
    """
    fig, axes = plt.subplots(2, 6, figsize=(18, 6))
    lead_names = ['I','II','III','AVR','AVL','AVF','V1','V2','V3','V4','V5','V6']
    axes = axes.flatten()

    for i, (ax, name) in enumerate(zip(axes, lead_names)):
        r = real[:, :, i].flatten()
        f = fake[:, :, i].flatten()

        ax.hist(r, bins=60, alpha=0.6, color='black',  label='Real',  density=True)
        ax.hist(f, bins=60, alpha=0.6, color='gray',   label='Fake',  density=True)
        ax.set_title(f"Lead {name}", fontsize=9)
        ax.set_xlabel("Amplitude", fontsize=8)
        ax.tick_params(labelsize=7)
        if i == 0:
            ax.legend(fontsize=7)

    plt.suptitle(f"Amplitude Distribution — Real vs Fake ({target_class})", fontsize=12)
    plt.tight_layout()
    path = f"eval_distributions_{target_class}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved: {path}")


def plot_all_12_leads(fake, target_class):
    """
    Plot 3: All 12 leads of one generated signal stacked vertically.
    Lets you visually check if all leads look plausible.
    """
    lead_names = ['I','II','III','AVR','AVL','AVF','V1','V2','V3','V4','V5','V6']
    time = np.arange(N_TIMESTEPS) / 100.0

    fig, axes = plt.subplots(12, 1, figsize=(15, 22), sharex=True)
    sample = fake[np.random.randint(0, len(fake))]    # one signal (1000, 12)

    for i, (ax, name) in enumerate(zip(axes, lead_names)):
        ax.plot(time, sample[:, i], color='black', linewidth=0.7)
        ax.set_ylabel(name, fontsize=9, rotation=0, labelpad=24)
        ax.set_ylim(-1.1, 1.1)
        ax.grid(True, alpha=0.2)
        ax.tick_params(labelsize=7)

    axes[-1].set_xlabel("Time (seconds)")
    plt.suptitle(f"Generated ECG — All 12 Leads ({target_class})", fontsize=12)
    plt.tight_layout()
    path = f"eval_12leads_{target_class}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved: {path}")


# ═══════════════════════════════════════════════
# PLOT 4 — MULTI-LEAD REAL vs FAKE
# Shows 4 key leads side by side: I, II, V1, V6
# I and II are limb leads, V1/V6 are precordial
# endpoints — together they cover the full picture
# ═══════════════════════════════════════════════

def plot_multilead_real_vs_fake(real, fake, target_class):
    """
    Plots 4 clinically important leads in two columns:
      Left  column → real signals
      Right column → fake signals

    Leads chosen:
      Lead I   → primary limb lead
      Lead II  → standard clinical monitoring lead
      V1       → precordial start (right side of heart)
      V6       → precordial end   (left side of heart)

    Together these 4 leads reveal whether the GAN learned:
      - limb lead morphology (I, II)
      - precordial progression (V1 → V6)
      - correct amplitude scale per lead
    """
    leads_to_show = [0, 1, 6, 11]              # indices in signal array
    lead_names    = ['I', 'II', 'V1', 'V6']
    time = np.arange(N_TIMESTEPS) / 100.0      # x axis in seconds

    fig, axes = plt.subplots(4, 2, figsize=(18, 14), sharex=True)
    fig.suptitle(f"Real vs Fake — 4 Leads ({target_class})", fontsize=13)

    for row, (lead_idx, lead_name) in enumerate(zip(leads_to_show, lead_names)):
        r_idx = np.random.randint(0, len(real))
        f_idx = np.random.randint(0, len(fake))

        # ── left: real ──────────────────────────
        axes[row, 0].plot(time, real[r_idx, :, lead_idx],
                          color='black', linewidth=0.8)
        axes[row, 0].set_title(f"Real — Lead {lead_name}", fontsize=10)
        axes[row, 0].set_ylim(-1.1, 1.1)
        axes[row, 0].set_ylabel("Amplitude", fontsize=8)
        axes[row, 0].grid(True, alpha=0.3)

        # ── right: fake (dashed) ─────────────────
        axes[row, 1].plot(time, fake[f_idx, :, lead_idx],
                          color='black', linewidth=0.8, linestyle='--')
        axes[row, 1].set_title(f"Fake — Lead {lead_name}", fontsize=10)
        axes[row, 1].set_ylim(-1.1, 1.1)
        axes[row, 1].grid(True, alpha=0.3)

    axes[-1, 0].set_xlabel("Time (seconds)")
    axes[-1, 1].set_xlabel("Time (seconds)")

    plt.tight_layout()
    path = f"eval_multilead_{target_class}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved: {path}")


# ═══════════════════════════════════════════════
# PLOT 5 — BEAT OVERLAY (average beat shape)
# Extracts individual beats, overlays them, and
# compares the AVERAGE real beat vs average fake beat
# ═══════════════════════════════════════════════

def plot_beat_overlay(real, fake, target_class, lead_idx=1, fs=100):
    """
    Segments signals into individual beats using a simple
    peak-detection on Lead II (or whichever lead_idx is given).

    Then plots:
      - 10 individual real beats as faint grey lines
      - 10 individual fake beats as faint grey lines
      - Average real beat as a thick black line
      - Average fake beat as a thick dashed black line

    This reveals whether the GAN learned the correct
    QRS spike shape and P-T wave morphology — even if
    individual beats are noisy, the average should be clean.

    Beat window: 300ms before and after peak = 0.6s per beat
    At 100Hz: 300 samples per beat
    """
    WINDOW  = 150     # samples on each side of peak = 300ms at 100Hz
    N_BEATS = 10      # how many individual beats to overlay

    lead_name = ['I','II','III','AVR','AVL','AVF',
                 'V1','V2','V3','V4','V5','V6'][lead_idx]

    def extract_beats(signals):
        """
        For each signal, find the highest peak in Lead II
        and extract a fixed-width window around it.
        Returns list of (WINDOW*2,) arrays.
        """
        beats = []
        for sig in signals:                        # sig: (1000, 12)
            lead = sig[:, lead_idx]
            # find all local maxima above 0.5 (QRS candidates)
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(lead, height=0.3, distance=40)
            for p in peaks:
                if WINDOW <= p < len(lead) - WINDOW:
                    beat = lead[p - WINDOW : p + WINDOW]  # (300,)
                    beats.append(beat)
            if len(beats) >= N_BEATS * 3:   # stop early once we have enough
                break
        return beats

    real_beats = extract_beats(real)
    fake_beats = extract_beats(fake)

    if len(real_beats) < 3 or len(fake_beats) < 3:
        print(f"Beat overlay skipped — not enough peaks detected in Lead {lead_name}")
        return

    real_arr  = np.array(real_beats)    # (n_beats, 300)
    fake_arr  = np.array(fake_beats)

    real_mean = real_arr.mean(axis=0)
    fake_mean = fake_arr.mean(axis=0)

    t = np.linspace(-WINDOW/fs*1000, WINDOW/fs*1000,
                    WINDOW * 2)              # x axis in milliseconds

    fig, axes = plt.subplots(1, 2, figsize=(16, 5), sharey=True)
    fig.suptitle(f"Beat Overlay — Lead {lead_name} ({target_class})\n"
                 f"Faint lines = individual beats,  Thick line = average beat",
                 fontsize=11)

    # ── left: real beats ────────────────────────
    for beat in real_arr[:N_BEATS]:
        axes[0].plot(t, beat, color='gray', alpha=0.3, linewidth=0.6)
    axes[0].plot(t, real_mean, color='black', linewidth=2.0, label='Average real')
    axes[0].axvline(0, color='black', linestyle=':', alpha=0.4, linewidth=0.8)
    axes[0].set_title("Real Beats", fontsize=10)
    axes[0].set_xlabel("Time relative to peak (ms)")
    axes[0].set_ylabel("Amplitude (normalised)")
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    # ── right: fake beats ────────────────────────
    for beat in fake_arr[:N_BEATS]:
        axes[1].plot(t, beat, color='gray', alpha=0.3, linewidth=0.6)
    axes[1].plot(t, fake_mean, color='black', linewidth=2.0,
                 linestyle='--', label='Average fake')
    axes[1].axvline(0, color='black', linestyle=':', alpha=0.4, linewidth=0.8)
    axes[1].set_title("Fake Beats", fontsize=10)
    axes[1].set_xlabel("Time relative to peak (ms)")
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    path = f"eval_beat_overlay_{target_class}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved: {path}")


# ═══════════════════════════════════════════════
# PLOT 6 — LOSS CURVE OVER EPOCHS
# Reads the loss log file saved during training.
# Shows whether D and G converged correctly.
# ═══════════════════════════════════════════════

def plot_loss_curve(target_class):
    """
    Reads loss_<CLASS>.csv which is saved during training.
    Expected columns: epoch, d_loss, g_loss

    Convergence targets:
      D_loss → 1.386  (= 2 × ln2, discriminator at chance level)
      G_loss → 0.693  (= ln2,     generator fooling D ~50%)

    If D_loss crashes to 0 early  → discriminator won (unstable)
    If G_loss crashes to 0 early  → mode collapse
    If both oscillate and converge → healthy training ✅

    NOTE: This plot requires that you save losses during training.
    Add this to your training loop in ptbxl_gan.py:

        import csv
        with open(f'loss_{target_class}.csv', 'a', newline='') as f:
            csv.writer(f).writerow([epoch, d_avg, g_avg])
    """
    loss_path = f"loss_{target_class}.csv"

    if not os.path.exists(loss_path):
        print(f"Loss curve skipped — '{loss_path}' not found.")
        print(f"  To enable: save epoch losses to '{loss_path}' during training.")
        print(f"  Format: epoch,d_loss,g_loss  (one row per epoch)")
        return

    data   = np.loadtxt(loss_path, delimiter=',')
    epochs = data[:, 0]
    d_loss = data[:, 1]
    g_loss = data[:, 2]

    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(epochs, d_loss, color='black',      linewidth=1.2, label='Discriminator loss')
    ax.plot(epochs, g_loss, color='black',      linewidth=1.2,
            linestyle='--', label='Generator loss')

    # convergence target lines
    ax.axhline(1.386, color='gray', linestyle=':', linewidth=0.9,
               label='D target (1.386 = 2×ln2)')
    ax.axhline(0.693, color='gray', linestyle='-.', linewidth=0.9,
               label='G target (0.693 = ln2)')

    ax.set_title(f"Training Loss Curve — {target_class}", fontsize=12)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = f"eval_loss_curve_{target_class}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved: {path}")


# ═══════════════════════════════════════════════
# PLOT 7 — POWER SPECTRAL DENSITY (PSD)
# Converts signals to frequency domain using Welch method.
# Compares how much power real vs fake signals have
# at each frequency (0–50 Hz).
# ═══════════════════════════════════════════════

def plot_psd(real, fake, target_class, lead_idx=1, fs=100):
    """
    Power Spectral Density shows the frequency content of signals.

    Real ECG should have specific power peaks at:
      ~1 Hz    → heartbeat rate (fundamental frequency)
      ~3–5 Hz  → P and T wave energy
      ~10–20 Hz → QRS complex energy (sharpest feature)
      Above 40 Hz → noise (should be low after filtering)

    If fake PSD matches real PSD:
      → GAN learned temporal structure correctly ✅

    If fake PSD is flat across all frequencies:
      → GAN only learned amplitude range, not structure ❌

    If fake PSD is missing the ~10–20 Hz peak:
      → GAN producing rounded waves instead of sharp QRS ⚠️
      (this is what we see in the current output)

    Uses Welch method: splits signal into overlapping windows,
    computes FFT on each, averages the results → smooth PSD.
    """
    lead_name = ['I','II','III','AVR','AVL','AVF',
                 'V1','V2','V3','V4','V5','V6'][lead_idx]

    # compute PSD for every signal then average
    def mean_psd(signals):
        psds = []
        for sig in signals:
            freqs, psd = welch(sig[:, lead_idx], fs=fs,
                               nperseg=256, noverlap=128)
            psds.append(psd)
        return freqs, np.mean(psds, axis=0)

    freqs_r, psd_real = mean_psd(real)
    freqs_f, psd_fake = mean_psd(fake)

    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    fig.suptitle(f"Power Spectral Density — Lead {lead_name} ({target_class})\n"
                 f"Averaged over {len(real)} real and {len(fake)} fake signals",
                 fontsize=11)

    # ── left: linear scale ───────────────────────
    axes[0].plot(freqs_r, psd_real, color='black',     linewidth=1.2, label='Real')
    axes[0].plot(freqs_f, psd_fake, color='black',     linewidth=1.2,
                 linestyle='--', label='Fake')
    axes[0].axvspan(0.5, 40, alpha=0.06, color='black',
                    label='Clinical ECG band (0.5–40 Hz)')
    axes[0].set_title("Linear scale", fontsize=10)
    axes[0].set_xlabel("Frequency (Hz)")
    axes[0].set_ylabel("Power spectral density")
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, 50)

    # ── right: log scale (shows low-power detail) ─
    axes[1].semilogy(freqs_r, psd_real + 1e-10, color='black',
                     linewidth=1.2, label='Real')
    axes[1].semilogy(freqs_f, psd_fake + 1e-10, color='black',
                     linewidth=1.2, linestyle='--', label='Fake')
    axes[1].axvspan(0.5, 40, alpha=0.06, color='black',
                    label='Clinical ECG band (0.5–40 Hz)')
    axes[1].set_title("Log scale (shows low-power detail)", fontsize=10)
    axes[1].set_xlabel("Frequency (Hz)")
    axes[1].set_ylabel("Power spectral density (log)")
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3, which='both')
    axes[1].set_xlim(0, 50)

    plt.tight_layout()
    path = f"eval_psd_{target_class}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved: {path}")


# ═══════════════════════════════════════════════


def print_report(target_class, var, var_status, stats,
                 ks_stat, p_val, ks_status,
                 kl, kl_leads, kl_status,
                 mse, lead_ranges):

    divider = "=" * 60

    print(f"\n{divider}")
    print(f"  GAN EVALUATION REPORT — Class: {target_class}")
    print(divider)

    # ── Metric 1: Variance ──────────────────────
    print(f"\n[1] VARIANCE (Diversity / Mode Collapse Check)")
    print(f"    Mean variance : {var:.6f}")
    print(f"    Status        : {var_status}")
    print(f"    Interpretation:")
    print(f"      < 0.01  → mode collapse — all signals identical")
    print(f"      < 0.05  → partial collapse — low diversity")
    print(f"      > 0.05  → healthy — good signal diversity")

    # ── Metric 2: Stats ─────────────────────────
    print(f"\n[2] SIGNAL STATISTICS COMPARISON")
    print(f"    {'':10}  {'Real':>10}  {'Fake':>10}")
    print(f"    {'Mean':10}  {stats['real_mean']:>10.4f}  {stats['fake_mean']:>10.4f}")
    print(f"    {'Std':10}  {stats['real_std']:>10.4f}  {stats['fake_std']:>10.4f}")
    print(f"    {'Min':10}  {stats['real_min']:>10.4f}  {stats['fake_min']:>10.4f}")
    print(f"    {'Max':10}  {stats['real_max']:>10.4f}  {stats['fake_max']:>10.4f}")
    print(f"    Interpretation:")
    print(f"      After normalisation, mean ≈ 0.0 and max/min ≈ ±1.0 is expected")
    print(f"      Real and fake std should be within 10–20% of each other")

    # ── Metric 3: KS Test ───────────────────────
    print(f"\n[3] KOLMOGOROV-SMIRNOV TEST (Distribution Similarity)")
    print(f"    KS statistic  : {ks_stat:.6f}  (0 = identical, 1 = completely different)")
    print(f"    p-value       : {p_val:.6f}")
    print(f"    Status        : {ks_status}")
    print(f"    Interpretation:")
    print(f"      p > 0.05 → real and fake come from same distribution ✅")
    print(f"      p < 0.05 → distributions are significantly different ❌")

    # ── Metric 4: KL Divergence ─────────────────
    print(f"\n[4] KL DIVERGENCE (Information Overlap, averaged over 12 leads)")
    print(f"    Mean KL       : {kl:.6f}")
    print(f"    Status        : {kl_status}")
    print(f"    Per-lead breakdown:")
    lead_names = ['I','II','III','AVR','AVL','AVF','V1','V2','V3','V4','V5','V6']
    for name, kl_val in zip(lead_names, kl_leads):
        bar = "█" * int(kl_val * 20)
        print(f"      Lead {name:<4}: {kl_val:.4f}  {bar}")
    print(f"    Interpretation:")
    print(f"      KL < 0.1  → very similar distributions ✅")
    print(f"      KL < 0.5  → moderate gap ⚠️")
    print(f"      KL > 0.5  → large gap — GAN needs more training ❌")

    # ── Metric 5: MSE ───────────────────────────
    print(f"\n[5] MSE — AVERAGE WAVEFORM SHAPE SIMILARITY")
    print(f"    MSE           : {mse:.8f}")
    print(f"    Interpretation:")
    print(f"      Compares average real waveform to average fake waveform")
    print(f"      Lower is better — no fixed threshold, compare across epochs")

    # ── Metric 6: Per-lead ranges ───────────────
    print(f"\n[6] PER-LEAD AMPLITUDE RANGE CHECK")
    print(f"    {'Lead':<6}  {'Real Std':>10}  {'Fake Std':>10}  {'Ratio':>8}  Status")
    print(f"    {'-'*52}")
    for row in lead_ranges:
        print(f"    {row['lead']:<6}  {row['real_std']:>10.4f}  "
              f"{row['fake_std']:>10.4f}  {row['ratio']:>8.3f}  {row['status']}")
    print(f"    Ratio = fake_std / real_std")
    print(f"    0.7 – 1.3 is acceptable range ✅")

    print(f"\n{divider}")
    print(f"  END OF REPORT")
    print(divider)


# ═══════════════════════════════════════════════
# MAIN — runs everything in sequence
# ═══════════════════════════════════════════════

def run_evaluation(target_class=TARGET_CLASS):

    print(f"\nStarting evaluation for class: {target_class}")
    print(f"Device: {DEVICE}\n")

    # ── 1. load models and data ────────────────
    G    = load_generator(target_class)
    real = load_real_signals(target_class, N_EVAL_SAMPLES)

    # ── 2. generate fake signals ───────────────
    print(f"\nGenerating {N_EVAL_SAMPLES} fake signals...")
    fake = generate_synthetic(G, N_EVAL_SAMPLES)
    print(f"Fake signals shape: {fake.shape}")

    # ── 3. compute all metrics ─────────────────
    print("\nComputing metrics...")

    var,  var_status              = metric_variance(fake)
    stats                         = metric_stats(real, fake)
    ks_stat, p_val, ks_status     = metric_ks_test(real, fake)
    kl, kl_leads, kl_status       = metric_kl_divergence(real, fake)
    mse                           = metric_mse(real, fake)
    lead_ranges                   = metric_lead_ranges(real, fake)

    # ── 4. print report ────────────────────────
    print_report(
        target_class, var, var_status, stats,
        ks_stat, p_val, ks_status,
        kl, kl_leads, kl_status,
        mse, lead_ranges
    )

    # ── 5. save plots ──────────────────────────
    print("\nGenerating plots...")

    # Plot 1 — Lead II real vs fake (original)
    plot_real_vs_fake(real, fake, target_class)

    # Plot 2 — Amplitude distributions all 12 leads (original)
    plot_amplitude_distributions(real, fake, target_class)

    # Plot 3 — All 12 leads of one generated signal (original)
    plot_all_12_leads(fake, target_class)

    # Plot 4 — Multi-lead real vs fake (I, II, V1, V6) — NEW
    plot_multilead_real_vs_fake(real, fake, target_class)

    # Plot 5 — Beat overlay average shape — NEW
    plot_beat_overlay(real, fake, target_class)

    # Plot 6 — Loss curve over epochs — NEW
    # (skipped automatically if loss_<CLASS>.csv not found)
    plot_loss_curve(target_class)

    # Plot 7 — Power spectral density — NEW
    plot_psd(real, fake, target_class)

    print(f"\nEvaluation complete for class: {target_class}")
    print(f"Up to 7 plot files saved in current directory.")


# ─────────────────────────────────────────────
# To evaluate all 5 classes:
#   for cls in ['NORM', 'MI', 'STTC', 'CD', 'HYP']:
#       run_evaluation(cls)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    run_evaluation(TARGET_CLASS)