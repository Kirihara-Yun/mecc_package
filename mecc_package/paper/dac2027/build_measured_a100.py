"""Build reproducible A100 figures from committed run JSON, without ideal targets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent.parent / "results" / "runs"
OUT = HERE / "measured_figures"
OUT.mkdir(exist_ok=True)

BLUE = "#2166A5"
MID = "#72A8C9"
GRAY = "#8C969E"
ORANGE = "#BF7440"
TEAL = "#488B82"
DARK = "#233646"
POLICIES = ["naive", "swapmoe", "independent", "ours_io", "ours", "flashmoe_rf_adaptation", "fiddler"]
NAMES = {"naive": "Streaming", "swapmoe": "Fixed CPU", "independent": "Independent",
         "ours_io": "MECC I/O", "ours": "MECC", "flashmoe_rf_adaptation": "RF adapter",
         "fiddler": "CPU compute"}
COLORS = {"naive": GRAY, "swapmoe": ORANGE, "independent": ORANGE,
          "ours_io": MID, "ours": BLUE, "flashmoe_rf_adaptation": TEAL,
          "fiddler": "#A4ADB5"}

plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                     "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
                     "xtick.labelsize": 8, "ytick.labelsize": 8,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.facecolor": "white", "figure.facecolor": "white",
                     "pdf.fonttype": 42, "svg.fonttype": "none"})


def read(run_id: str, policy: str) -> dict:
    path = RUNS / run_id / "result.json"
    status = RUNS / run_id / "status.json"
    raw = path.read_bytes()
    d = json.loads(raw)
    state = json.loads(status.read_text(encoding="utf-8"))
    assert state["phase"] == "complete" and d["mode"] == "real", run_id
    assert d["platform"] == "a100-80g" and d["config"]["cold_ssd"], run_id
    assert policy in d["results"], run_id
    return {"run_id": run_id, "sha256": hashlib.sha256(raw).hexdigest(),
            "config": d["config"], "plan": d["compiled_plan"],
            "metrics": d["results"][policy]}


def load() -> dict:
    main = {}
    for p in ["naive", "swapmoe", "ours_io", "ours", "flashmoe_rf_adaptation", "fiddler"]:
        run = ("a100-main-ours_io-20261105-retry1" if p == "ours_io"
               else f"a100-main-{p}-20261104")
        main[p] = read(run, p)
    independent = read("a100-e06-independent-20261105", "independent")
    budget = {c: {p: read(f"a100-p2-cpu{c}-{p}-20261104", p)
                  for p in ["naive", "swapmoe", "ours", "flashmoe_rf_adaptation", "fiddler"]}
              for c in (30, 60)}
    for group in (main, {"independent": independent}):
        for r in group.values():
            assert r["config"] == main["ours"]["config"]
            assert r["plan"]["k_h"] == 4 and r["plan"]["k_c"] == 3
    for c, group in budget.items():
        for r in group.values():
            assert r["config"] == budget[30]["ours"]["config"]
            assert r["plan"]["k_h"] == 4 and r["plan"]["k_c"] == (2 if c == 30 else 4)
    return {"main": main, "independent": independent, "budget": budget}


def style(ax):
    ax.grid(axis="y", color="#DCE3E8", linewidth=.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5, color="#7B858C")


def save(fig, stem: str):
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight", pad_inches=.08)
    fig.savefig(OUT / f"{stem}.png", dpi=240, bbox_inches="tight", pad_inches=.08)
    plt.close(fig)


def main_figure(data: dict):
    main = data["main"]
    order = ["naive", "swapmoe", "ours_io", "ours", "flashmoe_rf_adaptation", "fiddler"]
    fig, ax = plt.subplots(1, 2, figsize=(10.7, 3.05), gridspec_kw={"width_ratios": [1.45, 1]})
    fig.subplots_adjust(left=.07, right=.99, bottom=.26, top=.82, wspace=.32)
    x = np.arange(len(order))
    vals = [main[p]["metrics"]["tpot_ms"] / 1000 for p in order]
    bars = ax[0].bar(x, vals, color=[COLORS[p] for p in order], width=.64)
    ax[0].bar_label(bars, fmt="%.1f", padding=2, fontsize=8)
    ax[0].set_xticks(x, [NAMES[p].replace(" ", "\n") for p in order])
    ax[0].set_ylim(0, 25)
    ax[0].set_ylabel("TPOT (s/token)")
    ax[0].set_title("(a) Single-A100 decode latency")
    style(ax[0])
    vals = [main[p]["metrics"]["hit_pct"]["ssd"] for p in order]
    bars = ax[1].bar(x, vals, color=[COLORS[p] for p in order], width=.64)
    ax[1].bar_label(bars, fmt="%.1f", padding=2, fontsize=8)
    ax[1].set_xticks(x, [NAMES[p].replace(" ", "\n") for p in order])
    ax[1].set_ylim(0, 38)
    ax[1].set_ylabel("Cold-tier demand share (%)")
    ax[1].set_title("(b) All-phase demand share")
    style(ax[1])
    save(fig, "main")


def retention_figure(data: dict):
    main = data["main"]
    indep = data["independent"]
    groups = [("Independent", indep), ("Fixed CPU", main["swapmoe"]),
              ("MECC", main["ours"])]
    fig, ax = plt.subplots(1, 2, figsize=(10.7, 2.95))
    fig.subplots_adjust(left=.08, right=.98, bottom=.23, top=.82, wspace=.30)
    for a, field, div, ylabel, limit, title in [
        (ax[0], "tpot_ms", 1000, "TPOT (s/token)", 38, "(a) Decode latency"),
        (ax[1], "ssd", 1, "Cold-tier demand share (%)", 54, "(b) All-phase demand share")]:
        vals = [(r["metrics"]["hit_pct"][field] if field == "ssd"
                 else r["metrics"][field] / div) for _, r in groups]
        bars = a.bar(range(3), vals, color=[ORANGE, GRAY, BLUE], width=.56)
        a.bar_label(bars, fmt="%.1f", padding=3, fontsize=9)
        a.set_xticks(range(3), [name for name, _ in groups])
        a.set_ylim(0, limit)
        a.set_ylabel(ylabel)
        a.set_title(title)
        style(a)
    save(fig, "retention")


def budget_figure(data: dict):
    budget = data["budget"]
    order = ["naive", "swapmoe", "ours", "flashmoe_rf_adaptation", "fiddler"]
    fig, ax = plt.subplots(1, 2, figsize=(10.7, 3.0))
    fig.subplots_adjust(left=.08, right=.98, bottom=.27, top=.80, wspace=.34)
    x = np.arange(len(order))
    for a, field, ylabel, limit, title in [
        (ax[0], "tpot_ms", "TPOT (s/token)", 29, "(a) Decode latency"),
        (ax[1], "ssd", "Cold-tier demand share (%)", 50, "(b) All-phase demand share")]:
        for c, shift, col in [(30, -.18, MID), (60, .18, BLUE)]:
            vals = [(budget[c][p]["metrics"]["hit_pct"][field] if field == "ssd"
                     else budget[c][p]["metrics"][field] / 1000) for p in order]
            a.bar(x + shift, vals, width=.34, color=col, label=f"CPU {c} GB")
        a.set_xticks(x, [NAMES[p].replace(" ", "\n") for p in order])
        a.set_ylim(0, limit)
        a.set_ylabel(ylabel)
        a.set_title(title)
        style(a)
    ax[0].legend(frameon=False, ncol=2, loc="upper right")
    save(fig, "budget")


def main():
    data = load()
    main_figure(data)
    retention_figure(data)
    budget_figure(data)
    audit = {"scope": "one completed A100 run per plotted point; no ideal targets",
             "medium": "RAID logical block device reports ROTA=1; physical disks not inventoried",
             "main": {p: {k: r[k] for k in ("run_id", "sha256", "config")} for p, r in data["main"].items()},
             "independent": {k: data["independent"][k] for k in ("run_id", "sha256", "config")},
             "budget": {str(c): {p: {k: r[k] for k in ("run_id", "sha256", "config")}
                                for p, r in group.items()} for c, group in data["budget"].items()}}
    (OUT / "DATA_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print("Measured A100 figures and source hashes written to", OUT)


if __name__ == "__main__":
    main()
