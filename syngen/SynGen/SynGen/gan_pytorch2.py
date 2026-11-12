"""
gan_pytorch.py

Generator (and matching Discriminator) architecture for the 12-lead ECG GAN.

NOTE: your uploaded gan_pytorch.py was empty, so this Generator class was
reconstructed directly from the tensor shapes stored inside generator_NORM.pt
(dense.0 ... dense.7, upsample.0 ... upsample.6). Loading generator_NORM.pt
into this class with strict=True works with zero missing/unexpected keys,
and produces the expected (batch, 1000, 12) output — so this is confirmed to
be the correct architecture.

Pipeline:
  z (batch, 100)
    -> dense: Linear/BatchNorm/LeakyReLU stack -> (batch, 512*125)
    -> reshape -> (batch, 512, 125)
    -> upsample: 3x ConvTranspose1d(stride=2) + BatchNorm + LeakyReLU, Tanh at the end
    -> (batch, 12, 1000)
    -> permute -> (batch, 1000, 12)
"""

import torch
import torch.nn as nn


LATENT_DIM = 100
SEQ_LEN = 1000
N_LEADS = 12


class Generator(nn.Module):
    def __init__(self, latent_dim: int = LATENT_DIM, seq_len: int = SEQ_LEN, n_leads: int = N_LEADS):
        super().__init__()
        assert seq_len == 1000, "This architecture's upsample path is fixed for seq_len=1000 (125 -> 250 -> 500 -> 1000)."

        self.latent_dim = latent_dim
        self.seq_len = seq_len
        self.n_leads = n_leads

        self.dense = nn.Sequential(
            nn.Linear(latent_dim, 256),        # dense.0
            nn.BatchNorm1d(256),                # dense.1
            nn.LeakyReLU(0.2, inplace=True),    # dense.2
            nn.Linear(256, 512),                # dense.3
            nn.BatchNorm1d(512),                # dense.4
            nn.LeakyReLU(0.2, inplace=True),    # dense.5
            nn.Linear(512, 512 * 125),          # dense.6
            nn.BatchNorm1d(512 * 125),          # dense.7
            nn.LeakyReLU(0.2, inplace=True),    # dense.8
        )

        self.upsample = nn.Sequential(
            nn.ConvTranspose1d(512, 256, kernel_size=4, stride=2, padding=1),  # upsample.0  125 -> 250
            nn.BatchNorm1d(256),                                                # upsample.1
            nn.LeakyReLU(0.2, inplace=True),                                    # upsample.2
            nn.ConvTranspose1d(256, 128, kernel_size=4, stride=2, padding=1),  # upsample.3  250 -> 500
            nn.BatchNorm1d(128),                                                # upsample.4
            nn.LeakyReLU(0.2, inplace=True),                                    # upsample.5
            nn.ConvTranspose1d(128, n_leads, kernel_size=4, stride=2, padding=1),  # upsample.6  500 -> 1000
            nn.Tanh(),                                                            # upsample.7
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        x = self.dense(z)                          # (batch, 512*125)
        x = x.view(x.size(0), 512, 125)             # (batch, 512, 125)
        x = self.upsample(x)                        # (batch, n_leads, seq_len)
        x = x.permute(0, 2, 1)                       # (batch, seq_len, n_leads)
        return x


class Discriminator(nn.Module):
    """
    Standard matching discriminator for this GAN (not recoverable from the
    generator checkpoint since it isn't saved, but included so the file is a
    complete, self-contained module if you want to keep training later).
    """

    def __init__(self, seq_len: int = SEQ_LEN, n_leads: int = N_LEADS):
        super().__init__()
        self.model = nn.Sequential(
            nn.Conv1d(n_leads, 64, kernel_size=4, stride=2, padding=1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv1d(64, 128, kernel_size=4, stride=2, padding=1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv1d(128, 256, kernel_size=4, stride=2, padding=1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Flatten(),
            nn.Dropout(0.4),
            nn.LazyLinear(1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, n_leads) -> (batch, n_leads, seq_len)
        x = x.permute(0, 2, 1)
        return self.model(x)


if __name__ == "__main__":
    # quick self-test
    device = "cuda" if torch.cuda.is_available() else "cpu"
    G = Generator().to(device)
    z = torch.randn(4, LATENT_DIM, device=device)
    out = G(z)
    print("Generator output shape:", out.shape)  # (4, 1000, 12)
