# Reference verification and citation crosswalk

This record distinguishes peer-reviewed methodological evidence from official product documentation and software citations. Bibliographic identities and DOI targets for the main journal references were checked against publisher or primary-source records. Product details were checked against official issuer/regulator pages as they stood on 13 November 2026. This verification is bibliographic and definitional; it does not imply that every cited article supports every empirical interpretation in the manuscript.

| Manuscript reference | Verified source / DOI | Role and supported use |
|---|---|---|
| Abadir (2023) | https://doi.org/10.1093/ectj/utac023 | Minimal representation of variance matrices; mathematical foundation for spectral volatility/correlation models. |
| Abadir & Rockinger (2026) | https://doi.org/10.1093/ectj/utag017 | DSCC methodology. The published article describes a parameterization spanning admissible correlation matrices and evaluates minimum-variance portfolios with 100, 500 and 1,000 stocks. Its portfolio findings are specific to that larger-universe design and are not generalized to this four-proxy sample. |
| Bouri et al. (2021) | https://doi.org/10.1016/j.irfa.2020.101646 | Cross-asset return connectedness around COVID-19; background for time-varying market connectedness, not a direct replication of this study. |
| Cboe Global Markets (n.d.) | https://www.cboe.com/tradable_products/vix/faqs | Official VIX FAQ: the index reflects expected S&P 500 volatility over the next 30 days, implied by SPX option quotations. |
| Chavleishvili & Manganelli (2024) | https://doi.org/10.1002/jae.3009 | QVAR for forecasting and stress testing. Its distinction between reduced-form quantile systems and additional recursive structure for joint quantile forecasts/structural responses supports the manuscript's non-recursive interpretation. |
| DeMiguel et al. (2009) | https://doi.org/10.1093/rfs/hhm075 | Estimation error and naive 1/N diversification; used as contextual literature, not as a direct benchmark for the five-strategy experiment. |
| Dickey & Fuller (1979) | https://doi.org/10.2307/2286348 | ADF unit-root test. |
| Engle (2002) | https://doi.org/10.1198/073500102288618487 | Dynamic Conditional Correlation methodology. |
| Ferrer et al. (2018) | https://doi.org/10.1016/j.eneco.2018.09.022 | Time- and frequency-varying connectedness between renewable-energy equities and oil; the article reports short-horizon clean-energy/technology co-movement. The present paper does not estimate frequency-specific effects. |
| Holm (1979) | Scandinavian Journal of Statistics, 6(2), 65–70 | Stepwise family-wise error-rate adjustment used in the archived six-contrast families. |
| Invesco (n.d.) | https://www.invesco.com/us/en/financial-products/etfs/invesco-qqq-trust-series-1.html | Official product description: QQQ seeks to track the Nasdaq-100 Index, which includes 100 of the largest domestic and international nonfinancial Nasdaq-listed companies. |
| iShares (n.d.) | https://www.ishares.com/us/products/239738/ishares-global-clean-energy-etf-icln | Official product page: ICLN seeks to track the S&P Global Clean Energy Transition Index (Net). It is an equity ETF, not a direct measure of physical renewable generation. |
| Ji et al. (2019) | https://doi.org/10.1016/j.irfa.2018.12.002 | Dynamic connectedness/integration among cryptocurrencies; contextual background only. |
| Koenker & Bassett (1978) | https://doi.org/10.2307/1913643 | Regression quantiles. |
| Kwiatkowski et al. (1992) | https://doi.org/10.1016/0304-4076(92)90104-Y | KPSS stationarity test. |
| Newey & West (1987) | https://doi.org/10.2307/1913610 | HAC covariance estimator used in the six supplied directional portfolio contrasts. |
| Phillips & Perron (1988) | https://doi.org/10.1093/biomet/75.2.335 | PP unit-root test. |
| Roudane (2026a–c) | https://github.com/merwanroudane/dscc ; https://github.com/merwanroudane/hybridmetrics ; https://github.com/merwanroudane/QVAR | Software used by the archived run; versions and Git commits are recorded in the run manifests. These are software citations, not independent validation of all estimator properties. |
| United States Oil Fund, LP (2026) | https://www.sec.gov/Archives/edgar/data/1327068/000207187626000128/i26211_uso-424b3.htm | SEC-filed prospectus: USO seeks daily NAV changes reflecting the spot price of WTI delivered at Cushing through a specified short-term futures contract, collateral interest and expenses. It is not a spot-price series. |
| Yahoo Finance (n.d.) | https://help.yahoo.com/kb/finance/article-exchanges-data-delays-sln2310.html | Official data-provider help page is cited for a conditional redistribution warning. The historical run manifest does not independently record the provider; this is not proof that Yahoo supplied the archived values. |

## Important boundaries

- The manuscript's claims about QQQ, ICLN, USO and VIX are limited to the instruments/index represented by the tickers; they are not proxies for direct physical energy flows, AI investment, or spot-oil prices.
- The DSCC evidence in Abadir and Rockinger (2026) comes from substantially larger equity universes and a different portfolio experiment. It is contextual methodological evidence, not a like-for-like comparison with the current four-asset results.
- QVAR references support quantile modeling as a method. The supplied archive provides individual model-based coefficient tests, not a multiplicity-adjusted joint quantile-Granger test or identified structural responses.
- Reference formatting can be conformed to the journal's production style at acceptance. At submission, author names, journal title, year, volume, issue, pages/article number and DOI should remain complete and consistent.
