import io
import os
import secrets
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

from agent_executor import execute_request

from config import (
    CORS_ORIGINS,
    MAX_IMAGE_PIXELS,
    MAX_NEW_TOKENS,
    MAX_UPLOAD_BYTES,
    PORT,
    HOST,
    REQUIRE_API_KEY,
    SATQUERY_API_KEY,
)
from model_manager import model_manager
from response_builder import build_error_response, build_response


APP_NAME = "SatQuery AI"
APP_VERSION = "2.0.0"

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Secure remote-sensing inference API for Task 1/2 VQA, "
        "Task 3 change detection, and Task 4 optical/SAR fusion."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )


_RATE_WINDOW_SECONDS = 60
_RATE_MAX_REQUESTS = 20
_rate_hits = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    return (forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown"))


def _rate_limit(request: Request) -> None:
    key = _client_key(request)
    now = time.monotonic()
    q = _rate_hits[key]

    while q and now - q[0] > _RATE_WINDOW_SECONDS:
        q.popleft()

    if len(q) >= _RATE_MAX_REQUESTS:
        raise ValueError("Rate limit exceeded. Please try again later.")

    q.append(now)


def _authenticate(api_key: Optional[str]) -> None:
    if not REQUIRE_API_KEY:
        return

    if not SATQUERY_API_KEY:
        raise RuntimeError("Server authentication is not configured.")

    if not api_key or not secrets.compare_digest(api_key, SATQUERY_API_KEY):
        raise PermissionError("Invalid API key.")


def _parse_max_tokens(value: Optional[str]) -> Optional[int]:
    if value is None or not str(value).strip():
        return None

    try:
        parsed = int(str(value).strip())
    except ValueError as exc:
        raise ValueError("max_new_tokens must be an integer.") from exc

    if parsed < 1 or parsed > min(MAX_NEW_TOKENS, 512):
        raise ValueError(
            f"max_new_tokens must be between 1 and {min(MAX_NEW_TOKENS, 512)}."
        )

    return parsed


async def _load_uploaded_image(
    uploaded_file: Optional[UploadFile],
) -> Optional[Image.Image]:

    if uploaded_file is None:
        return None

    filename = (uploaded_file.filename or "upload").replace("\x00", "")
    content_type = (uploaded_file.content_type or "").lower()

    if content_type and not content_type.startswith("image/"):
        raise ValueError(f"Unsupported uploaded content type for '{filename}'.")

    data = await uploaded_file.read(MAX_UPLOAD_BYTES + 1)

    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Uploaded image '{filename}' exceeds the {MAX_UPLOAD_BYTES} byte limit."
        )

    if not data:
        raise ValueError(f"Uploaded image '{filename}' is empty.")

    try:
        # verify() checks the file structure before decoding.
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()

        with Image.open(io.BytesIO(data)) as decoded:
            if decoded.width * decoded.height > MAX_IMAGE_PIXELS:
                raise ValueError(
                    f"Uploaded image '{filename}' exceeds the pixel limit."
                )
            return decoded.convert("RGB")

    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(
            f"Uploaded file '{filename}' is not a valid image."
        ) from exc


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def root():
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "ok",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "model_loaded": model_manager.model is not None,
        "active_adapter": model_manager.get_active_adapter(),
    }


@app.get("/ready")
def ready():
    model_ready = model_manager.model is not None
    return JSONResponse(
        status_code=200 if model_ready else 503,
        content={
            "status": "ready" if model_ready else "not_ready",
            "model_loaded": model_ready,
        },
    )


@app.post("/predict")
async def predict(
    request: Request,
    task: str = Form(...),
    question: str = Form(...),
    input_mode: str = Form("dual_sensor"),
    image: Optional[UploadFile] = File(None),
    patch_id: Optional[str] = Form(None),
    patch_id_s1: Optional[str] = Form(None),
    before_image: Optional[UploadFile] = File(None),
    after_image: Optional[UploadFile] = File(None),
    optical_image: Optional[UploadFile] = File(None),
    sar_image: Optional[UploadFile] = File(None),
    s1_name: Optional[str] = Form(None),
    # root_dir deliberately removed from public API
    max_new_tokens: Optional[str] = Form(None),
    x_api_key: Optional[str] = Header(None),
):
    try:
        _rate_limit(request)
        _authenticate(x_api_key)

        parsed_tokens = _parse_max_tokens(max_new_tokens)

        result = execute_request(
            task=task,
            question=question,
            image=await _load_uploaded_image(image),
            input_mode=input_mode,
            patch_id=patch_id,
            patch_id_s1=patch_id_s1,
            before_image=await _load_uploaded_image(before_image),
            after_image=await _load_uploaded_image(after_image),
            optical_image=await _load_uploaded_image(optical_image),
            sar_image=await _load_uploaded_image(sar_image),
            s1_name=s1_name,
            max_new_tokens=parsed_tokens,
        )

        return JSONResponse(
            status_code=200,
            content=build_response(result),
        )

    except PermissionError as exc:
        return JSONResponse(
            status_code=401,
            content=build_error_response(str(exc), "authentication_error"),
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content=build_error_response(str(exc), "validation_error"),
        )
    except RuntimeError:
        # Do not leak model/filesystem internals to HTTP clients.
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                "The inference service could not complete the request.",
                "runtime_error",
            ),
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                "An internal server error occurred.",
                "internal_error",
            ),
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
