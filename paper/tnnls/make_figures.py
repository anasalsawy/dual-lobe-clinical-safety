"""Regenerate the manuscript figures as print-friendly, column-width graphics.

IEEE column width is 3.5 in (88 mm); text in figures uses an Arial-metric
sans-serif font at >= 8 pt so it stays legible after reduction.
Outputs both vector PDF (for final submission) and 600-dpi PNG (for Word).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Ellipse, Polygon

OUT = Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "Liberation Sans",
    "font.size": 8,
    "pdf.fonttype": 42,
    "savefig.dpi": 600,
})

INK = "#1a1a1a"
GREY = "#6b6b6b"
LIGHT = "#ececec"
BLUE = "#1f5a96"
BLUE_L = "#dce8f5"
ORANGE = "#b3541e"
ORANGE_L = "#fbe6d8"
GREEN = "#2e7d32"
GREEN_L = "#e1f0e2"
COL_W = 3.5


def canvas(h, w=COL_W):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100 * h / w)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc="white", ec=INK, lw=0.8, ls="-", fs=8,
        weight="normal", color=INK, r=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            weight=weight, color=color, linespacing=1.15)


def arrow(ax, p, q, color=INK, lw=0.8, ls="-", rad=0.0, ms=7):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=ms, color=color,
                                 lw=lw, ls=ls, shrinkA=0, shrinkB=0,
                                 connectionstyle=f"arc3,rad={rad}"))


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png")
    plt.close(fig)


# Fig. 1 -- prompt-echo effect ---------------------------------------------
def fig1():
    fig, ax = canvas(2.35)
    ax.text(2, 64, "Asked questions $Q_u$", fontsize=8, weight="bold")
    ax.text(38, 64, "Active trajectory", fontsize=8, weight="bold")
    ax.text(72, 64, r"Unasked $Q^*\!\setminus Q_u$", fontsize=8, weight="bold", color=ORANGE)
    qs = ["How do I build X?", "Which framework?", "Why is it failing?"]
    ans = ["Build plan", "Framework\ncomparison", "Debugging path"]
    for i, (q, a) in enumerate(zip(qs, ans)):
        y = 50 - i * 14
        box(ax, 2, y, 30, 10, q)
        box(ax, 38, y, 28, 10, a, fc=BLUE_L, ec=BLUE)
        arrow(ax, (32, y + 5), (38, y + 5))
    # latent space
    ax.add_patch(FancyBboxPatch((70, 8), 28, 54, boxstyle="round,pad=0,rounding_size=2",
                                fc=ORANGE_L, ec=ORANGE, lw=0.8, ls=(0, (3, 2))))
    lat = ["Existing\nsolution?", "Cheaper\npath?", "Hidden\nconstraint?", "Critical\nrisk?"]
    for i, t in enumerate(lat):
        cy = 53 - i * 12.5
        ax.add_patch(Ellipse((84, cy), 22, 10, fc="white", ec=ORANGE, lw=0.7, ls=(0, (2, 1.5))))
        ax.text(84, cy, t, ha="center", va="center", fontsize=7, color=ORANGE, linespacing=1.0)
    ax.text(50, 2.5, "Branches never asked about never enter the active trajectory.",
            ha="center", fontsize=7, style="italic", color=GREY)
    save(fig, "fig1_prompt_echo")


# Fig. 2 -- prompt-space prediction ----------------------------------------
def fig2():
    fig, ax = canvas(3.3)
    ax.text(2, 90, "(a) Continuation-centric path", fontsize=8, weight="bold")
    xs = [2, 35, 68]
    labels = [r"Prompt $q_0$", "Answer trajectory", "Detailed output"]
    for x, t in zip(xs, labels):
        box(ax, x, 77, 30, 9, t)
    arrow(ax, (32, 81.5), (35, 81.5))
    arrow(ax, (65, 81.5), (68, 81.5))

    ax.text(2, 70, "(b) Proposed context-expansion path", fontsize=8, weight="bold")
    box(ax, 30, 58, 40, 9, r"User intent $I$, prompt $q_0$", fc=BLUE_L, ec=BLUE)
    ax.add_patch(FancyBboxPatch((2, 25), 96, 28, boxstyle="round,pad=0,rounding_size=2",
                                fc="white", ec=GREY, lw=0.7, ls=(0, (3, 2))))
    ax.text(4, 49.5, r"Predicted latent questions $Q_L$", fontsize=7, color=GREY, style="italic")
    qs = [r"$q_1$: Exists?", r"$q_2$: Constraints?", r"$q_3$: Alternatives?",
          r"$q_4$: Risks?", r"$q_5$: Decisive?", r"$q_6$: Actual goal?"]
    for k, t in enumerate(qs):
        cx, cy = 18 + (k % 3) * 32, 41 - (k // 3) * 10
        ax.add_patch(Ellipse((cx, cy), 29, 8, fc=LIGHT, ec=GREY, lw=0.6))
        ax.text(cx, cy, t, ha="center", va="center", fontsize=7)
    arrow(ax, (50, 58), (50, 53))
    arrow(ax, (50, 25), (50, 22))
    box(ax, 20, 13, 60, 9, r"Expanded context $C^+$", fc=ORANGE_L, ec=ORANGE)
    arrow(ax, (50, 13), (50, 9))
    box(ax, 20, 0.8, 60, 8.2, r"Informed response $a_0 \sim P(a_0\mid C^+)$", fc=GREEN_L, ec=GREEN)
    save(fig, "fig2_prompt_space")


# Fig. 3 -- coarse-to-fine ---------------------------------------------------
def house(ax, x0, y0, s, level):
    w, h, roof = 16 * s, 12 * s, 7 * s
    ax.add_patch(Polygon([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0 + w / 2, y0 + h + roof),
                          (x0, y0 + h)], closed=True, fc="white", ec=INK, lw=0.9))
    if level >= 2:
        for wx in (x0 + 2 * s, x0 + w - 5.5 * s):
            ax.add_patch(plt.Rectangle((wx, y0 + 7 * s), 3.5 * s, 3 * s, fc="white", ec=INK, lw=0.7))
        ax.add_patch(plt.Rectangle((x0 + w / 2 - 2 * s, y0), 4 * s, 6 * s, fc="white", ec=INK, lw=0.7))
    if level >= 3:
        ax.plot([x0, x0 + w], [y0 + 3 * s, y0 + 3 * s], color=GREY, lw=0.5)
        ax.plot([x0 + w / 2] * 2, [y0 + h, y0 + h + roof * 0.7], color=GREY, lw=0.5)
    if level >= 4:
        ax.plot([x0 + w / 2 + 1.2 * s], [y0 + 3 * s], "o", ms=1.2, color=INK)
        for k in range(5):
            xx = x0 + 3 * s + k * 2.4 * s
            ax.plot([xx, xx + 1 * s], [y0 + h - 0.6 * s, y0 + h - 1.6 * s], color=ORANGE, lw=0.5)


def fig3():
    fig, ax = canvas(1.55)
    titles = ["Pass 1\nGlobal outline", "Pass 2\nMajor structure", "Pass 3\nSubstructure", "Pass 4\nDetails"]
    for i, t in enumerate(titles):
        x = 2 + i * 25
        ax.add_patch(FancyBboxPatch((x, 2), 21, 40, boxstyle="round,pad=0,rounding_size=1.5",
                                    fc=LIGHT if i < 3 else BLUE_L, ec=GREY, lw=0.6))
        ax.text(x + 10.5, 36, t, ha="center", va="center", fontsize=6.5, weight="bold", linespacing=1.1)
        house(ax, x + 3.5, 6, 0.87, i + 1)
        if i < 3:
            arrow(ax, (x + 21, 20), (x + 25, 20), ms=6)
    save(fig, "fig3_coarse_to_fine")


# Fig. 4 -- launchpad hypothesis --------------------------------------------
def fig4():
    fig, ax = canvas(1.85)
    box(ax, 2, 4, 36, 36, "", fc=LIGHT, ec=GREY)
    ax.text(20, 34.5, "Today", ha="center", fontsize=8, weight="bold")
    ax.text(4, 18, "\u2022 Large latent capability\n\u2022 Growing tool access\n"
            "\u2022 Strong local execution\n\u2022 User steers the spotlight",
            fontsize=6.8, va="center", linespacing=1.4)
    box(ax, 62, 4, 36, 36, "", fc=BLUE_L, ec=BLUE)
    ax.text(80, 34.5, "After expansion", ha="center", fontsize=8, weight="bold", color=BLUE)
    ax.text(64, 18, "\u2022 Proactive questioning\n\u2022 Broader context\n"
            "\u2022 Greater autonomy\n\u2022 Larger cost of error",
            fontsize=6.8, va="center", linespacing=1.4)
    ax.add_patch(plt.Rectangle((43.5, 4), 13, 36, fc=ORANGE_L, ec=ORANGE, lw=0.8, hatch="////"))
    ax.text(50, 22, "Open\nSesame\nbarrier", ha="center", va="center", fontsize=6.8, weight="bold",
            color=ORANGE, bbox=dict(fc="white", ec="none", pad=1))
    arrow(ax, (30, 41.5), (70, 41.5), color=BLUE, lw=1.0, rad=-0.12)
    ax.text(50, 47, "prompt-space prediction", ha="center", fontsize=6.5, color=BLUE, style="italic")
    save(fig, "fig4_launchpad")


# Fig. 5 -- dual-lobe supervision -------------------------------------------
def fig5():
    fig, ax = canvas(3.2)
    box(ax, 26, 83, 48, 7.5, r"User intent $I$ and request $q_0$")
    ax.add_patch(FancyBboxPatch((2, 26), 40, 50, boxstyle="round,pad=0,rounding_size=2",
                                fc=BLUE_L, ec=BLUE, lw=0.9))
    ax.text(22, 71, "Lobe A\nGenerator / Executor", ha="center", va="center", fontsize=7.5,
            weight="bold", color=BLUE, linespacing=1.1)
    ax.text(4, 51, "\u2022 Expand prompt space\n\u2022 Coarse-to-fine\n   representation\n"
            "\u2022 Reason through task\n\u2022 Use tools, resources\n\u2022 Produce candidate",
            fontsize=6.8, va="center", linespacing=1.35)
    ax.add_patch(FancyBboxPatch((58, 26), 40, 50, boxstyle="round,pad=0,rounding_size=2",
                                fc=ORANGE_L, ec=ORANGE, lw=0.9))
    ax.text(78, 71, "Lobe B\nIndependent Supervisor", ha="center", va="center", fontsize=7.5,
            weight="bold", color=ORANGE, linespacing=1.1)
    ax.text(60, 52, "\u2022 Find omitted branches\n\u2022 Verify claims\n"
            "\u2022 Check tool use vs. claims\n\u2022 Detect intent shift\n\u2022 Detect fixation\n"
            "\u2022 Enforce safety rules",
            fontsize=6.8, va="center", linespacing=1.35)
    box(ax, 60, 28, 36, 7.5, "Own retrieval, rule sets,\nthresholds", fc="white", ec=ORANGE,
        fs=6.3, ls=(0, (3, 2)))
    arrow(ax, (40, 83), (22, 76))
    arrow(ax, (60, 83), (78, 76), ls=(0, (3, 2)))
    ax.text(83, 79, "intent only", fontsize=6.3, color=GREY, style="italic")
    arrow(ax, (42, 58), (58, 58))
    ax.text(50, 60, "candidate", ha="center", fontsize=6.3, color=GREY)
    arrow(ax, (58, 46), (42, 46), color=ORANGE)
    ax.text(50, 40.5, "revise /\nask", ha="center", fontsize=6.3, color=ORANGE, linespacing=1.0)
    box(ax, 2, 3, 40, 9, "Approved final answer", fc=GREEN_L, ec=GREEN, weight="bold", fs=7.2)
    box(ax, 58, 3, 40, 9, "Escalate to human", fc="white", ec=ORANGE, weight="bold",
        color=ORANGE, fs=7.2)
    arrow(ax, (62, 26), (30, 12), color=GREEN, rad=0.1)
    ax.text(40, 20, "pass", fontsize=6.3, color=GREEN)
    arrow(ax, (84, 26), (84, 12), color=ORANGE)
    ax.text(86, 18, "unresolved", fontsize=6.3, color=ORANGE)
    save(fig, "fig5_dual_lobe")


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5):
        f()
    print("figures written to", OUT)
