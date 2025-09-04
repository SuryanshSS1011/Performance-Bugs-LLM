"""Generate Figs. 1, 2, 3 from the paper into results/visualizations/."""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "results" / "visualizations"
OUT.mkdir(parents=True, exist_ok=True)

CATS = [
    "Algorithmic\nInefficiency",
    "Memory\nUsage",
    "Redundant\nComputation",
    "CPU\nOverhead",
    "I/O\nInefficiency",
]
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]


def fig1_category_distribution():
    counts = [165, 116, 54, 99, 56]
    pcts = [33.7, 23.7, 11.0, 20.2, 11.4]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(CATS, counts, color=COLORS)
    for bar, c, p in zip(bars, counts, pcts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{c}\n({p}%)",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    ax.set_ylabel("Number of Bugs")
    ax.set_ylim(0, max(counts) * 1.18)
    ax.set_title(
        "Fig. 1. Distribution of 490 performance bugs across five categories"
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(OUT / "fig1_category_distribution.png", dpi=150)
    plt.close()


def fig2_per_project_breakdown():
    projects = [
        "Csv", "Compress", "Gson", "Codec", "JacksonDatabind", "JacksonCore",
        "Lang", "Chart", "JxPath", "Closure", "Mockito", "Math",
        "Cli", "Jsoup", "Time", "Collections", "JacksonXml",
    ]
    totals = [35, 32, 32, 29, 31, 31, 31, 30, 30, 29, 29, 29, 29, 28, 25, 24, 16]
    algo = [28.6, 31.2, 31.2, 32.3, 32.3, 32.3, 33.3, 33.3, 34.5, 34.5,
            34.5, 34.5, 34.5, 35.7, 40.0, 41.7, 31.2]
    mem  = [22.9, 25.0, 25.0, 25.4, 25.4, 22.6, 23.3, 26.7, 29.0, 20.7,
            24.1, 27.6, 13.8, 31.0, 28.6, 16.7, 31.2]
    red  = [11.4, 9.4, 18.8, 12.9, 12.9, 16.1, 12.9, 13.3, 10.3, 6.9,
            10.3, 10.3, 24.1, 6.9, 12.0, 8.3, 6.2]
    cpu  = [22.9, 21.9, 18.8, 16.1, 16.1, 19.4, 16.1, 16.7, 13.8, 20.7,
            20.7, 13.8, 13.8, 14.3, 12.0, 29.2, 12.5]
    io   = [14.3, 12.5, 6.2, 12.9, 12.9, 9.7, 14.3, 10.0, 12.4, 17.2,
            10.3, 13.8, 13.8, 12.0, 7.4, 4.1, 18.8]

    x = np.arange(len(projects))
    fig, ax = plt.subplots(figsize=(13, 6))
    bottom = np.zeros(len(projects))
    layers = [
        ("Algorithmic Inefficiency", algo, COLORS[0]),
        ("Memory Usage", mem, COLORS[1]),
        ("Redundant Computation", red, COLORS[2]),
        ("CPU Overhead", cpu, COLORS[3]),
        ("I/O Inefficiency", io, COLORS[4]),
    ]
    for label, vals, color in layers:
        vals = np.array(vals)
        ax.bar(x, vals, bottom=bottom, color=color, label=label, edgecolor="white", linewidth=0.4)
        for i, v in enumerate(vals):
            if v >= 8:
                ax.text(x[i], bottom[i] + v / 2, f"{v:.1f}", ha="center", va="center", fontsize=7, color="white")
        bottom += vals
    for i, t in enumerate(totals):
        ax.text(x[i], 102, str(t), ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(projects, rotation=30, ha="right")
    ax.set_ylabel("Percentage of Bugs")
    ax.set_ylim(0, 110)
    ax.set_title("Fig. 2. Breakdown of performance bug types across 17 Defects4J projects")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=5, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(OUT / "fig2_per_project_breakdown.png", dpi=150, bbox_inches="tight")
    plt.close()


def fig3_per_category_metrics():
    cats = ["Algorithmic\nInefficiency", "Memory\nUsage", "Redundant\nComputation", "CPU\nOverhead", "I/O\nInefficiency"]
    counts = [33, 23, 11, 20, 11]
    precision = [85.0, 87.0, 75.0, 86.0, 82.0]
    recall =    [91.0, 83.0, 82.0, 80.0, 73.0]
    f1 =        [87.9, 85.0, 78.4, 82.9, 77.3]

    x = np.arange(len(cats))
    width = 0.26
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(x - width, precision, width, label="Precision", color="#1f77b4")
    ax.bar(x,         recall,    width, label="Recall",    color="#ff7f0e")
    ax.bar(x + width, f1,        width, label="F1 Score",  color="#2ca02c")
    for i, c in enumerate(counts):
        ax.text(x[i], 102, f"count: {c}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.set_ylabel("Percentage (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Fig. 3. Per-category model performance: Precision, Recall, F1")
    ax.legend(loc="upper right", frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(OUT / "fig3_per_category_metrics.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    fig1_category_distribution()
    fig2_per_project_breakdown()
    fig3_per_category_metrics()
    print(f"Wrote 3 figures to {OUT}")
