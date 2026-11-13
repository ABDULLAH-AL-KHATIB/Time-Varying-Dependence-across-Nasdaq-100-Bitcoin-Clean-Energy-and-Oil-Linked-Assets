# IRFA DSCC–QVAR replication code

This repository contains the core Python source and Google Colab notebook for the study of time-varying dependence among QQQ, BTC-USD, ICLN, USO and VIX. Included analyses are limited to DSCC-λ-GARCH/EGARCH estimation and rolling minimum-variance evaluation, five-variable reduced-form QVAR(1)/(2) at τ = 0.10/0.50/0.90, and ADF/PP/KPSS unit-root diagnostics. No supplementary optional model families are included.

## Data required

Create `data/` and place two lawfully obtained CSV files inside it:

- `price_panel.csv`: `Date` plus the five price/index columns in `metadata/DATA_SCHEMA.csv`.
- `returns_decimal.csv`: matching dates and decimal log returns computed as `ln(P_t) - ln(P_{t-1})`.

The script validates date alignment and reconstructs returns from prices. The original executed model driver is not available; `replicate_irfa.py` is a reconstructed implementation and needs a clean-environment run before its outputs can be claimed to exactly reproduce the archived historical estimates. It multiplies decimal returns by 100 before model estimation. The archived portfolio inference contains six one-sided contrasts per window, not all ten possible pairs among the five strategies; the original contrast pre-specification is unavailable. Document the data provider, field (`Close`, `Adj Close`, or another licensed field), currency, timezone, download timestamp and licence. Do not assume the legacy historical filename proves an adjusted-close convention.

**Do not upload the frozen inputs or date-level results to this public repository until the original data provider, field and redistribution rights are verified.** Earlier project notes describe Yahoo Finance as the source, whose help page prohibits redistribution of Yahoo-supplied information. The run manifest does not independently record the provider, so this attribution remains to be confirmed. The complete generated result archive is retained separately in the private author package.

## Install and run locally

```bash
python -m pip install -r code/requirements.txt
python code/install_core_repositories.py
python code/replicate_irfa.py --data-dir ./data --outdir ./replication_output
```

The run is designed to write DSCC estimates, covariance/correlation paths, rolling backtest outputs, QVAR coefficient summaries and diagnostics, HybridMetrics stationarity results, publication tables/figures and a run manifest. No empirical output from the historical run is included in this public code-only staging tree. To rebuild tables and figures from an existing core result directory:

```bash
python code/build_publication_assets.py \
  --results-dir ./replication_output \
  --price-file ./data/price_panel.csv \
  --return-file ./data/returns_decimal.csv \
  --outdir ./publication_output
```

## Google Colab

Open `code/IRFA_DSCC_QVAR_Colab.ipynb` in Google Colab. The notebook clones this repository when its URL is configured, asks you to upload the two licensed input files when they are not present, installs the pinned repositories and runs the core pipeline. It creates a ZIP of the resulting output. No GitHub or Zenodo credentials are embedded in the notebook.

## Methods and versions

- DSCC `0.1.1` (MIT); GARCH and EGARCH eigenvalue dynamics; 10 starts; seed `20261113`; 756- and 1,008-day rolling windows; 21-day forecast horizon.
- QVAR source pinned to commit `926f660c501eb1d2a1b29e2dc4ab15705cc8a87b`; non-recursive reduced-form QVAR(1)/(2); five endogenous variables; τ = 0.10, 0.50 and 0.90.
- HybridMetrics source pinned to commit `2fc7e314619d3d439cdd38c20f9fc32ebb59533c`; ADF/PP/KPSS diagnostic battery.

The QVAR output in the historical run reports individual model-based slope p-values, not multiplicity-adjusted joint quantile-Granger tests or structural impulse responses. Do not interpret them as formal causal discoveries. The requirements pin `arch==9.0.0` because HybridMetrics documents that its Phillips-Perron routine requires the `arch` package. A new run fails fast if the dependency is unavailable. The historical archive does not record the exact `arch` version.

## Historical-run reproducibility limitation

The original executed `run_pipeline.py` is not present in the supplied historical output archive; only its SHA-256 is recorded. The enclosed driver is a reconstructed implementation. It must be run in the pinned environment and compared with the archived generated results before claiming exact source-level reproduction. The archived data file hashes also do not match the historical manifest hashes, despite numeric log-return reconstruction to `9.80e-12`.

## Licence and citation

The MIT licence applies to the original code in this repository only. It does not relicense third-party repositories, market data, or generated data derived from third-party sources. Cite the repository using `CITATION.cff`; insert the actual GitHub URL and Zenodo DOI after creating the live records.

Before publication, confirm ownership/licensing of the project-authored code. The MIT licence in this repository applies only to that project-authored code and does not relicense DSCC, QVAR, HybridMetrics or any market data.
