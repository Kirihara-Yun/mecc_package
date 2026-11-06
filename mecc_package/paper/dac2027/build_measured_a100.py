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

BLUE = "#4279A8"
MID = "#84AFBD"
GRAY = "#A8ADB3"
ORANGE = "#D59A60"
TEAL = "#76A68B"
DARK = "#233646"
POLICIES = ["naive", "swapmoe", "independent", "ours_io", "ours", "flashmoe_rf_adaptation", "fiddler"]
NAMES = {"naive": "Streaming", "swapmoe": "Fixed CPU", "independent": "Independent",
         "ours_io": "MECC I/O", "ours": "MECC", "flashmoe_rf_adaptation": "RF adapter",
         "fiddler": "CPU compute"}
COLORS = {"naive": GRAY, "swapmoe": ORANGE, "independent": ORANGE,
          "ours_io": MID, "ours": BLUE, "flashmoe_rf_adaptation": TEAL,
          "fiddler": "#A4ADB5"}

plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman"],
                     "font.size": 11, "axes.titlesize": 11, "axes.labelsize": 10,
                     "xtick.labelsize": 10, "ytick.labelsize": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.facecolor": "white", "figure.facecolor": "white",
                     "pdf.fonttype": 42, "svg.fonttype": "none", "hatch.linewidth": .8})


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
    ax.tick_params(length=3, pad=7, color=DARK)
    ax.spines["left"].set_color(DARK)
    ax.spines["bottom"].set_color(DARK)


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
    fig, ax = plt.subplots(1, 3, figsize=(10.7, 3.65),
                           gridspec_kw={"width_ratios": [1.13, 1, 1]})
    fig.subplots_adjust(left=.17, right=.985, bottom=.18, top=.84, wspace=.23)
    labels = [NAMES[p] for p in order]
    n = len(order)
    colors = [ORANGE, GRAY, GRAY, MID, BLUE, TEAL]
    hatches = ["\\\\", "///", "...", "---", "xxx", "+++"]
    for a, metric, limit, ticks, title, xlabel in [
        (ax[0], "tpot_ms", 25, [0, 10, 20], "(a) Decode latency", "TPOT (s/token)"),
        (ax[1], "ttft_ms", 455, [0, 200, 400], "(b) First token", "TTFT (s)"),
        (ax[2], "ssd", 39, [0, 10, 20, 30], "(c) Cold-tier access", "Demand share (%)")]:
        values = []
        for y, p in enumerate(order):
            value = (main[p]["metrics"]["hit_pct"]["ssd"] if metric == "ssd"
                     else main[p]["metrics"][metric] / 1000)
            values.append(value)
        bars = a.barh(range(n), values, height=.68, color=colors,
                      edgecolor=DARK, linewidth=.65, zorder=3)
        for bar, hatch in zip(bars, hatches): bar.set_hatch(hatch)
        a.bar_label(bars, labels=[f"{v:.1f}" for v in values], padding=3, fontsize=8)
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
    fig, ax = plt.subplots(1, 2, figsize=(10.7, 3.45),
                           gridspec_kw={"width_ratios": [1, 1.22]})
    fig.subplots_adjust(left=.16, right=.985, bottom=.21, top=.83, wspace=.28)
    vals = [r["metrics"]["tpot_ms"] / 1000 for _, r in groups]
    bars = ax[0].barh(range(3), vals, height=.56, color=[GRAY, ORANGE, BLUE],
                      edgecolor=DARK, linewidth=.65, zorder=3)
    for bar, hatch in zip(bars, ["///", "\\\\", "xxx"]): bar.set_hatch(hatch)
    ax[0].bar_label(bars, labels=[f"{v:.1f}" for v in vals], padding=4, fontsize=9)
    ax[0].set_xlim(0, 40); ax[0].set_xticks([0,10,20,30,40])
    ax[0].set_yticks(range(3), [name for name, _ in groups]); ax[0].invert_yaxis()
    ax[0].set_xlabel("TPOT (s/token)")
    ax[0].set_title("(a) Decode latency", loc="left", fontweight="bold", color=DARK)
    style(ax[0])
    left = np.zeros(3)
    for tier, color, hatch in [("hbm",BLUE,"xxx"),("cpu",TEAL,"///"),("ssd",ORANGE,"\\\\")]:
        values=np.array([r["metrics"]["hit_pct"][tier] for _,r in groups])
        ax[1].barh(range(3),values,left=left,height=.56,color=color,edgecolor=DARK,
                   linewidth=.5,hatch=hatch,label={"hbm":"HBM","cpu":"CPU","ssd":"HDD"}[tier])
        for y,(start,value) in enumerate(zip(left,values)):
            if value>=7: ax[1].text(start+value/2,y,f"{value:.1f}",ha="center",va="center",
                                    color="white" if tier=="hbm" else DARK,fontsize=8)
        left+=values
    ax[1].set_xlim(0,101); ax[1].set_xticks([0,25,50,75,100])
    ax[1].set_yticks(range(3),[""]*3); ax[1].invert_yaxis()
    ax[1].set_xlabel("Selected-expert demand share (%)")
    ax[1].set_title("(b) Demand source by tier", loc="left", fontweight="bold", color=DARK)
    ax[1].legend(frameon=False,ncol=3,loc="upper center",bbox_to_anchor=(.5,1.25),fontsize=8)
    style(ax[1])
    save(fig, "retention")


def budget_figure(data: dict):
    budget = data["budget"]
    order = ["naive", "swapmoe", "ours", "flashmoe_rf_adaptation", "fiddler"]
    fig, ax = plt.subplots(1, 2, figsize=(10.7, 4.25))
    fig.subplots_adjust(left=.18, right=.985, bottom=.17, top=.82, wspace=.22)
    for a, field, limit, title, xlabel in [
        (ax[0], "tpot_ms", 29, "(a) Decode latency", "TPOT (s/token)  ·  lower is better"),
        (ax[1], "ssd", 51, "(b) Cold-tier access", "Demand share (%)  ·  lower is better")]:
        vals30, vals60 = [], []
        for y, p in enumerate(order):
            values = [(budget[c][p]["metrics"]["hit_pct"][field] if field == "ssd"
                       else budget[c][p]["metrics"][field] / 1000) for c in (30, 60)]
            vals30.append(values[0]); vals60.append(values[1])
        face=[BLUE if p == "ours" else GRAY for p in order]
        b30=a.barh(np.arange(len(order))-.19,vals30,height=.33,color=face,
                   edgecolor=DARK,linewidth=.6,hatch="///",label="CPU 30 GB",zorder=3)
        b60=a.barh(np.arange(len(order))+.19,vals60,height=.33,color=face,
                   edgecolor=DARK,linewidth=.6,hatch="xxx",label="CPU 60 GB",zorder=3)
        for bars, vals in ((b30,vals30),(b60,vals60)):
            a.bar_label(bars,labels=[f"{v:.1f}" for v in vals],padding=3,fontsize=7.7)
        a.set_xlim(-1, limit)
        a.set_yticks(range(len(order)), [NAMES[p] for p in order] if a is ax[0] else [""] * len(order))
        a.invert_yaxis()
        a.set_xlabel(xlabel)
        a.set_title(title, loc="left", fontweight="bold", color=DARK)
        style(a)
    ax[0].legend(frameon=False,ncol=2,loc="upper right",bbox_to_anchor=(1.0,1.16),fontsize=8)
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
