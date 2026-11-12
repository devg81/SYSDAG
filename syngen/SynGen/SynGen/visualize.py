import torch
from gan_pytorch import Generator  # import your model class

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# load generator
G = Generator().to(DEVICE)
G.load_state_dict(torch.load("generator_NORM.pt", map_location=DEVICE))
G.eval()
import matplotlib.pyplot as plt

def plot_generated(generator, n_samples=3):
    noise = torch.randn(n_samples, 100).to(DEVICE)
    fake = generator(noise).detach().cpu().numpy()

    for i in range(n_samples):
        signal = fake[i]

        plt.figure(figsize=(12,6))
        for lead in range(12):
            plt.plot(signal[:, lead] + lead*3)

        plt.title(f"Generated ECG {i+1}")
        plt.show()
plot_generated(G)