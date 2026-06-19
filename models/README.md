# models/

- `trained/` — trained models, saved as `.joblib`/`.pkl`. Naming convention: `<dataset_variant>_<model_name>.joblib` (e.g. `dataset3_xgboost.joblib`).
- `search_results/` — Bayesian hyperparameter search logs/results per fold (CSV/JSON), used to compare candidates before picking the final model.

Model files can be large — if they exceed git limits, consider Git LFS or only committing the best model per dataset variant.
