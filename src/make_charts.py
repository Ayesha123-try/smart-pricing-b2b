"""Static PNG charts for the README, drawn from the tables in outputs/report_data/."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from corridor import ROOT

DATA = ROOT / "outputs" / "report_data"
CHARTS = ROOT / "outputs" / "charts"
ACCENT, MUTED, INK, SOFT = "#2F6DB5", "#B8BFC8", "#20262E", "#667080"

plt.rcParams.update({"font.size": 10, "text.color": INK, "axes.edgecolor": MUTED, "axes.labelcolor": SOFT,
                     "xtick.color": SOFT, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False})


def gap_definitions():
    d = pd.read_csv(DATA / "definitions.csv")
    fig, ax = plt.subplots(figsize=(9, 4.6))
    colors = [ACCENT if "headline" in x or "stretch" in x else MUTED for x in d["definition"]]
    ax.barh(d["definition"], d["gap_pct"], color=colors, height=0.62)
    for y, v in enumerate(d["gap_pct"]):
        ax.text(v + 0.08, y, f"{v:.2f}%", va="center", color=INK, zorder=3,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
    ax.set_xlabel("% of revenue")
    ax.set_xlim(0, 10.5)
    ax.set_title("3.9% below target, up to 7.9% below stretch", loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(CHARTS / "gap_definitions.png", dpi=170)


def calibration():
    d = pd.read_csv(DATA / "calibration.csv")
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.barh(d["band"][::-1], d["actual_pct"][::-1], color=ACCENT, height=0.6)
    ax.axvline(25, color=INK, lw=1, ls="--")
    ax.text(25, 3.5, "25% if well calibrated", color=SOFT, ha="center", va="bottom")
    for y, v in enumerate(d["actual_pct"][::-1]):
        ax.text(1, y, f"{v:.1f}%", va="center", color="white", fontweight="bold")
    ax.set_xlim(0, 34)
    ax.set_xlabel("% of Q4 2017 won deals")
    ax.set_title("The corridor is well calibrated on unseen deals", loc="left", fontweight="bold", pad=16)
    fig.tight_layout()
    fig.savefig(CHARTS / "corridor_calibration.png", dpi=170)


def model_vs_base_rate():
    d = pd.read_csv(DATA / "models.csv")[::-1].reset_index(drop=True)
    headline = pd.read_csv(DATA / "headline.csv").set_index("metric")["value"]
    base_brier = headline["base_brier"]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for y, r in d.iterrows():
        color = ACCENT if r["chosen"] else MUTED
        ax.plot([r["brier_gain_low"], r["brier_gain_high"]], [y, y], color=color, lw=2, solid_capstyle="round")
        ax.plot(base_brier - r["brier"], y, "o", color=color, ms=7)
    ax.axvline(0, color=INK, lw=1, ls="--")
    ax.set_yticks(range(len(d)), d["model"])
    ax.set_xlabel("Brier score improvement over the base rate, 95% interval (right of zero is better)")
    ax.set_title("No model's interval sits clearly above the base rate", loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(CHARTS / "model_vs_base_rate.png", dpi=170)


def main():
    CHARTS.mkdir(exist_ok=True)
    gap_definitions()
    calibration()
    model_vs_base_rate()


if __name__ == "__main__":
    main()
