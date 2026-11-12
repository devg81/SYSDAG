"""
visualize.py

Quick sanity-check plots for the ECGs produced by generate_ecg_all_classes.py.

Usage:
    python visualize.py --output_dir ./generated_ecg --n_per_class 2
"""

import os
import argparse
import numpy as np
import matplotlib.pyplot as plt


def plot_ecg(signal, title, fs=100):
    """signal: (1000, 12) array."""
    time = np.arange(signal.shape[0]) / fs
    plt.figure(figsize=(12, 6))
    for lead in range(signal.shape[1]):
        plt.plot(time, signal[:, lead] + lead * 3)
    plt.title(title)
    plt.xlabel("Time (s)")
    plt.yticks([])
    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", default="./generated_ecg",
                         help="Folder produced by generate_ecg_all_classes.py")
    parser.add_argument("--n_per_class", type=int, default=2,
                         help="How many example ECGs to plot per class")
    args = parser.parse_args()

    combined = np.load(os.path.join(args.output_dir, "all_classes_combined.npy"))
    labels = np.load(os.path.join(args.output_dir, "all_classes_labels.npy"))

    classes = sorted(set(labels.tolist()))
    print(f"Classes found: {classes}")
    print(f"Total samples: {combined.shape[0]}, shape per sample: {combined.shape[1:]}")

    for cls in classes:
        idx = np.where(labels == cls)[0][: args.n_per_class]
        for i in idx:
            plot_ecg(combined[i], title=f"Generated ECG — class {cls} (sample {i})")


if __name__ == "__main__":
    main()
