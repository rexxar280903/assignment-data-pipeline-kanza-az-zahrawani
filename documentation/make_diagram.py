"""Generate documentation/data-flow-diagram.png (run: python documentation/make_diagram.py)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "data-flow-diagram.png"

STEPS = [
    ("Raw Dataset", "data/raw/\nautomobileEDA_dirty_training.csv\n205 rows x 30 cols", "#e8eef7", "#3b5b92", ""),
    ("Load Data", "load_data()\npd.read_csv (read-only)", "#dff0e6", "#2e7d4f", "EXTRACT"),
    ("Data Inspection", "inspect_data()\nhead, shape, dtypes, missing,\nduplicates, unique values", "#fff3dc", "#b7791f", "TRANSFORM"),
    ("Data Cleaning", "clean_data()\ntrim/lowercase, drop 4 dups,\nparse dates, impute, drop no-price", "#fff3dc", "#b7791f", "TRANSFORM"),
    ("Data Transformation", "transform_data()\nMin-Max scaling, one-hot,\nordinal & frequency encoding", "#fff3dc", "#b7791f", "TRANSFORM"),
    ("Processed Dataset", "save_data() -> data/processed/\nautomobileEDA_processed.csv\n198 rows x 61 cols", "#f3e5f5", "#7b3f99", "LOAD"),
]

fig, ax = plt.subplots(figsize=(19, 5.2), dpi=150)
ax.set_xlim(0, 19)
ax.set_ylim(0, 5.2)
ax.axis("off")

w, h, gap, y = 2.65, 2.1, 0.5, 1.3
x = 0.35
centers = []
for title, body, fill, edge, stage in STEPS:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.18",
                                fc=fill, ec=edge, lw=2))
    ax.text(x + w / 2, y + h - 0.38, title, ha="center", va="center",
            fontsize=12.5, fontweight="bold", color=edge)
    ax.text(x + w / 2, y + 0.82, body, ha="center", va="center", fontsize=8.6, color="#222")
    if stage:
        ax.text(x + w / 2, y - 0.35, stage, ha="center", va="center", fontsize=9,
                fontweight="bold", color=edge)
    centers.append(x)
    x += w + gap

for i in range(len(centers) - 1):
    ax.add_patch(FancyArrowPatch((centers[i] + w + 0.04, y + h / 2),
                                 (centers[i + 1] - 0.04, y + h / 2),
                                 arrowstyle="-|>", mutation_scale=20, lw=2, color="#555"))

ax.text(9.5, 4.65, "Data Flow Diagram - Automobile Data Pipeline (src/pipeline.py)",
        ha="center", fontsize=15, fontweight="bold", color="#222")
ax.text(9.5, 0.35, "ETL: Extract (load raw CSV)  ->  Transform (inspect, clean, transform)  ->  Load (save processed CSV)",
        ha="center", fontsize=10, color="#444", style="italic")

fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(f"Saved {OUT}")
