"""Render the editor graphic from the published SQLite snapshot. Requires Matplotlib."""
from pathlib import Path
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent


def draw():
    db = sqlite3.connect((HERE / "worldcup.db").as_uri() + "?mode=ro", uri=True)
    try:
        rows = db.execute("SELECT * FROM knockout_summary ORDER BY tournament").fetchall()
    finally:
        db.close()
    paper, ink, muted = "#f8f7f2", "#142c39", "#425864"
    colors = ["#28516c", "#a6c9c7", "#d9943a"]
    title_labels = ["Regulation", "Extra time", "Penalty shoot-out"]
    fig, ax = plt.subplots(figsize=(11, 6.8))
    fig.patch.set_facecolor(paper)
    ax.set_facecolor(paper)
    fig.subplots_adjust(left=.22, right=.96, top=.71, bottom=.235)
    fig.text(.045,.906,"How World Cup knockout matches were decided",fontsize=23,weight="bold",color=ink)
    fig.text(.047,.852,"Each bar represents one tournament. The numbers inside are match counts.",fontsize=12,color=muted)
    fig.legend([Patch(facecolor=c) for c in colors],title_labels,loc="upper left",
               bbox_to_anchor=(.045,.815),frameon=False,ncol=3,handlelength=1.2,
               columnspacing=1.8,borderaxespad=0,fontsize=11,labelcolor=ink)
    for pos, (year, total, *counts) in enumerate(rows):
        ax.text(-.032,pos,f"{year}   ·   {total} matches",transform=ax.get_yaxis_transform(),
                ha="right",va="center",fontsize=11,color=ink)
        left = 0
        for i, count in enumerate(counts):
            if count == 0:
                continue
            width = count / total
            ax.barh(pos,width,left=left,height=.64,color=colors[i],edgecolor=paper,linewidth=1.2)
            ax.text(left+width/2,pos,str(count),ha="center",va="center",fontsize=13,
                    weight="bold",color="white" if i == 0 else ink)
            left += width
    ax.set_xlim(0,1)
    ax.set_ylim(len(rows)-.5,-.5)
    ax.set_yticks([])
    ax.set_xticks([0,.25,.5,.75,1])
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1,decimals=0))
    ax.tick_params(axis="x",length=0,labelsize=10,colors=muted,pad=5)
    for spine in ax.spines.values():
        spine.set_visible(False)
    total = sum(row[1] for row in rows)
    after_90 = sum(row[3] + row[4] for row in rows)
    pens = sum(row[4] for row in rows)
    fig.text(.047,.132,f"{after_90} of {total} matches went beyond regulation. {pens} ended in a shoot-out.",
             fontsize=13,weight="bold",color=ink)
    fig.text(.047,.082,"Includes third-place matches. The 2026 knockout stage began with a round of 32.",
             fontsize=10,color=muted)
    fig.text(.047,.042,"Data from OpenFootball (CC0). Analysis and graphic by ParlayAPI.",fontsize=9,color=muted)
    target = HERE.parents[1] / "press" / "world-cup-knockout-results.png"
    fig.savefig(target,dpi=180,facecolor=paper)
    plt.close(fig)
    return target


if __name__ == "__main__":
    print(draw())
