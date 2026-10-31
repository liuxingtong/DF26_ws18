from pathlib import Path
import shutil, csv
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
R=Path(__file__).resolve().parents[3]; F=R/'research/paper_draft_cn/figures'; D=R/'05_Shanghai Power to Form Students/data/dapuqiao'; M=R/'05_Shanghai Power to Form Students/out/dapuqiao/results_v2/e0_formal_remote_20261029/matching_disruption'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})
def save(fig,name):
 for ext in ['png','pdf','svg']:fig.savefig(F/f'{name}.{ext}',dpi=300,bbox_inches='tight',pad_inches=.04)
 plt.close(fig)
# new filename prevents cached old image being reused
shutil.copyfile(F/'study_area_satellite.png',F/'study_area_no_overlay.png')
from sys import path
path.insert(0,str(R/'05_Shanghai Power to Form Students'))
from engine.optimization.data import load_study
study=load_study('public_coordination',shared_experiment_controls=True)
b=study.buildings; z=study.zones if hasattr(study,'zones') else gpd.read_file(D/'intervention_zones.geojson').to_crs(b.crs)
colors={'resident':'#0072B2','developer':'#E69F00','state':'#009E73','unknown':'#BDBDBD'}
fig,ax=plt.subplots(figsize=(6.3,4.1))
b.plot(ax=ax,color=b.stakeholder_proxy.map(colors).fillna('#BDBDBD'),edgecolor='white',linewidth=.1)
z.boundary.plot(ax=ax,color='#777777',linewidth=.35)
b[b.heritage].boundary.plot(ax=ax,color='#111111',linewidth=1)
b[b.zone_id.isna()].boundary.plot(ax=ax,color='#CC79A7',linewidth=.9)
ax.set_axis_off();ax.set_aspect('equal')
handles=[Line2D([],[],marker='s',ls='',color=c,label=k.title()) for k,c in colors.items()]
handles += [Line2D([],[],color='#111111',label='Heritage freeze'),Line2D([],[],color='#CC79A7',label='Unmatched unit')]
ax.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,-.12),ncol=3,frameon=False,fontsize=7)
save(fig,'fig1_stakeholder_labels')
# matching figures show per-seed values plus median and range, rather than treating averaged extremes as single plans
read=lambda f:list(csv.DictReader(open(M/f,encoding='utf-8-sig')))
a=read('matched_capacity_detail.csv');b=read('matched_disruption_detail.csv')
fig,axs=plt.subplots(1,2,figsize=(6.3,2.8))
for method,color,offset in [('PC','#0072B2',-.012),('DG','#E69F00',.012)]:
 for metric,sty in [('min_disruption_pct','-'),('mean_disruption_pct','--')]:
  x=[.2,.4,.6]; vals=[[float(r[metric]) for r in a if r['method']==method and float(r['capacity_band_pct'])==v and r[metric] not in ('','None')] for v in x]
  axs[0].plot(np.array(x)+offset,[np.median(v) for v in vals],sty,marker='o',ms=3,color=color,label=method+(' minimum' if sty=='-' else ' mean'))
 for ceiling in [0,5,10,20,30]:
  vals=[float(r['max_capacity_pct']) for r in b if r['method']==method and float(r['disruption_ceiling_pct'])==ceiling and r['max_capacity_pct'] not in ('','None')]
  axs[1].scatter(np.full(len(vals),ceiling+offset*25),vals,color=color,alpha=.25,s=8)
 x=[0,5,10,20,30];ys=[np.median([float(r['max_capacity_pct']) for r in b if r['method']==method and float(r['disruption_ceiling_pct'])==v]) for v in x]
 axs[1].plot(x,ys,marker='o',ms=3,color=color,label=method)
axs[0].set(xlabel='Target net floor-area change (%)',ylabel='Residential exposure (%)',xticks=[.2,.4,.6]);axs[1].set(xlabel='Residential exposure ceiling (%)',ylabel='Maximum net floor-area change (%)',xticks=[0,5,10,20,30]);
for ax in axs:ax.grid(axis='y',color='#eeeeee');ax.legend(frameon=False,fontsize=6,loc='upper center',bbox_to_anchor=(.5,1.25),ncol=2)
fig.tight_layout(w_pad=1.4);save(fig,'fig_e6_matched_tradeoffs')
print('generated labels and E6 figures')
