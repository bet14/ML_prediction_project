# notebooks/

Exploratory notebooks, EDA, quick experiments — not production code (that belongs in `src/`).

Naming convention: number by stage, e.g.:
- `01_eda_raw_data.ipynb`
- `02_feature_engineering.ipynb`
- `03_model_baseline.ipynb`
- `04_hyperparameter_search.ipynb`
- `05_evaluation_backtest.ipynb`

Once a piece of notebook code is stable and needs reuse, move it into a function/module in the matching `src/` subfolder.
