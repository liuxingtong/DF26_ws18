"""Figures from exact BL merged-front analysis, all source files are CSV."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize
R=Path(__file__).resolve().parents[3]; F=Path(__file__).resolve().parent
D=R/'05_Shanghai Power to Form Students/out/dapuqiao/results_v2/e0_formal_remote_20261029/baseline_dominance_pareto'
read=lambda p:list(csv.DictReader(open(p,encoding='utf-8-sig')))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})
def save(fig,name):
 for ext in ['png','pdf','svg']:fig.savefig(F/f'{name}.{ext}',dpi=300,bbox_inches='tight',pad_inches=.04)
 plt.close(fig)
rows=read(D/'pareto_annotated.csv'); base=read(D/'baseline_merged_front.csv')
norm=Normalize(0,max(float(r['residential_disruption'])*100 for r in rows)); cmap=plt.get_cmap('viridis')
# Re-filter per-method union for display; seed summary denominator remains exported per-seed Pareto set.
import sys
sys.path.insert(0,str(R/'05_Shanghai Power to Form Students/scripts'))
from analyze_dapuqiao_baseline_dominance import front
fig,axs=plt.subplots(1,3,figsize=(6.3,2.5),sharex=True,sharey=True)
for ax,method,marker in zip(axs,['PC','DG','RH'],['o','^','s']):
 ax.scatter([float(r['development_capacity'])*100 for r in base],[float(r['street_connected_released_ground'])*100 for r in base],s=6,c='#7F7F7F',alpha=.45,linewidths=0,label='BL')
 rr=front([r for r in rows if r['method']==method])
 for outside in [False,True]:
  q=[r for r in rr if (r['dominated_by_baseline'].lower()=='false')==outside]
  ax.scatter([float(r['development_capacity'])*100 for r in q],[float(r['street_connected_released_ground'])*100 for r in q],c=[float(r['residential_disruption'])*100 for r in q],cmap=cmap,norm=norm,s=15,marker=marker,edgecolors='black' if outside else 'none',linewidths=.55)
 ax.text(.04,.95,method,transform=ax.transAxes,va='top');ax.grid(color='#eeeeee',lw=.4);ax.set_xlabel('Net floor-area change (%)')
axs[0].set_ylabel('Street-adjacent ground release (%)')
fig.subplots_adjust(wspace=.25,bottom=.25,right=.86)
for ax in axs: ax.tick_params(labelsize=7)
cax=fig.add_axes([.9,.27,.014,.55]);cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax);cb.set_label('Residential exposure (%)',fontsize=7)
fig.legend(handles=[Line2D([],[],marker='o',ls='',color='#7F7F7F',label='BL merged front'),Line2D([],[],marker='o',ls='',markerfacecolor='white',markeredgecolor='black',label='Not dominated by BL')],loc='upper center',bbox_to_anchor=(.45,1.08),ncol=2,frameon=False,fontsize=7)
save(fig,'fig3_merged_pareto_fronts')
for ax in axs:
 ax.set_xlim(-.5,1.5);ax.set_ylim(-.01,.45)
save(fig,'fig3_merged_pareto_zoom')
# Statistics figure: each dot is one seed. Median and min/max are distinct.
detail=read(D/'dominance_by_seed.csv');summary=read(D/'dominance_summary.csv')
fig,ax=plt.subplots(figsize=(3.2,2.6));colors=['#0072B2','#E69F00','#009E73']
for i,(method,color) in enumerate(zip(['PC','DG','RH'],colors)):
 vals=[float(r['not_dominated_pct']) for r in detail if r['method']==method]
 r=next(r for r in summary if r['method']==method); med=float(r['median_pct']);lo=float(r['min_pct']);hi=float(r['max_pct'])
 ax.scatter(i+np.linspace(-.09,.09,len(vals)),vals,s=12,color=color,alpha=.65)
 ax.plot([i,i],[lo,hi],color=color,lw=1);ax.plot([i-.15,i+.15],[med,med],color='black',lw=1.5)
ax.set(xticks=[0,1,2],xticklabels=['PC','DG','RH'],ylim=(-3,103),ylabel='Pareto solutions not dominated by BL (%)');ax.grid(axis='y',color='#eeeeee');fig.tight_layout();save(fig,'fig3_baseline_nondominated_share')
print('Generated shared-scale fronts and per-seed dominance statistics.')
