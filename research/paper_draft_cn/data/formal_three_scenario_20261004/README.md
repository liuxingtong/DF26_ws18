# Formal comparison data for the paper draft

This tracked snapshot contains the summary and Pareto CSV files used by `../../figures/make_formal_figures.py` and the paper manuscript. It comes from `05_Shanghai Power to Form Students/out/dapuqiao/method_comparison/formal_three_scenario_20261004`.

The full local experiment output also contains candidate records, building changes, geometry exports, source files, and code snapshots. The tracked snapshot keeps the paper figures reproducible without adding that larger output to Git. `experiment_manifest.json` records the four methods, five seeds, shared constraints, normalization, and input mode. `fairness_audit.csv` records 400 effective independent evaluations and 401 candidates including the current city in every one of the 20 runs.

Figures can be regenerated from the repository root with `.venv/bin/python research/paper_draft_cn/figures/make_formal_figures.py` after installing Pillow. The preview figure is retained for comparison of the original platform run but is not used in the formal results section.
