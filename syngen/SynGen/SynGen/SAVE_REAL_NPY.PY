from gan_pytorch import build_label_map, PTBXLDataset
import numpy as np
from torch.utils.data import DataLoader

PTBXL_CSV = r"D:/SynGen/dataset/ptbxl_database.csv"
SCP_CSV   = r"D:/SynGen/dataset/scp_statements.csv"
DATA_ROOT = r"D:/SynGen/dataset"

label_map = build_label_map(PTBXL_CSV, SCP_CSV)

for cls in ["NORM", "MI", "STTC", "CD", "HYP"]:
    dataset = PTBXLDataset(label_map, DATA_ROOT, cls, folds=list(range(1, 9)))
    loader  = DataLoader(dataset, batch_size=64, shuffle=False)
    
    all_signals = []
    for batch in loader:
        all_signals.append(batch.numpy())
    
    arr = np.concatenate(all_signals, axis=0)
    np.save(f"real_{cls}.npy", arr)
    print(f"{cls}: saved {arr.shape}")