#!/usr/bin/env python3
"""Core replication pipeline for the IRFA DSCC + reduced-form QVAR paper.

This script deliberately excludes optional NPCQ, TVNCQ and DeepTVAR analyses.
It uses the frozen input data distributed in data/raw and the pinned core
packages/repositories. Outputs are written to replication_output/.

Run from the repository root:
    python 05_Code/replicate_irfa.py --data-dir 03_Data/raw --outdir replication_output

The original executed driver was not present in the uploaded output archive.
This driver reconstructs the core analysis from the package APIs and recorded
settings; exact numerical identity with the archived outputs must be verified
in the pinned Colab environment before claiming exact source-level replication.
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, subprocess, sys, time, inspect
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
DSCC_SEED=20261113
N_STARTS=10
WINDOWS=[756,1008]
HORIZON=21


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def git_commit(path:Path)->str|None:
    try:
        return subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    except Exception:return None


def load_frozen(data_dir:Path):
    price_path = data_dir/'price_panel.csv' if (data_dir/'price_panel.csv').exists() else data_dir/'verified_adjusted_close_prices.csv'
    return_path = data_dir/'returns_decimal.csv' if (data_dir/'returns_decimal.csv').exists() else data_dir/'verified_log_returns.csv'
    prices=pd.read_csv(price_path,parse_dates=['Date']).set_index('Date')
    returns=pd.read_csv(return_path,parse_dates=['Date']).set_index('Date')
    if list(prices.columns)!=VARS or list(returns.columns)!=VARS:
        raise ValueError(f'Expected columns {VARS}; found {list(returns.columns)}')
    calc=np.log(prices).diff().dropna()
    diff=float(np.max(np.abs(calc.values-returns.values)))
    if not calc.index.equals(returns.index) or prices.isna().any().any() or returns.isna().any().any() or diff>2e-10:
        raise ValueError(f'Data integrity check failed; max return difference={diff}')
    return prices,returns,diff


def export_dscc(returns_pct:pd.DataFrame,out:Path):
    import dscc
    (out/'DSCC/tables').mkdir(parents=True,exist_ok=True)
    (out/'DSCC/figures').mkdir(parents=True,exist_ok=True)
    fitted={}
    for dyn in ['garch','egarch']:
        model=dscc.DSCC(returns_pct[ASSETS],dynamics=dyn)
        res=model.fit(n_starts=N_STARTS,seed=DSCC_SEED)
        fitted[dyn]=res
        (out/f'DSCC/DSCC_{dyn}_summary.txt').write_text(res.summary(),encoding='utf-8')
        res.to_frame().to_csv(out/f'DSCC/tables/DSCC_{dyn}_parameters.csv')
        sigma=np.asarray(res.sigma())
        corr=np.asarray(res.correlation())
        dates=returns_pct.index
        var_rows=[];corr_rows=[]
        for ti,date in enumerate(dates):
            for i,a in enumerate(ASSETS):
                var_rows.append({'Date':date,'Dynamics':dyn.upper(),'Asset':a,'Conditional_Variance':sigma[ti,i,i]})
            for i in range(len(ASSETS)):
                for j in range(i+1,len(ASSETS)):
                    corr_rows.append({'Date':date,'Dynamics':dyn.upper(),'Asset_i':ASSETS[i],'Asset_j':ASSETS[j],'Correlation':corr[ti,i,j]})
        pd.DataFrame(var_rows).to_csv(out/f'DSCC/tables/DSCC_{dyn}_conditional_variances.csv',index=False)
        pd.DataFrame(corr_rows).to_csv(out/f'DSCC/tables/DSCC_{dyn}_conditional_correlations.csv',index=False)
        fig=res.plot_correlations();fig.savefig(out/f'DSCC/figures/DSCC_{dyn}_correlations.png',dpi=300,bbox_inches='tight');plt.close(fig)
        fig=res.plot_eigenvalues();fig.savefig(out/f'DSCC/figures/DSCC_{dyn}_eigenvalues.png',dpi=300,bbox_inches='tight');plt.close(fig)
        init='last' if dyn=='garch' else 'average'
        fc=res.forecast(H=HORIZON,init=init)
        np.save(out/f'DSCC/tables/DSCC_{dyn}_forecast_sigma.npy',np.asarray(fc.sigma))
        np.save(out/f'DSCC/tables/DSCC_{dyn}_forecast_correlation.npy',np.asarray(fc.correlation))
        pd.DataFrame(np.asarray(fc.mean_sigma),index=ASSETS,columns=ASSETS).to_csv(out/f'DSCC/tables/DSCC_{dyn}_forecast_mean_sigma.csv')
    forecasters=[dscc.EqualWeight(),dscc.SampleCovForecaster(),dscc.DCCForecaster(),dscc.DSCCForecaster('garch',init='last'),dscc.DSCCForecaster('egarch',init='average')]
    bt_meta=[]
    for window in WINDOWS:
        bt=dscc.rolling_backtest(returns_pct[ASSETS],forecasters,window=window,horizon=HORIZON,holding='buy_and_hold')
        wdir=out/f'DSCC/rolling_backtest_window_{window}';wdir.mkdir(parents=True,exist_ok=True)
        for name,method in [('performance_table','performance_table'),('pairwise','pairwise'),('turnover_table','turnover_table'),('covariance_table','covariance_table')]:
            getattr(bt,method)().to_csv(wdir/f'{name}.csv')
        fig=dscc.plot_wealth(bt);fig.savefig(wdir/'wealth.png',dpi=300,bbox_inches='tight');plt.close(fig)
        bt_meta.append({'window':window,'horizon':HORIZON,'holding':'buy_and_hold','type':type(bt).__name__})
    (out/'DSCC/dscc_backtest_manifest.json').write_text(json.dumps(bt_meta,indent=2))
    return fitted


def export_qvar(returns_pct:pd.DataFrame,out:Path):
    from qvar import QuantileVAR
    from qvar.tables import format_qvar_summary
    qdir=out/'QVAR/tables';qdir.mkdir(parents=True,exist_ok=True)
    for lag in LAGS:
        model=QuantileVAR(lags=lag,recursive=False)
        result=model.fit(returns_pct[VARS],taus=TAUS)
        (qdir/f'QVAR_lag{lag}_summary.txt').write_text(format_qvar_summary(result),encoding='utf-8')
        # Library result attributes are exported with an explicit tidy schema.
        coefs=getattr(result,'coefficients',None);ses=getattr(result,'std_errors',None);pvals=getattr(result,'pvalues',None)
        if coefs is None: raise RuntimeError('QVAR results object has no coefficients attribute; inspect pinned package API.')
        rows=[]
        x_names=['const']+[f'{v}_L{ell}' for ell in range(1,lag+1) for v in VARS]
        # Store the exact lag-aligned design and dependent-variable panels used for crossing diagnostics.
        x_rows=[]; y_rows=[]
        for t in range(lag, len(returns_pct)):
            xr={'Date':returns_pct.index[t],'const':1.0}
            for ell in range(1,lag+1):
                for v in VARS: xr[f'{v}_L{ell}']=float(returns_pct.iloc[t-ell][v])
            yr={'Date':returns_pct.index[t]}
            for v in VARS: yr[v]=float(returns_pct.iloc[t][v])
            x_rows.append(xr); y_rows.append(yr)
        pd.DataFrame(x_rows).to_csv(qdir/f'QVAR_lag{lag}_X.csv',index=False)
        pd.DataFrame(y_rows).to_csv(qdir/f'QVAR_lag{lag}_Y.csv',index=False)
        for tau in TAUS:
            matrix_rows=[]
            for eq,arr0 in coefs[tau].items():
                arr=np.asarray(arr0).ravel()
                se=np.asarray(ses[tau][eq]).ravel() if ses is not None else np.full_like(arr,np.nan)
                pv=np.asarray(pvals[tau][eq]).ravel() if pvals is not None else np.full_like(arr,np.nan)
                matrix_rows.append([float(x) for x in arr])
                for nm,b,s,pv0 in zip(x_names,arr,se,pv):
                    rows.append({'Lag':lag,'Quantile':tau,'Equation':eq,'Regressor':nm,'Coefficient':float(b),'StdError':float(s),'PValue':float(pv0)})
            pd.DataFrame(matrix_rows,index=list(coefs[tau].keys()),columns=x_names).to_csv(qdir/f'QVAR_lag{lag}_tau{tau:.2f}_coefficient_matrix.csv')
        pd.DataFrame(rows).to_csv(qdir/f'QVAR_lag{lag}_coefficients.csv',index=False)
        (qdir/f'QVAR_lag{lag}_public_attributes.json').write_text(json.dumps({'lags':lag,'taus':TAUS,'recursive':False,'n_obs':int(len(returns_pct)-lag),'n_vars':len(VARS)},indent=2))
    (out/'QVAR/qvar_manifest.json').write_text(json.dumps({'lags':LAGS,'taus':TAUS,'recursive':False,'interpretation':'Reduced-form QVAR; no structural identification.'},indent=2))


def export_hybridmetrics(returns_pct:pd.DataFrame,out:Path):
    # HybridMetrics documents that its Phillips-Perron test requires `arch`.
    # Fail explicitly instead of silently exporting an incomplete unit-root battery.
    try:
        import arch  # noqa: F401
    except ImportError as exc:
        raise RuntimeError('The complete ADF/PP/KPSS battery requires arch; install requirements.txt first.') from exc
    from hybridmetrics import run_unit_root_battery
    hdir=out/'HybridMetrics';hdir.mkdir(parents=True,exist_ok=True)
    df=run_unit_root_battery(returns_pct[VARS],alpha=.05)
    if df.empty:
        raise RuntimeError('HybridMetrics returned an empty unit-root battery.')
    if df.astype(str).apply(lambda c: c.str.contains(r'error|unavailable|not installed',case=False,regex=True,na=False)).any().any():
        raise RuntimeError('HybridMetrics returned an error/unavailable test result; inspect the unit-root battery before using it.')
    df.to_csv(hdir/'hybridmetrics_unit_root_battery.csv')
    (hdir/'hybridmetrics_manifest.json').write_text(json.dumps({'unit_root_battery':True,'deep_tvar':False,'input':'percentage log returns'},indent=2))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data-dir',default='03_Data/raw')
    p.add_argument('--outdir',default='replication_output')
    args=p.parse_args()
    data_dir=Path(args.data_dir);out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    prices,returns,diff=load_frozen(data_dir)
    returns_pct=returns*100.0
    # Save the canonical working panels used by the estimators.
    prices.to_csv(out/'price_panel.csv',index_label='Date')
    returns.to_csv(out/'returns_decimal.csv',index_label='Date')
    returns_pct.to_csv(out/'returns_percentage_points.csv',index_label='Date')
    desc=returns_pct.describe().T
    desc['skewness']=returns_pct.skew();desc['excess_kurtosis']=returns_pct.kurtosis()
    desc.to_csv(out/'descriptive_statistics.csv')
    export_dscc(returns_pct,out)
    export_qvar(returns_pct,out)
    export_hybridmetrics(returns_pct,out)
    # Rebuild publication tables and figures directly from the generated model outputs.
    builder=Path(__file__).with_name('build_publication_assets.py')
    subprocess.check_call([sys.executable,str(builder),'--results-dir',str(out),'--price-file',str(out/'price_panel.csv'),'--return-file',str(out/'returns_decimal.csv'),'--outdir',str(out/'publication_output')])
    import importlib.metadata as md
    pkg={}
    for x in ['dscc','qvar-model','hybridmetrics','numpy','pandas','scipy','statsmodels','arch']:
        try:pkg[x]=md.version(x)
        except Exception:pkg[x]='unknown'
    repo_root=Path(__file__).resolve().parents[1]
    repositories={name:{'path':str(repo_root/'vendor'/folder),'commit':git_commit(repo_root/'vendor'/folder)} for name,folder in [('QVAR','QVAR'),('HybridMetrics','hybridmetrics')]}
    run={'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'python':platform.python_version(),'packages':pkg,'repositories':repositories,'data':{'prices_n':len(prices),'returns_n':len(returns),'price_start':str(prices.index.min().date()),'price_end':str(prices.index.max().date()),'return_start':str(returns.index.min().date()),'return_end':str(returns.index.max().date()),'price_sha256':sha256(data_dir/('price_panel.csv' if (data_dir/'price_panel.csv').exists() else 'verified_adjusted_close_prices.csv')),'return_sha256':sha256(data_dir/('returns_decimal.csv' if (data_dir/'returns_decimal.csv').exists() else 'verified_log_returns.csv')),'max_recomputed_return_difference':diff,'price_field_status':'not independently verifiable from the historical archive: filename indicates adjusted close but acquisition arguments are absent','data_provider':'not independently recorded in the historical run manifest; author must verify before publication or redistribution'},'source_sha256':{'replicate_irfa.py':sha256(Path(__file__)),'build_publication_assets.py':sha256(Path(__file__).with_name('build_publication_assets.py'))},'settings':{'dscc_dynamics':['garch','egarch'],'dscc_n_starts':N_STARTS,'dscc_seed':DSCC_SEED,'backtest_windows':WINDOWS,'horizon':HORIZON,'qvar_lags':LAGS,'qvar_taus':TAUS,'qvar_recursive':False,'core_analyses_only':True}}
    (out/'run_manifest.json').write_text(json.dumps(run,indent=2))
    print(json.dumps(run,indent=2))

if __name__=='__main__':main()
