# evaluate_all.py
import os

classes = ["NORM", "MI", "STTC", "CD", "HYP"]

for cls in classes:
    os.system(
        f"python evaluate_class.py "
        f"--real_npy real_{cls}.npy "
        f"--fake_npy synthetic_data/{cls}_synthetic.npy "
        f"--class_name {cls} "
        f"--output_dir eval_{cls}"
    )