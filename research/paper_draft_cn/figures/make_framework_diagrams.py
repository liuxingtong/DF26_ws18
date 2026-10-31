"""Render wide, English-language PNG flowcharts for the paper."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = Path(__file__).resolve().parent
BLUE, ORANGE, GREEN, RED = "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"
INK, EDGE = "#222222", "#888888"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def base(title, width=19, height=5.4):
    fig, ax = plt.subplots(figsize=(width, height), dpi=180)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(.5, .94, title, ha="center", va="center", fontsize=17, weight="bold")
    return fig, ax


def box(ax, x, y, w, h, title, detail="", edge=EDGE):
    ax.add_patch(FancyBboxPatch(
        (x, y - h / 2), w, h,
        boxstyle="round,pad=0.007,rounding_size=0.016",
        facecolor="white", edgecolor=edge, linewidth=1.25))
    ax.text(x + w / 2, y + (0.018 if detail else 0), title,
            ha="center", va="center", fontsize=10.1, weight="bold", color=INK)
    if detail:
        ax.text(x + w / 2, y - .031, detail,
                ha="center", va="center", fontsize=7.5, color="#444444")


def arrow(ax, x1, y1, x2, y2, color=EDGE):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10,
        linewidth=1.2, color=color, shrinkA=0, shrinkB=0))


def bus(ax, incoming, outgoing, x0, x1, start, end, centers, colors):
    """Connect one stage to three branches and merge at the next stage."""
    y = .5
    ax.plot((incoming, x0), (y, y), color=EDGE, lw=1.2)
    ax.plot((x0, x0), (min(centers), max(centers)), color=EDGE, lw=1.2)
    for cy, color in zip(centers, colors):
        arrow(ax, x0, cy, start, cy, color)
        ax.plot((end, x1), (cy, cy), color=color, lw=1.2)
    ax.plot((x1, x1), (min(centers), max(centers)), color=EDGE, lw=1.2)
    arrow(ax, x1, y, outgoing, y)


def finish(fig, name):
    fig.savefig(HERE / name, bbox_inches="tight", pad_inches=.12, facecolor="white")
    plt.close(fig)


def conceptual():
    fig, ax = base("From Urban Evidence to Spatial Decisions")
    xs = (.025, .165, .305, .445, .585, .725, .865)
    w, h = .105, .12
    centers = (.72, .5, .28)
    colors = (BLUE, ORANGE, GREEN)
    headings = ("Urban data", "Governance rules", "Form generation",
                "Evaluation", "Pareto solutions", "Role preferences", "Spatial review")
    for x, heading in zip(xs, headings):
        ax.text(x + w / 2, .82, heading, ha="center", fontsize=9.5, color="#555555")
    box(ax, xs[0], .5, w, h, "Urban evidence", "Buildings / streets")
    for cy, title, color in zip(centers, ("Public coordination", "Development growth",
                                          "Residents + heritage"), colors):
        box(ax, xs[1], cy, w, h, title, edge=color)
    box(ax, xs[2], .5, w, h, "Candidates", "Building operations")
    box(ax, xs[3], .5, w, h, "Shared tests", "Constraints + 3 objectives")
    box(ax, xs[4], .5, w, h, "Pareto sets", "One set per scenario")
    for cy, title, color in zip(centers, ("Residents", "Development", "Public planning"), colors):
        box(ax, xs[5], cy, w, h, title, edge=color)
    box(ax, xs[6], .5, w, h, "Spatial review", "3D + building records")
    bus(ax, xs[0] + w, xs[2], .147, .287, xs[1], xs[1] + w, centers, colors)
    for left, right in ((2, 3), (3, 4)):
        arrow(ax, xs[left] + w, .5, xs[right], .5)
    bus(ax, xs[4] + w, xs[6], .707, .847, xs[5], xs[5] + w, centers, colors)
    ax.text(.5, .10, "Each scenario produces a Pareto set; each role can rank every set.",
            ha="center", fontsize=10, color="#555555")
    finish(fig, "conceptual_framework.png")


def workflow():
    fig, ax = base("Generation and Selection Workflow", width=19, height=5.8)
    xs = (.02, .145, .27, .395, .52, .645, .77, .895)
    w, h = .085, .12
    centers = (.72, .5, .28)
    colors = (BLUE, ORANGE, GREEN)
    box(ax, xs[0], .5, w, h, "Frozen input", "Urban + heritage data")
    for cy, title, color in zip(centers, ("Public", "Growth", "Heritage"), colors):
        box(ax, xs[1], cy, w, h, title, "Permissions", color)
    box(ax, xs[2], .5, w, h, "Generate", "Form operations")
    box(ax, xs[3], .5, w, h, "Validate", "Hard constraints")
    for cy, title, color in zip(centers, ("Exposure", "Added GFA", "Ground release"), colors):
        box(ax, xs[4], cy, w, h, title, "Shared objective", color)
    box(ax, xs[5], .5, w, h, "Search", "Pareto sets")
    box(ax, xs[6], .5, w, h, "Rank by role", "3 perspectives")
    box(ax, xs[7], .5, w, h, "Inspect", "3D + building log")
    bus(ax, xs[0] + w, xs[2], .125, .25, xs[1], xs[1] + w, centers, colors)
    arrow(ax, xs[2] + w, .5, xs[3], .5)
    bus(ax, xs[3] + w, xs[5], .5, .625, xs[4], xs[4] + w, centers, colors)
    arrow(ax, xs[5] + w, .5, xs[6], .5)
    arrow(ax, xs[6] + w, .5, xs[7], .5)
    ax.text(.5, .12, "Scenario-specific generation  /  shared evaluation  /  role-specific selection",
            ha="center", fontsize=10, color="#555555")
    finish(fig, "research_workflow.png")


if __name__ == "__main__":
    conceptual()
    workflow()

def operator_chains():
    fig, ax = plt.subplots(figsize=(19, 5.8), dpi=180)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(.5,.94,'Governance Scenarios and Operator Chains',ha='center',fontsize=17,weight='bold',color=INK)
    scenario_colors=(BLUE,ORANGE,GREEN)
    operator_colors={
        'Densify':'#9467bd',
        'Ground release':'#8c564b',
        'Volume splitting':'#17becf',
        'Height redistribution':'#e377c2',
        'Public setback':'#7f7f7f',
        'Courtyard access':'#bcbd22',
    }
    rows=[
        ('Public coordination',['Densify','Public setback','Height redistribution','Courtyard access']),
        ('Development growth',['Densify','Ground release','Volume splitting','Courtyard access']),
        ('Resident + heritage priority',['Ground release','Height redistribution','Public setback','Courtyard access']),
    ]
    ys=(.70,.50,.30)
    for (title,ops),y,sc in zip(rows,ys,scenario_colors):
        box(ax,.035,y,.19,.13,title,'scenario',edge=sc)
        x=.255; arrow(ax,.23,y,x,y)
        for j,op in enumerate(ops):
            w=.13
            box(ax,x,y,w,.13,op,'operator',edge=operator_colors[op])
            if j<3: arrow(ax,x+w+.006,y,x+w+.035,y)
            x += .155
        arrow(ax,x-.02,y,.91,y)
    box(ax,.91,.5,.08,.22,'Candidate','checks + objectives',edge=EDGE)
    ax.text(.5,.08,'Operator colors are consistent across scenarios',ha='center',fontsize=10,color='#555555')
    finish(fig, 'scenario_operator_chains.png')

if __name__ == '__main__':
    operator_chains()
