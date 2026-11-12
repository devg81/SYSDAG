"""
evaluate_class.py

Evaluates synthetic ECG quality for ONE diagnostic class at a time, using
the exact same evaluation matrix used for the NORM class in the March
report: Variance (mode collapse), Mean/Std difference, KS statistic,
KL divergence, MSE (waveform shape), per-lead Real-vs-Fake std, an
overall real-vs-fake stats table, a beat-overlay plot (Lead II), and
per-lead amplitude distribution histograms.

Run it once per class (NORM, MI, STTC, CD, HYP) — each run only needs
that class's real signals and that class's trained generator.

INPUTS
------
--real_npy   Path to a (N, 1000, 12) float array of REAL, already
             normalised ([-1, 1]) ECGs for this class (e.g. saved from
             your PTB-XL preprocessing pipeline for that superclass).
--checkpoint Path to that class's generator_<CLASS>.pt (uses gan_pytorch.py
             Generator to produce fake signals) — OR --fake_npy to skip
             generation and evaluate a pre-generated array directly.
--class_name Class label, used only in plot titles / output filenames.
--n_fake     How many fake samples to generate for evaluation (default 200,
             matches the mode-collapse check used in the report).
--output_dir Where plots + a metrics.json get written (default ./eval_<CLASS>).

USAGE
-----
    # Straight from a trained checkpoint
    python evaluate_class.py \
        --real_npy real_NORM.npy \
        --checkpoint checkpoints/generator_NORM.pt \
        --class_name NORM \
        --output_dir eval_NORM

    # Or against an already-generated array
    python evaluate_class.py \
        --real_npy real_MI.npy \
        --fake_npy generated_ecg/MI/MI_all.npy \
        --class_name MI \
        --output_dir eval_MI

OUTPUT
------
eval_<CLASS>/
    generated_ecg_sample.png          <- one example fake ECG, 12 leads stacked
    beat_overlay_lead_II.png          <- real vs fake beat overlay, Lead II
    amplitude_distribution.png        <- 12-panel real vs fake histograms
    metrics.json                      <- every number below, machine-readable
    metrics_summary.txt               <- same numbers, plain text for the report
"""

import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import ks_2samp
from scipy.signal import find_peaks

LEAD_NAMES = ["I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6"]
FS = 100  # Hz, matches PTB-XL records100


# ----------------------------------------------------------------------
# Generation (optional — skip with --fake_npy if you already have samples)
# ----------------------------------------------------------------------

def generate_fake(checkpoint_path: str, n_samples: int) -> np.ndarray:
    import torch
    from gan_pytorch import Generator, LATENT_DIM

    device = "cuda" if torch.cuda.is_available() else "cpu"
    G = Generator().to(device)
    G.load_state_dict(torch.load(checkpoint_path, map_location=device), strict=True)
    G.eval()

    chunks = []
    remaining = n_samples
    batch = 64
    with torch.no_grad():
        while remaining > 0:
            b = min(batch, remaining)
            z = torch.randn(b, LATENT_DIM, device=device)
            chunks.append(G(z).cpu().numpy())
            remaining -= b
    return np.concatenate(chunks, axis=0)


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------

def kl_divergence_1d(real_vals, fake_vals, bins=50, eps=1e-8):
    """Histogram-based KL(real || fake) over the shared [-1, 1] range."""
    hist_range = (-1.0, 1.0)
    p, edges = np.histogram(real_vals, bins=bins, range=hist_range, density=True)
    q, _ = np.histogram(fake_vals, bins=bins, range=hist_range, density=True)
    p = p + eps
    q = q + eps
    p = p / p.sum()
    q = q / q.sum()
    return float(np.sum(p * np.log(p / q)))


def compute_metrics(real: np.ndarray, fake: np.ndarray) -> dict:
    """
    real, fake: (N, 1000, 12) arrays, values normalised to roughly [-1, 1].
    Mirrors the evaluation matrix used for NORM in the March report.
    """
    metrics = {}

    # --- Mode-collapse / diversity: variance across generated samples ---
    metrics["variance"] = float(np.var(fake))

    # --- Overall mean / std difference (real vs fake, flattened) ---
    real_flat = real.reshape(-1)
    fake_flat = fake.reshape(-1)
    metrics["mean_difference"] = float(abs(real_flat.mean() - fake_flat.mean()))
    metrics["std_difference"] = float(abs(real_flat.std() - fake_flat.std()))

    # --- KS statistic, averaged across leads ---
    ks_per_lead = []
    for lead in range(real.shape[2]):
        stat, _ = ks_2samp(real[:, :, lead].reshape(-1), fake[:, :, lead].reshape(-1))
        ks_per_lead.append(stat)
    metrics["ks_statistic_mean"] = float(np.mean(ks_per_lead))
    metrics["ks_statistic_per_lead"] = {LEAD_NAMES[i]: float(ks_per_lead[i]) for i in range(len(ks_per_lead))}

    # --- KL divergence, averaged across leads ---
    kl_per_lead = []
    for lead in range(real.shape[2]):
        kl_per_lead.append(kl_divergence_1d(real[:, :, lead].reshape(-1), fake[:, :, lead].reshape(-1)))
    metrics["kl_divergence_mean"] = float(np.mean(kl_per_lead))
    metrics["kl_divergence_per_lead"] = {LEAD_NAMES[i]: float(kl_per_lead[i]) for i in range(len(kl_per_lead))}

    # --- MSE between average real waveform and average fake waveform ---
    real_avg = real.mean(axis=0)  # (1000, 12)
    fake_avg = fake.mean(axis=0)  # (1000, 12)
    metrics["mse_waveform_shape"] = float(np.mean((real_avg - fake_avg) ** 2))

    # --- Overall stats table (Mean / Std / Min / Max), real vs fake ---
    metrics["stats_table"] = {
        "real": {
            "mean": float(real_flat.mean()),
            "std": float(real_flat.std()),
            "min": float(real_flat.min()),
            "max": float(real_flat.max()),
        },
        "fake": {
            "mean": float(fake_flat.mean()),
            "std": float(fake_flat.std()),
            "min": float(fake_flat.min()),
            "max": float(fake_flat.max()),
        },
    }

    # --- Per-lead Real Std vs Fake Std ---
    per_lead_std = {}
    for i, name in enumerate(LEAD_NAMES):
        per_lead_std[name] = {
            "real_std": float(real[:, :, i].std()),
            "fake_std": float(fake[:, :, i].std()),
        }
    metrics["per_lead_std"] = per_lead_std

    return metrics


# ----------------------------------------------------------------------
# Plots
# ----------------------------------------------------------------------

def plot_generated_sample(fake: np.ndarray, class_name: str, out_path: str):
    signal = fake[0]  # (1000, 12)
    plt.figure(figsize=(12, 6))
    for lead in range(signal.shape[1]):
        plt.plot(signal[:, lead] + lead * 3)
    plt.title(f"Generated ECG 1 — {class_name}")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def extract_beats(signal_1d: np.ndarray, fs=FS, window_ms=1500):
    """Find R-peaks on a 1D lead and cut fixed windows around each."""
    window = int(window_ms / 1000 * fs)  # samples each side
    peaks, _ = find_peaks(signal_1d, height=0.3, distance=int(0.4 * fs))
    beats = []
    for p in peaks:
        if p - window >= 0 and p + window < len(signal_1d):
            beats.append(signal_1d[p - window: p + window])
    return np.array(beats), window


def plot_beat_overlay(real: np.ndarray, fake: np.ndarray, class_name: str, out_path: str, lead_idx=1):
    """Lead II (index 1) beat overlay: real vs fake."""
    lead_name = LEAD_NAMES[lead_idx]

    real_beats_all, window = [], None
    for s in real[:, :, lead_idx]:
        beats, window = extract_beats(s)
        if len(beats):
            real_beats_all.append(beats)
    fake_beats_all = []
    for s in fake[:, :, lead_idx]:
        beats, window = extract_beats(s)
        if len(beats):
            fake_beats_all.append(beats)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    time_ms = np.linspace(-1500, 1500, 2 * window) if window else np.array([])

    if real_beats_all:
        real_beats = np.concatenate(real_beats_all, axis=0)
        for b in real_beats:
            axes[0].plot(time_ms, b, color="gray", alpha=0.15, linewidth=0.7)
        axes[0].plot(time_ms, real_beats.mean(axis=0), color="black", linewidth=2, label="Average real")
    axes[0].set_title("Real Beats")
    axes[0].set_xlabel("Time relative to peak (ms)")
    axes[0].set_ylabel("Amplitude (normalised)")
    axes[0].legend()

    if fake_beats_all:
        fake_beats = np.concatenate(fake_beats_all, axis=0)
        for b in fake_beats:
            axes[1].plot(time_ms, b, color="gray", alpha=0.15, linewidth=0.7)
        axes[1].plot(time_ms, fake_beats.mean(axis=0), color="black", linestyle="--", linewidth=2, label="Average fake")
    axes[1].set_title("Fake Beats")
    axes[1].set_xlabel("Time relative to peak (ms)")
    axes[1].legend()

    fig.suptitle(f"Beat Overlay — Lead {lead_name} ({class_name})\nFaint lines = individual beats, Thick line = average beat")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()

    if not real_beats_all or not fake_beats_all:
        print("  [warning] Could not detect enough R-peaks for a full beat overlay "
              "(low-amplitude or very noisy signal) — plot may be sparse.")


def plot_amplitude_distributions(real: np.ndarray, fake: np.ndarray, class_name: str, out_path: str):
    fig, axes = plt.subplots(2, 6, figsize=(20, 7))
    axes = axes.flatten()
    for i, name in enumerate(LEAD_NAMES):
        ax = axes[i]
        ax.hist(real[:, :, i].reshape(-1), bins=60, range=(-1, 1), alpha=0.6, label="Real", color="dimgray", density=True)
        ax.hist(fake[:, :, i].reshape(-1), bins=60, range=(-1, 1), alpha=0.6, label="Fake", color="lightgray", density=True)
        ax.set_title(f"Lead {name}")
        ax.set_xlabel("Amplitude")
        if i == 0:
            ax.legend()
    fig.suptitle(f"Amplitude Distribution — Real vs Fake ({class_name})")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--real_npy", required=True, help="Path to (N, 1000, 12) real signals for this class")
    parser.add_argument("--checkpoint", default=None, help="Path to generator_<CLASS>.pt (generates fake samples)")
    parser.add_argument("--fake_npy", default=None, help="Path to pre-generated (N, 1000, 12) fake signals (alternative to --checkpoint)")
    parser.add_argument("--class_name", required=True, help="e.g. NORM, MI, STTC, CD, HYP")
    parser.add_argument("--n_fake", type=int, default=200, help="Number of fake samples to generate if using --checkpoint (default 200)")
    parser.add_argument("--output_dir", default=None, help="Default: ./eval_<CLASS_NAME>")
    args = parser.parse_args()

    if args.checkpoint is None and args.fake_npy is None:
        parser.error("Provide either --checkpoint (to generate fake samples) or --fake_npy (pre-generated).")

    output_dir = args.output_dir or f"./eval_{args.class_name}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading real signals from {args.real_npy} ...")
    real = np.load(args.real_npy)
    print(f"  real shape: {real.shape}")

    if args.fake_npy:
        print(f"Loading fake signals from {args.fake_npy} ...")
        fake = np.load(args.fake_npy)
    else:
        print(f"Generating {args.n_fake} fake samples from {args.checkpoint} ...")
        fake = generate_fake(args.checkpoint, args.n_fake)
    print(f"  fake shape: {fake.shape}")

    print("Computing metrics ...")
    metrics = compute_metrics(real, fake)

    print("Plotting ...")
    plot_generated_sample(fake, args.class_name, os.path.join(output_dir, "generated_ecg_sample.png"))
    plot_beat_overlay(real, fake, args.class_name, os.path.join(output_dir, "beat_overlay_lead_II.png"))
    plot_amplitude_distributions(real, fake, args.class_name, os.path.join(output_dir, "amplitude_distribution.png"))

    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    summary_path = os.path.join(output_dir, "metrics_summary.txt")
    with open(summary_path, "w") as f:
        f.write(f"Evaluation Matrix — {args.class_name}\n")
        f.write("=" * 40 + "\n")
        f.write(f"Variance (diversity/mode collapse): {metrics['variance']:.4f}\n")
        f.write(f"Mean Difference:                    {metrics['mean_difference']:.4f}\n")
        f.write(f"Std Difference:                     {metrics['std_difference']:.4f}\n")
        f.write(f"KS Statistic (mean):                {metrics['ks_statistic_mean']:.4f}\n")
        f.write(f"KL Divergence (mean):                {metrics['kl_divergence_mean']:.4f}\n")
        f.write(f"MSE (waveform shape):               {metrics['mse_waveform_shape']:.4f}\n\n")
        f.write("Real vs Fake — overall stats\n")
        st = metrics["stats_table"]
        f.write(f"  Mean:    real={st['real']['mean']:.4f}  fake={st['fake']['mean']:.4f}\n")
        f.write(f"  Std Dev: real={st['real']['std']:.4f}  fake={st['fake']['std']:.4f}\n")
        f.write(f"  Min:     real={st['real']['min']:.4f}  fake={st['fake']['min']:.4f}\n")
        f.write(f"  Max:     real={st['real']['max']:.4f}  fake={st['fake']['max']:.4f}\n\n")
        f.write("Per-lead Std (Real vs Fake)\n")
        for name, vals in metrics["per_lead_std"].items():
            f.write(f"  {name:<5} real={vals['real_std']:.4f}  fake={vals['fake_std']:.4f}\n")

    print(f"\nDone. Results saved to {output_dir}/")
    print(f"  - generated_ecg_sample.png")
    print(f"  - beat_overlay_lead_II.png")
    print(f"  - amplitude_distribution.png")
    print(f"  - metrics.json")
    print(f"  - metrics_summary.txt")


if __name__ == "__main__":
    main()
