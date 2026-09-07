# SatQuery AI — Integrated Frontend + Backend

This package connects the existing SatQuery React workflow to the validated FastAPI/GeoChat backend.

## Workflow

1. Upload Satellite Data
2. Select Area of Interest
3. Ask Question
4. View Analytics
5. View Results
6. Analytics History

## Backend contract

The React application sends `multipart/form-data` to:

`/api/predict`

During Vite development, `/api/*` is proxied to the backend at `http://127.0.0.1:8000` (override with `SATQUERY_BACKEND_URL`).

The browser never receives or stores the backend API secret.

### Task mapping

- `vqa`, `captioning`, `grounding` → backend `task12`
- `change` → backend `task3`
- `fusion` → backend `task4`

The frontend sends the exact backend field names:
- Task 1/2: `task`, `question`, `input_mode`, `image`
- Task 3: `task`, `question`, `before_image`, `after_image`
- Task 4: `task`, `question`, `optical_image`, `sar_image`

## Security boundary

For production, serve the React app and `/api` through the same HTTPS origin using a reverse proxy. Keep the FastAPI server private and keep `SATQUERY_API_KEY` only on the trusted server/proxy side. Do not put `SATQUERY_API_KEY` in `VITE_*` variables because Vite exposes `VITE_*` values to browser code.

The backend already includes:
- API-key authentication support
- request rate limiting
- image size/pixel validation
- CORS allow-list support
- security response headers
- no arbitrary filesystem root from clients
- safe error responses

## Run

### Backend

Use the validated GeoChat Python environment and start:

`python -m uvicorn app:app --host 127.0.0.1 --port 8000`

The backend's own `README.md` and `requirements.txt` contain its environment details.

### Frontend

From this directory:

`npm install`

Then:

`npm run dev`

Open the Vite URL shown in the terminal.

For a production build:

`npm run build`

The generated `dist/` directory is not committed to the source package; build it from the final source.
