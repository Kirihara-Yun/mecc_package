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

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                     "font.size": 11, "axes.titlesize": 11, "axes.labelsize": 10,
                     "xtick.labelsize": 10, "ytick.labelsize": 10,
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
    ax.grid(axis="x", color="#E4E9ED", linewidth=.65)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, pad=7)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#B4BEC6")


def rows(ax, n):
    for y in range(n):
        if y % 2 == 0:
            ax.axhspan(y - .46, y + .46, color="#F5F8FA", zorder=0)
    ax.set_ylim(-.55, n - .45)


def save(fig, stem: str):
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight", pad_inches=.08)
    fig.savefig(OUT / f"{stem}.png", dpi=240, bbox_inches="tight", pad_inches=.08)
    plt.close(fig)


def main_figure(data: dict):
    main = data["main"]
    order = ["swapmoe", "naive", "fiddler", "ours_io", "ours", "flashmoe_rf_adaptation"]
    fig, ax = plt.subplots(1, 2, figsize=(10.7, 3.65), gridspec_kw={"width_ratios": [1.13, 1]})
    fig.subplots_adjust(left=.18, right=.985, bottom=.16, top=.86, wspace=.22)
    labels = [NAMES[p] for p in order]
    n = len(order)
    for a, metric, limit, ticks, title, xlabel in [
        (ax[0], "tpot_ms", 25, [0, 5, 10, 15, 20], "A  Decode latency", "TPOT (s/token)  ·  lower is better"),
        (ax[1], "ssd", 39, [0, 10, 20, 30], "B  Cold-tier access", "Demand share (%)  ·  lower is better")]:
        rows(a, n)
        for y, p in enumerate(order):
            value = (main[p]["metrics"]["hit_pct"]["ssd"] if metric == "ssd"
                     else main[p]["metrics"]["tpot_ms"] / 1000)
            color = BLUE if p == "ours" else TEAL if p == "flashmoe_rf_adaptation" else GRAY
            a.plot([0, value], [y, y], color=color, lw=1.65, alpha=.65, zorder=2)
            a.scatter([value], [y], s=73 if p == "ours" else 55, color=color,
                      edgecolor="white", linewidth=.8, zorder=3)
            a.annotate(f"{value:.1f}", (value, y), xytext=(7, 0), textcoords="offset points",
                       va="center", fontsize=10, color=DARK, weight="bold" if p == "ours" else "normal")
        a.set_xlim(0, limit)
        a.set_xticks(ticks)
        a.set_yticks(range(n), labels if a is ax[0] else [""] * n)
        a.invert_yaxis()
        a.set_title(title, loc="left", fontweight="bold", color=DARK)
        a.set_xlabel(xlabel)
        style(a)
    save(fig, "main")


def retention_figure(data: dict):
    main = data["main"]
    indep = data["independent"]
    groups = [("Independent", indep), ("Fixed CPU", main["swapmoe"]),
              ("MECC", main["ours"])]
    fig, ax = plt.subplots(1, 2, figsize=(10.7, 3.2))
    fig.subplots_adjust(left=.17, right=.985, bottom=.18, top=.84, wspace=.23)
    for a, field, div, xlabel, limit, title in [
        (ax[0], "tpot_ms", 1000, "TPOT (s/token)  ·  lower is better", 40, "A  Decode latency"),
        (ax[1], "ssd", 1, "Demand share (%)  ·  lower is better", 56, "B  Cold-tier access")]:
        rows(a, 3)
        vals = [(r["metrics"]["hit_pct"][field] if field == "ssd"
                 else r["metrics"][field] / div) for _, r in groups]
        for y, (v, color) in enumerate(zip(vals, [GRAY, GRAY, BLUE])):
            a.plot([0, v], [y, y], color=color, lw=1.8, alpha=.72)
            a.scatter(v, y, s=90 if y == 2 else 65, color=color, edgecolor="white", zorder=3)
            a.annotate(f"{v:.1f}", (v, y), xytext=(8, 0), textcoords="offset points",
                       va="center", fontsize=10, weight="bold" if y == 2 else "normal")
        a.set_xlim(0, limit)
        a.set_yticks(range(3), [name for name, _ in groups] if a is ax[0] else [""] * 3)
        a.invert_yaxis()
        a.set_xlabel(xlabel)
        a.set_title(title, loc="left", fontweight="bold", color=DARK)
        style(a)
    save(fig, "retention")


def budget_figure(data: dict):
    budget = data["budget"]
    order = ["naive", "swapmoe", "ours", "flashmoe_rf_adaptation", "fiddler"]
    fig, ax = plt.subplots(1, 2, figsize=(10.7, 3.65))
    fig.subplots_adjust(left=.18, right=.985, bottom=.17, top=.82, wspace=.22)
    for a, field, limit, title, xlabel in [
        (ax[0], "tpot_ms", 29, "A  Decode latency", "TPOT (s/token)  ·  lower is better"),
        (ax[1], "ssd", 51, "B  Cold-tier access", "Demand share (%)  ·  lower is better")]:
        rows(a, len(order))
        for y, p in enumerate(order):
            values = [(budget[c][p]["metrics"]["hit_pct"][field] if field == "ssd"
                       else budget[c][p]["metrics"][field] / 1000) for c in (30, 60)]
            col = BLUE if p == "ours" else GRAY
            a.plot(values, [y, y], color=col, lw=2 if p == "ours" else 1.35, alpha=.75)
            a.scatter(values[0], y, s=59, facecolor="white", edgecolor=col,
                      linewidth=1.7, zorder=3)
            a.scatter(values[1], y, s=65, facecolor=col, edgecolor="white", zorder=3)
            if p == "ours":
                a.annotate(f"{values[0]:.1f}", (values[0], y), xytext=(5, 9),
                           textcoords="offset points", fontsize=9, color=BLUE)
                a.annotate(f"{values[1]:.1f}", (values[1], y), xytext=(5, -13),
                           textcoords="offset points", fontsize=9, color=BLUE)
        a.set_xlim(-1, limit)
        a.set_yticks(range(len(order)), [NAMES[p] for p in order] if a is ax[0] else [""] * len(order))
        a.invert_yaxis()
        a.set_xlabel(xlabel)
        a.set_title(title, loc="left", fontweight="bold", color=DARK)
        style(a)
    fig.text(.72, .94, "○  CPU 30 GB     ●  CPU 60 GB", color=DARK, fontsize=10)
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
