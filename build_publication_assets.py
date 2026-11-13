#!/usr/bin/env python3
"""Rebuild all paper tables and figures from the core DSCC/QVAR/HybridMetrics run.

Expected results directory structure:
  results/DSCC/DSCC_{garch,egarch}_summary.txt
  results/DSCC/tables/DSCC_{garch,egarch}_conditional_correlations.csv
  results/DSCC/rolling_backtest_window_{756,1008}/(performance_table,pairwise,turnover_table).csv
  results/QVAR/tables/QVAR_lag{1,2}_{X,Y}.csv
  results/QVAR/tables/QVAR_lag{1,2}_tau{0.10,0.50,0.90}_coefficient_matrix.csv
  results/QVAR/tables/QVAR_lag{1,2}_summary.txt
  results/HybridMetrics/hybridmetrics_unit_root_battery.csv

Returns must be the frozen decimal log-return file. The model outputs use returns
multiplied by 100, while this script makes that transformation explicitly.
No optional NPCQ, TVNCQ, or DeepTVAR analyses are included.
"""
from __future__ import annotations
import argparse, re, json, hashlib, platform, time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ASSETS=['Nasdaq100_ETF','Bitcoin','Clean_Energy_ETF','Oil_Linked_ETF']
VARS=ASSETS+['VIX']
TAUS=[0.10,0.50,0.90]
LAGS=[1,2]
WINDOWS=[756,1008]

def clean_csv(path:Path, **kwargs):
    df=pd.read_csv(path, **kwargs)
    return df.loc[:,~df.columns.astype(str).str.startswith('Unnamed:')]

def parse_model_fit(results:Path)->pd.DataFrame:
    rows=[]
    for model,fn in [('DSCC-lambda-GARCH','DSCC_garch_summary.txt'),('DSCC-lambda-EGARCH','DSCC_egarch_summary.txt')]:
        txt=(results/'DSCC'/fn).read_text(encoding='utf-8',errors='replace')
        def grab(label):
            m=re.search(rf'{re.escape(label)}:\s*(-?\d+(?:\.\d+)?)',txt)
            if not m: raise ValueError(f'Cannot parse {label} from {fn}')
            return float(m.group(1))
        conv=bool(re.search(r'Converged:\s*yes',txt,re.I))
        rows.append({'Model':model.replace('lambda','λ'),'Log_likelihood':grab('Log-likelihood'),'AIC':grab('AIC'),'BIC':grab('BIC'),'Converged':'Yes' if conv else 'No'})
    return pd.DataFrame(rows)

def holm_adjust(pvals):
    p=np.asarray(pvals,dtype=float); n=len(p); order=np.argsort(p); out=np.empty(n); running=0.0
    for rank,idx in enumerate(order):
        running=max(running,min(1.0,(n-rank)*p[idx])); out[idx]=running
    return out

def build_qvar(results:Path, table_dir:Path):
    qdir=results/'QVAR'/'tables'
    metrics=[]; crossings=[]; allcoefs=[]; summaries=[]
    for lag in LAGS:
        X=clean_csv(qdir/f'QVAR_lag{lag}_X.csv',parse_dates=['Date'])
        Y=clean_csv(qdir/f'QVAR_lag{lag}_Y.csv',parse_dates=['Date'])
        if len(X)!=len(Y): raise ValueError(f'QVAR lag {lag}: X/Y row counts differ')
        predictions={}
        for tau in TAUS:
            cf=clean_csv(qdir/f'QVAR_lag{lag}_tau{tau:.2f}_coefficient_matrix.csv',index_col=0)
            # preserve coefficient names; rows are equations, columns are intercept/lagged variables
            if list(cf.index)!=VARS: raise ValueError(f'Unexpected QVAR equation order at lag {lag}, tau {tau}: {list(cf.index)}')
            xcols=['const']+[f'{v}_L{ell}' for ell in range(1,lag+1) for v in VARS]
            if not set(xcols).issubset(X.columns) or not set(xcols).issubset(cf.columns):
                raise ValueError(f'QVAR lag {lag} tau {tau}: missing regressors in X or coefficient matrix')
            Xv=X[xcols].to_numpy(float)
            B=cf[xcols].to_numpy(float)
            pred=Xv @ B.T
            predictions[tau]=pd.DataFrame(pred,index=pd.to_datetime(X['Date']),columns=VARS)
            # companion matrix for the lag polynomial at each quantile
            A=[]
            for ell in range(1,lag+1):
                mat=np.zeros((len(VARS),len(VARS)))
                for i,eq in enumerate(VARS):
                    for j,var in enumerate(VARS): mat[i,j]=float(cf.loc[eq,f'{var}_L{ell}'])
                A.append(mat)
            if lag==1: companion=A[0]
            else: companion=np.block([[A[0],A[1]],[np.eye(len(VARS)),np.zeros((len(VARS),len(VARS)))]])
            rho=float(np.max(np.abs(np.linalg.eigvals(companion))))
            metrics.append({'Lag':lag,'Quantile':tau,'Observations':len(Y),'Companion_spectral_radius':rho})
            for eq in VARS:
                for reg in cf.columns:
                    allcoefs.append({'Lag':lag,'Quantile':tau,'Equation':eq,'Regressor':reg,'Coefficient':float(cf.loc[eq,reg])})
        for var in VARS:
            q10=predictions[.10][var]; q50=predictions[.50][var]; q90=predictions[.90][var]
            c10=int((q10>q50).sum()); c50=int((q50>q90).sum()); anyc=int(((q10>q50)|(q50>q90)).sum())
            crossings.append({'Lag':lag,'Variable':var,'N':len(q10),'Q10_above_Q50':c10,'Q50_above_Q90':c50,'Any_crossing':anyc,'Any_crossing_pct':100.0*anyc/len(q10)})
        # Parse coefficient-level p-values from the package's formatted summary (4-decimal output).
        txt=(qdir/f'QVAR_lag{lag}_summary.txt').read_text(encoding='utf-8',errors='replace')
        pvals=[]
        for block in re.split(r'Equation:\s+',txt)[1:]:
            for line in block.splitlines():
                if re.match(r'^\s*const\s',line): continue
                m=re.match(r'^\s*[A-Za-z0-9_]+_L\d+\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+([0-9.]+)',line)
                if m: pvals.append(float(m.group(1)))
        expected=5*5*lag*3
        if len(pvals)!=expected:
            raise ValueError(f'QVAR lag {lag}: parsed {len(pvals)} slope p-values; expected {expected}')
        summaries.append({'Lag':lag,'Slope_coefficient_tests':len(pvals),'Nominal_p_below_0_05':sum(x<.05 for x in pvals),'Nominal_p_below_0_01':sum(x<.01 for x in pvals),'Interpretation':'Individual model-based coefficient tests; not omnibus Granger tests'})
    qmetrics=pd.DataFrame(metrics); qcross=pd.DataFrame(crossings); qsummary=pd.DataFrame(summaries); qcoef=pd.DataFrame(allcoefs)
    qmetrics.to_csv(table_dir/'Table9_QVAR_stability.csv',index=False,float_format='%.8f')
    qcross.to_csv(table_dir/'Table10_QVAR_quantile_crossings.csv',index=False,float_format='%.8f')
    qsummary.to_csv(table_dir/'Table11_QVAR_inference_summary.csv',index=False)
    qcoef.to_csv(table_dir/'QVAR_coefficients_tidy.csv',index=False,float_format='%.8f')
    return qmetrics,qcross,qsummary,qcoef

def build_tables(results:Path, price_file:Path, return_file:Path, out:Path):
    table_dir=out/'tables'; table_dir.mkdir(parents=True,exist_ok=True)
    prices=clean_csv(price_file,parse_dates=['Date']).set_index('Date')
    returns=clean_csv(return_file,parse_dates=['Date']).set_index('Date')
    if list(prices.columns)!=VARS or list(returns.columns)!=VARS: raise ValueError('Input data columns/order do not match documented five-variable panel')
    calc=np.log(prices).diff().dropna()
    err=float(np.max(np.abs(calc.values-returns.values)))
    if err>2e-10: raise ValueError(f'Price/return integrity check failed: {err}')
    r_pct=returns*100.0
    # Table 1: descriptive moments, reported in percent.
    d=r_pct.describe().T
    d['Skewness']=r_pct.skew(); d['Excess_Kurtosis']=r_pct.kurtosis()
    d['Min_pct']=r_pct.min(); d['Max_pct']=r_pct.max()
    d=d[['mean','std','Skewness','Excess_Kurtosis','Min_pct','Max_pct']]
    d.columns=['Mean_pct','SD_pct','Skewness','Excess_Kurtosis','Min_pct','Max_pct']
    d.to_csv(table_dir/'Table1_descriptive_statistics.csv',float_format='%.8f')
    # Additional descriptive matrix.
    r_pct.corr().to_csv(table_dir/'Table2_unconditional_correlations.csv',float_format='%.8f')
    # Unit-root diagnostics.
    ur=clean_csv(results/'HybridMetrics'/'hybridmetrics_unit_root_battery.csv')
    if 'pvalue' not in ur.columns: raise ValueError('HybridMetrics result lacks pvalue column')
    ur['pvalue_report']=ur['pvalue'].apply(lambda x:'<0.001' if pd.notna(x) and x<.001 else ('≥0.10 (upper bound)' if pd.notna(x) and x>=.1 else f'{x:.3f}'))
    ur.to_csv(table_dir/'Table3_unit_root_battery.csv',index=False,float_format='%.8f')
    # DSCC fit + pairwise correlation summaries.
    fit=parse_model_fit(results); fit.to_csv(table_dir/'Table4_DSCC_model_fit.csv',index=False,float_format='%.6f')
    corr_rows=[]
    for dyn in ['garch','egarch']:
        c=clean_csv(results/'DSCC'/'tables'/f'DSCC_{dyn}_conditional_correlations.csv')
        for pair,g in c.groupby(['Asset_i','Asset_j']):
            v=g['Correlation'].dropna()
            corr_rows.append({'Dynamics':dyn.upper(),'Asset_i':pair[0],'Asset_j':pair[1],'N':len(v),'Mean':v.mean(),'SD':v.std(),'Median':v.median(),'Min':v.min(),'Max':v.max()})
    corr=pd.DataFrame(corr_rows); corr.to_csv(table_dir/'Table5_DSCC_conditional_correlation_summary.csv',index=False,float_format='%.6f')
    # Rolling portfolio summaries and pairwise tests.
    perfs=[]; turns=[]; pairs=[]
    for window in WINDOWS:
        wd=results/'DSCC'/f'rolling_backtest_window_{window}'
        perf=pd.read_csv(wd/'performance_table.csv'); turnover=pd.read_csv(wd/'turnover_table.csv'); pair=pd.read_csv(wd/'pairwise.csv')
        if not {'AV','SD','IR'}.issubset(perf.columns): raise ValueError(f'Unexpected performance schema at {window}')
        for _,row in perf.iterrows(): perfs.append({'Window_days':window,'Strategy':str(row.iloc[0]),'Annualized_return_pct':row['AV'],'Annualized_volatility_pct':row['SD'],'AV_SD_ratio':row['IR']})
        for _,row in turnover.iterrows(): turns.append({'Window_days':window,'Strategy':str(row.iloc[0]),'Turnover':row['TO'],'Gross_leverage':row['GL'],'Short_position_share':row['PL']})
        pair['Holm_adjusted_p']=holm_adjust(pair['p-value'].astype(float).to_numpy())
        pair=pair.rename(columns={pair.columns[0]:'Comparison_order'})
        pair['Comparison_order']=pd.to_numeric(pair['Comparison_order'],errors='coerce').astype('Int64')
        pair.insert(0,'Window_days',window); pairs.extend(pair.to_dict('records'))
    perfdf=pd.DataFrame(perfs); turndf=pd.DataFrame(turns); pairdf=pd.DataFrame(pairs)
    perfdf.to_csv(table_dir/'Table6_portfolio_performance.csv',index=False,float_format='%.8f')
    turndf.to_csv(table_dir/'Table7_portfolio_turnover.csv',index=False,float_format='%.8f')
    pairdf.to_csv(table_dir/'Table8_pairwise_HAC_tests.csv',index=False,float_format='%.8f')
    pairdf.groupby('Window_days').agg(N_comparisons=('Holm_adjusted_p','count'),Min_raw_p=('p-value','min'),Min_Holm_p=('Holm_adjusted_p','min'),Survive_Holm_05=('Holm_adjusted_p',lambda x:int((x<.05).sum()))).reset_index().to_csv(table_dir/'DSCC_pairwise_multiplicity_summary.csv',index=False,float_format='%.8f')
    qmetrics,qcross,qsummary,qcoef=build_qvar(results,out/'tables')
    return {'prices':prices,'returns':returns,'returns_pct':r_pct,'max_return_reconstruction_error':err,'fit':fit,'corr':corr,'performance':perfdf,'turnover':turndf,'pairwise':pairdf,'qvar_metrics':qmetrics,'qvar_crossings':qcross,'qvar_summary':qsummary,'qvar_coefficients':qcoef}

def build_figures(results:Path, dat:dict, out:Path):
    figdir=out/'figures';figdir.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':10,'axes.labelsize':9,'savefig.dpi':300})
    # Figure 1: six conditional-correlation paths.
    corr_file=results/'DSCC'/'tables'/'DSCC_egarch_conditional_correlations.csv'
    c=clean_csv(corr_file,parse_dates=['Date'])
    pairs=[('Nasdaq100_ETF','Bitcoin'),('Nasdaq100_ETF','Clean_Energy_ETF'),('Nasdaq100_ETF','Oil_Linked_ETF'),('Bitcoin','Clean_Energy_ETF'),('Bitcoin','Oil_Linked_ETF'),('Clean_Energy_ETF','Oil_Linked_ETF')]
    fig,axs=plt.subplots(2,3,figsize=(14,7.3),sharex=True)
    for ax,(a,b) in zip(axs.flat,pairs):
        g=c[(c.Asset_i==a)&(c.Asset_j==b)]
        if g.empty:g=c[(c.Asset_i==b)&(c.Asset_j==a)]
        if g.empty: raise ValueError(f'Missing correlation path for {a}/{b}')
        ax.plot(g.Date,g.Correlation,lw=.8); ax.axhline(0,color='black',lw=.6,alpha=.5)
        ax.set_title(f'{a.replace("_ETF", "")} – {b.replace("_ETF", "")}'); ax.set_ylim(-1,1); ax.grid(alpha=.2); ax.tick_params(axis='x',rotation=25)
    fig.suptitle('DSCC–EGARCH conditional correlations (four traded-asset proxies)',fontsize=14,fontweight='bold',y=1.01)
    fig.tight_layout(); fig.savefig(figdir/'Figure1_DSCC_EGARCH_Conditional_Correlations.png',bbox_inches='tight');fig.savefig(figdir/'Figure1_DSCC_EGARCH_Conditional_Correlations.pdf',bbox_inches='tight');plt.close(fig)
    # Figure 2: annualized average-return/volatility ratios (AV/SD), not active information ratios.
    perf=dat['performance']; models=['1/N','Sample','DCC','DSCC-garch','DSCC-egarch-av']
    fig,ax=plt.subplots(figsize=(10,5.6));x=np.arange(len(models));width=.35
    for j,w in enumerate(WINDOWS):
        vals=perf[perf.Window_days==w].set_index('Strategy').reindex(models)['AV_SD_ratio'].values
        ax.bar(x+(j-.5)*width,vals,width,label=f'Window = {w} days')
    ax.set_xticks(x);ax.set_xticklabels(['1/N','Sample covariance','DCC','DSCC-GARCH','DSCC-EGARCH-av'],rotation=12,ha='right')
    ax.set_ylabel('Annualised average return / volatility (AV/SD)');ax.set_title('Rolling minimum-variance portfolio performance');ax.legend(frameon=False);ax.grid(axis='y',alpha=.25)
    fig.tight_layout();fig.savefig(figdir/'Figure2_Portfolio_AV_SD_Ratios.png',bbox_inches='tight');fig.savefig(figdir/'Figure2_Portfolio_AV_SD_Ratios.pdf',bbox_inches='tight');plt.close(fig)
    # Figure 3: QVAR(1) coefficients.
    qdir=results/'QVAR'/'tables'; fig,axs=plt.subplots(1,3,figsize=(15,5.4))
    for ax,tau in zip(axs,TAUS):
        cf=clean_csv(qdir/f'QVAR_lag1_tau{tau:.2f}_coefficient_matrix.csv',index_col=0)
        mat=cf[[f'{v}_L1' for v in VARS]].values;lim=max(float(np.nanmax(np.abs(mat))),1e-8)
        im=ax.imshow(mat,cmap='RdBu_r',vmin=-lim,vmax=lim,aspect='auto')
        ax.set_xticks(range(5));ax.set_xticklabels(['QQQ','BTC','ICLN','USO','VIX'],rotation=35,ha='right');ax.set_yticks(range(5));ax.set_yticklabels(['QQQ','BTC','ICLN','USO','VIX'])
        ax.set_title(f'τ = {tau:.2f}');ax.set_xlabel('Lagged regressor')
        for i in range(5):
            for j in range(5):ax.text(j,i,f'{mat[i,j]:.2f}',ha='center',va='center',fontsize=7,color='black')
        fig.colorbar(im,ax=ax,fraction=.046,pad=.04)
    axs[0].set_ylabel('Dependent equation');fig.suptitle('Reduced-form QVAR(1): lag-one slope coefficients',fontsize=14,fontweight='bold')
    fig.tight_layout();fig.savefig(figdir/'Figure3_QVAR_Coefficient_Heatmaps.png',bbox_inches='tight');fig.savefig(figdir/'Figure3_QVAR_Coefficient_Heatmaps.pdf',bbox_inches='tight');plt.close(fig)
    # Figure 4: stability and crossings.
    fig,axs=plt.subplots(1,2,figsize=(11,4.8))
    for tau,g in dat['qvar_metrics'].groupby('Quantile'):axs[0].plot(g.Lag,g.Companion_spectral_radius,marker='o',label=f'τ={tau:.1f}')
    axs[0].axhline(1,color='red',ls='--',lw=1,label='Unit boundary');axs[0].set_xlabel('QVAR lag order');axs[0].set_ylabel('Companion spectral radius');axs[0].set_title('Reduced-form stability diagnostic');axs[0].legend(frameon=False);axs[0].grid(alpha=.2)
    lag2=dat['qvar_crossings'][dat['qvar_crossings'].Lag==2]
    axs[1].bar(lag2.Variable,lag2.Any_crossing_pct);axs[1].set_ylabel('Target-date predictions with any crossing (%)');axs[1].set_title('QVAR(2) quantile crossings');axs[1].tick_params(axis='x',rotation=35);axs[1].grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(figdir/'Figure4_QVAR_Stability_and_Crossings.png',bbox_inches='tight');fig.savefig(figdir/'Figure4_QVAR_Stability_and_Crossings.pdf',bbox_inches='tight');plt.close(fig)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--results-dir',required=True,help='Core results directory with DSCC, QVAR, and HybridMetrics subfolders')
    p.add_argument('--price-file',required=True,help='Frozen or licensed price CSV with Date plus the five variables')
    p.add_argument('--return-file',required=True,help='Decimal log-return CSV with Date plus the five variables')
    p.add_argument('--outdir',default='publication_output')
    args=p.parse_args()
    results=Path(args.results_dir);out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    dat=build_tables(results,Path(args.price_file),Path(args.return_file),out)
    build_figures(results,dat,out)
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                h.update(block)
        return h.hexdigest()
    generated = sorted(list((out/'tables').glob('*.csv')) + list((out/'figures').glob('*.png')) + list((out/'figures').glob('*.pdf')))
    manifest={
        'build_timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'python': platform.python_version(),
        'result_dir':str(results.resolve()),
        'price_file':str(Path(args.price_file).resolve()),
        'return_file':str(Path(args.return_file).resolve()),
        'price_rows':len(dat['prices']),'return_rows':len(dat['returns']),
        'price_start':str(dat['prices'].index.min().date()),'price_end':str(dat['prices'].index.max().date()),
        'return_start':str(dat['returns'].index.min().date()),'return_end':str(dat['returns'].index.max().date()),
        'max_return_reconstruction_error_decimal':dat['max_return_reconstruction_error'],
        'portfolio_ratio_definition':'AV_SD_ratio = annualized average return / annualized standard deviation; not benchmark-relative information ratio',
        'generated_assets':[{'path':str(x.relative_to(out)),'bytes':x.stat().st_size,'sha256':_sha256(x)} for x in generated],
        'generated_tables':sorted(x.name for x in (out/'tables').glob('*.csv')),
        'generated_figures':sorted(x.name for x in (out/'figures').glob('*.png')),
        'reproduction_scope':'publication tables and figures rebuilt from supplied archived model outputs; original estimation driver is absent'
    }
    (out/'publication_build_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
