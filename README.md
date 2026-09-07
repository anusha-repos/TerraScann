# SatQuery AI — Integrated Project

This folder contains the final React frontend and validated SatQuery FastAPI backend connected through a clean `/api/predict` contract.

## Structure

- `frontend/` — React/Vite application
- `backend/` — FastAPI + AgentRouter + GeoChat task modules

## Important

The backend model/data paths are the validated Kaggle paths in `backend/config.py`. The GeoChat runtime must use the validated Python 3.10 environment.

The frontend does not contain model weights, dataset paths, or API secrets.

For deployment, place both behind an HTTPS reverse proxy. The browser talks to the same-origin `/api/predict`; the proxy forwards requests to FastAPI. Keep FastAPI private and keep `SATQUERY_API_KEY` out of browser-exposed configuration.

## Current integration mapping

The frontend's existing task selector remains the source of task intent:
- Single-image VQA / Captioning / Grounding → `task12`
- Bi-temporal change analysis → `task3`
- Optical + SAR joint analysis → `task4`

Automatic natural-language task detection is intentionally not introduced in this integration snapshot.

## Validation

The backend Python files compile successfully, and the modified frontend JSX files parse successfully. A complete GPU inference test still belongs in the user's validated Kaggle GeoChat environment.
