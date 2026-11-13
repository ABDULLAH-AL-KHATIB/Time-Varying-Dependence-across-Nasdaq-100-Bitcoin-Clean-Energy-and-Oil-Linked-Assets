# Public GitHub / Zenodo release checklist

- [ ] Replace the `YOUR_GITHUB_USERNAME` placeholder in `CITATION.cff` and notebook configuration.
- [ ] Confirm that the author has the right to release all project-authored code under the proposed MIT licence; do not apply it to third-party packages.
- [ ] Keep all third-party dependencies installed from their own package/repository sources and preserve their separate licences.
- [ ] Verify the original market-data provider, exact price/index field, timezone, timestamp convention and redistribution licence.
- [ ] Do not upload frozen input data or daily/dated outputs unless their redistribution rights are documented.
- [ ] Run the Colab notebook from a clean network-enabled runtime with the licensed input files; review convergence, warnings, test completeness and every generated table/figure.
- [ ] Compare the clean-run outputs with the archived results; the historical executed driver is absent, so exact source-level reproduction is not established.
- [ ] Confirm author identity, affiliation, title, version, release date, keywords and metadata in `CITATION.cff` and `.zenodo.json`.
- [ ] Create a GitHub release and only then activate Zenodo archiving / mint the DOI.
- [ ] Replace placeholder URL/DOI fields in the manuscript only after the live records exist.
