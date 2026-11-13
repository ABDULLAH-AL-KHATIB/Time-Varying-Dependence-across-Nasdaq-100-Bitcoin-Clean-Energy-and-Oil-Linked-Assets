# Software and run provenance

## Archived run

- Timestamp: 2026-11-13T10:27:14Z (from original run manifest).
- Python: 3.13.18 (from the original run manifest).
- DSCC: 0.1.1.
- QVAR (`qvar-model`): 0.1.0; source commit `926f660c501eb1d2a1b29e2dc4ab15705cc8a87b`.
- HybridMetrics: 0.2.1; source commit `2fc7e314619d3d439cdd38c20f9fc32ebb59533c`.
- Core design: DSCC GARCH/EGARCH, 10 starts, seed 20261113; rolling windows 756 and 1,008 trading days; forecast horizon 21; reduced-form non-recursive QVAR lags 1 and 2 at quantiles 0.10, 0.50 and 0.90; HybridMetrics ADF/PP/KPSS.

## Original source and reconstructed replication

The original executed `run_pipeline.py` was not included in the supplied run archive; only its SHA-256 digest is recorded in the original manifest. The supplied generated outputs document a completed run, but the exact source that produced them cannot be recovered from the uploaded archive. The enclosed `replicate_irfa.py` is a reconstructed implementation based on archived outputs, recorded settings and the public package APIs. It is not byte-identical to the missing original source and must not be represented as such. The public release records hashes for its own source files and for inputs used in future runs.

## Price-field metadata

The supplied price file retains the legacy filename `verified_adjusted_close_prices.csv`, but the original manifest does not identify the source provider, downloader arguments, timezone, timestamp convention or whether `Close`, `Adj Close` or an auto-adjusted close field was selected. The filename alone does not establish the field convention. Future runs must record the provider, field, ticker mapping, retrieval timestamp, timezone and applicable data licence.

## Hash verification

The SHA-256 hashes in the original run manifest do not match the exact CSV byte hashes in the uploaded archive. Both the manifest values and actual file hashes are preserved in `07_Audit/RESULTS_PROVENANCE_RECONCILIATION.json`; no explanation is inferred. The numerical price/return relationship was independently checked: the maximum absolute difference between `diff(log(price))` and the supplied decimal log-return file is `9.798634126312322e-12`.


## Reconstructed clean-run dependency note

The Colab requirements additionally pin `arch==9.0.0` for the HybridMetrics Phillips-Perron test, which its upstream documentation states requires the `arch` package. This is an explicit dependency for future reconstructed runs; the historical archive does not record the exact `arch` version.
