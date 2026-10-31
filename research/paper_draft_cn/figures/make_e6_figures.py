"""Draw matched comparisons from a completed E6 batch; preserve unmatched gaps."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

METHODS={'BL':('#777777','s'),'PC':('#0072B2','o'),'DG':('#E69F00','^'),'RH':('#009E73','D')}


def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def make(source, output):
    capacity=read(source/'matched_capacity_detail.csv')
    disruption=read(source/'matched_disruption_detail.csv')
    panels=[(capacity,'capacity_band_pct','min_disruption_pct','Target net floor-area change (%)','Minimum residential exposure (%)'),
            (disruption,'disruption_ceiling_pct','max_capacity_pct','Residential exposure ceiling (%)','Maximum net floor-area change (%)')]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,'svg.fonttype':'none',
                         'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(6.5,2.8),layout='constrained')
    audit=[]
    for ax,(rows,xkey,ykey,xlabel,ylabel) in zip(axes,panels):
        xs=sorted({float(r[xkey]) for r in rows})
        for index,(method,(color,marker)) in enumerate(METHODS.items()):
            medians=[]
            for x in xs:
                all_rows=[r for r in rows if r['method']==method and float(r[xkey])==x]
                if len(all_rows)!=10:raise ValueError(f'Expected 10 seeds for {method}, {xkey}={x}')
                values=[float(r[ykey]) for r in all_rows if r[ykey] not in ('','None')]
                medians.append(float(np.median(values)) if values else np.nan)
                audit.append(dict(method=method,condition=xkey,value=x,matched_seeds=len(values),
                                  median=medians[-1] if values else None,
                                  minimum=min(values) if values else None,maximum=max(values) if values else None))
                if values:
                    ax.plot([x,x],[min(values),max(values)],c=color,lw=.7,alpha=.5)
                    jitter=(xs[-1]-xs[0])*.006 if len(xs)>1 else 0
                    ax.scatter(x+np.linspace(-jitter,jitter,len(values)),values,c=color,s=7,alpha=.3,marker=marker)
                    if len(values)<10:ax.annotate(f'n={len(values)}',(x,medians[-1]),xytext=(3,4),textcoords='offset points',fontsize=6,color=color)
            ax.plot(xs,medians,c=color,marker=marker,ms=3,lw=1,label=method)
        ax.set(xlabel=xlabel,ylabel=ylabel,xticks=xs)
        ax.grid(axis='y',color='#e8e8e8',lw=.5);ax.set_axisbelow(True)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside upper center',ncol=4,frameon=False,fontsize=8)
    output.mkdir(parents=True,exist_ok=True)
    for ext in ('png','pdf','svg'):fig.savefig(output/f'fig4_e6_matched_tradeoffs.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig)
    with (output/'fig4_e6_plot_values.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
    provenance=dict(statistic='Median of per-seed optima; whiskers show seed min/max; faint points show individual seeds',
        missing='Unmatched conditions remain absent; lines stop at missing values; no interpolation',
        sources={str(source/name):hashlib.sha256((source/name).read_bytes()).hexdigest() for name in ['matched_capacity_detail.csv','matched_disruption_detail.csv']})
    (output/'fig4_e6_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('Saved E6 figures and plotting data')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--matching-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();make(a.matching_root,a.output)
