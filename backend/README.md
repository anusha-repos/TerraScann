# SatQuery AI Backend — Hardened

## Architecture
Frontend → FastAPI (`app.py`) → `agent_executor.py` → `agent_router.py`
→ Task 1/2, Task 3, Task 4 → `ModelManager` → GeoChat-7B + LoRA.

## Security
- API-key authentication can be enforced in production.
- Constant-time API-key comparison.
- Upload size and image-pixel limits.
- Image structure verification before decoding.
- No client-controlled filesystem root.
- Explicit CORS allow-list.
- Basic per-client rate limiting.
- Security response headers.
- Internal runtime errors are not exposed to clients.
- Shared model inference is serialized because adapter switching is mutable.
- Secrets belong in environment variables, never Git.

## Kaggle paths
The defaults match the supplied public datasets:
- GeoChat: `/kaggle/input/datasets/sreenidhirvns/satquery-geochat-7b`
- Task12: `/kaggle/input/datasets/sreenidhirvns/satquery-adapter-backup/adapter`
- Task3: `/kaggle/input/datasets/sreenidhirvns/satquery-task3-change-lora/adapter`
- Task4: `/kaggle/input/datasets/sreenidhirvns/satquery-task4-lora/adapter`
- BigEarthNet: `/kaggle/input/datasets/sreenidhirvns/satquery-bigearthnet/ben-ge-8k/ben-ge-8k`
- SECOND: `/kaggle/input/datasets/sreenidhirvns/satquery-second/SECOND_train_set`

## Important deployment note
The Kaggle notebook is a validation environment, not a production hosting solution. A real frontend should call this API only after the backend is running on a persistent GPU-capable server.

## Test order
1. Environment/dependency check.
2. Backend import check.
3. Dataset/model path check.
4. Model + adapter loading/switching.
5. Task inference tests.
6. FastAPI health.
7. Frontend integration.


## Frontend integration

The React frontend calls `/api/predict`. In local Vite development, the Vite server proxies `/api` to the FastAPI service, so the browser does not need a backend URL or API secret.

For production, terminate HTTPS at a reverse proxy and keep FastAPI on a private interface/network. Keep `SATQUERY_API_KEY` server-side; never place it in a `VITE_*` environment variable.
