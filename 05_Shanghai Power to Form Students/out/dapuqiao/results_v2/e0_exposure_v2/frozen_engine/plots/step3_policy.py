"""Step3 图:权力情景的高度乘数热图(红=拔高 / 蓝=压低 / 白=照旧)。"""
import numpy as np
import matplotlib.pyplot as plt
import common
from . import _base


def policy_heatmap(scenarios, show=True):
    """scenarios = common.load_scenarios() 的结果(name -> 政策 dict)。"""
    names = list(scenarios.keys())
    shs = common.STAKEHOLDERS
    mult = np.ones((len(names), len(shs)))
    for i, sn in enumerate(names):
        for j, sh in enumerate(shs):
            mult[i, j] = float((scenarios[sn] or {}).get(sh, {}).get("mult", 1.0))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    vmax = max(float(np.abs(mult - 1.0).max()), 0.1)
    im = ax.imshow(mult, cmap="RdBu_r", vmin=1 - vmax, vmax=1 + vmax, aspect="auto")
    ax.set_xticks(range(len(shs)))
    ax.set_xticklabels(["%s\n%s" % (s, _base.SH_LABEL[s]) for s in shs], fontsize=8)
    ax.set_yticks(range(len(names))); ax.set_yticklabels([_base.display_label(n) for n in names], fontsize=9)
    for i in range(len(names)):
        for j in range(len(shs)):
            pol = (scenarios[names[i]] or {}).get(shs[j], {})
            txt = "×%.2g" % mult[i, j]
            if "cap_m" in pol:
                txt += "\ncap %g m" % pol["cap_m"]
            shade = abs(mult[i, j] - 1.0) / vmax
            ax.text(j, i, txt, ha="center", va="center", fontsize=8,
                    color="white" if shade > 0.55 else "black")
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02).set_label("Multiplier", fontsize=8)
    fig.tight_layout()
    _base.autosave(fig, "policy_heatmap")
    if show:
        plt.show()
    return fig
