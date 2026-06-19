# configs/

Configuration files and environment variables.

- `.env.example` — template for required environment variables (API keys). Copy to `.env` and fill in real values; `.env` is already in `.gitignore` and must never be committed.
- A `config.yaml` can be added here for fixed parameters (e.g. train/validate/test date ranges, list of correlated FX pairs, default hyperparameter grid) as needed.
