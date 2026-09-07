import os
from pathlib import Path


def _env(name: str, default: str) -> str:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else default


def _positive_int(name: str, default: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(1, min(value, maximum))


# Model/data paths
GEOCHAT_REPO = _env("GEOCHAT_REPO", "/content/GeoChat")
GEOCHAT_MODEL_PATH = _env(
    "GEOCHAT_MODEL_PATH",
    "/kaggle/input/datasets/sreenidhirvns/satquery-geochat-7b",
)
TASK12_ADAPTER_PATH = _env(
    "TASK12_ADAPTER_PATH",
    "/kaggle/input/datasets/sreenidhirvns/satquery-adapter-backup/adapter",
)
TASK3_ADAPTER_PATH = _env(
    "TASK3_ADAPTER_PATH",
    "/kaggle/input/datasets/sreenidhirvns/satquery-task3-change-lora/task3_change_lora",
)
TASK4_ADAPTER_PATH = _env(
    "TASK4_ADAPTER_PATH",
    "/kaggle/input/datasets/sreenidhirvns/satquery-task4-lora",
)
BIGEARTHNET_PARQUET_PATH = _env(
    "BIGEARTHNET_PARQUET_PATH",
    "/kaggle/input/datasets/sreenidhirvns/satquery-bigearthnet/BigEarthNet.txt.parquet",
)
BIGEARTHNET_ROOT = _env(
    "BIGEARTHNET_ROOT",
    "/kaggle/input/datasets/sreenidhirvns/satquery-bigearthnet/ben-ge-8k/ben-ge-8k",
)
SECOND_ROOT = _env(
    "SECOND_ROOT",
    "/kaggle/input/datasets/sreenidhirvns/satquery-second/SECOND_train_set",
)

# Runtime
DEVICE = _env("SATQUERY_DEVICE", "cuda")
MAX_NEW_TOKENS = _positive_int("SATQUERY_MAX_NEW_TOKENS", 128, 512)
MAX_UPLOAD_BYTES = _positive_int("SATQUERY_MAX_UPLOAD_BYTES", 10 * 1024 * 1024, 50 * 1024 * 1024)
MAX_IMAGE_PIXELS = _positive_int("SATQUERY_MAX_IMAGE_PIXELS", 25_000_000, 100_000_000)

# API
HOST = _env("SATQUERY_HOST", "0.0.0.0")
PORT = _positive_int("SATQUERY_PORT", 8000, 65535)
SATQUERY_API_KEY = os.getenv("SATQUERY_API_KEY", "").strip()
CORS_ORIGINS = [
    x.strip() for x in os.getenv("SATQUERY_CORS_ORIGINS", "").split(",") if x.strip()
]

# In production, authentication should be enabled.
ENVIRONMENT = _env("SATQUERY_ENVIRONMENT", "development").lower()
REQUIRE_API_KEY = os.getenv(
    "SATQUERY_REQUIRE_API_KEY",
    "true" if ENVIRONMENT == "production" else "false",
).lower() in {"1", "true", "yes", "on"}

# Never accept arbitrary filesystem roots from HTTP clients.
ALLOWED_DATA_ROOTS = {
    str(Path(BIGEARTHNET_ROOT).resolve()),
}
