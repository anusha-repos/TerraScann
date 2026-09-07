"""
SatQuery GeoChat loader.

The loader is deployment-oriented:
- configurable repository/model paths
- no artificial Python-interpreter guard
- discovers CUDA libraries from the active environment
- keeps the original GeoChat builder/inference path
"""

import os
import re
import site
import sys

import torch


GEOCHAT_REPO = os.getenv("GEOCHAT_REPO", "/content/GeoChat")

if not os.path.isdir(GEOCHAT_REPO):
    raise FileNotFoundError(
        f"GeoChat repository not found: {GEOCHAT_REPO}"
    )

if GEOCHAT_REPO not in sys.path:
    sys.path.insert(0, GEOCHAT_REPO)


def _configure_cuda_library_path() -> None:
    """Expose CUDA libraries installed in the active Python environment."""
    candidates = []

    try:
        candidates.extend(site.getsitepackages())
    except Exception:
        pass

    try:
        candidates.append(site.getusersitepackages())
    except Exception:
        pass

    prefix_site = os.path.join(
        sys.prefix,
        "lib",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages",
    )
    candidates.append(prefix_site)

    lib_dirs = []
    for base in dict.fromkeys(candidates):
        if not base:
            continue
        for rel in (
            ("nvidia", "cuda_runtime", "lib"),
            ("nvidia", "cublas", "lib"),
            ("nvidia", "cusparse", "lib"),
            ("nvidia", "cudnn", "lib"),
        ):
            path = os.path.join(base, *rel)
            if os.path.isdir(path):
                lib_dirs.append(path)

    existing = os.environ.get("LD_LIBRARY_PATH", "").split(":")
    merged = [p for p in lib_dirs + existing if p]
    os.environ["LD_LIBRARY_PATH"] = ":".join(dict.fromkeys(merged))


_configure_cuda_library_path()


from geochat.model.builder import load_pretrained_model
from geochat.mm_utils import (
    get_model_name_from_path,
    process_images,
    tokenizer_image_token,
)
from geochat.constants import IMAGE_TOKEN_INDEX


def load_geochat_model(
    model_path=None,
    load_4bit=True,
    load_8bit=False,
):
    """Load the shared GeoChat model and vision processor."""
    if model_path is None:
        model_path = os.getenv(
            "GEOCHAT_MODEL_PATH",
            "/kaggle/input/datasets/sreenidhirvns/satquery-geochat-7b",
        )

    if not os.path.isdir(model_path):
        raise FileNotFoundError(
            f"GeoChat model directory does not exist: {model_path}"
        )

    if not os.path.isfile(os.path.join(model_path, "config.json")):
        raise FileNotFoundError(
            f"GeoChat config.json not found: {model_path}"
        )

    model_name = get_model_name_from_path(model_path)

    return load_pretrained_model(
        model_path=model_path,
        model_base=None,
        model_name=model_name,
        load_8bit=load_8bit,
        load_4bit=load_4bit,
        device_map="auto",
    )


def build_prompt(question: str) -> str:
    question = str(question).strip()
    if not question:
        raise ValueError("Question cannot be empty.")
    return f"USER: <image>\n{question}\nASSISTANT:"


def generate_answer(
    question,
    image,
    tokenizer,
    model,
    image_processor,
    max_new_tokens=128,
):
    prompt = build_prompt(question)

    image_tensor = process_images(
        [image],
        image_processor,
        model.config,
    )

    device = next(model.parameters()).device
    if device.type == "cuda":
        image_tensor = image_tensor.to(device=device, dtype=torch.float16)
    else:
        image_tensor = image_tensor.to(device=device)

    input_ids = tokenizer_image_token(
        prompt,
        tokenizer,
        IMAGE_TOKEN_INDEX,
        return_tensors="pt",
    ).unsqueeze(0).to(device)

    with torch.inference_mode():
        output_ids = model.generate(
            input_ids=input_ids,
            images=image_tensor,
            do_sample=False,
            temperature=0,
            max_new_tokens=max_new_tokens,
            use_cache=True,
        )

    generated_ids = output_ids[:, input_ids.shape[1]:]
    return tokenizer.batch_decode(
        generated_ids,
        skip_special_tokens=True,
    )[0].strip()


def parse_geochat_boxes(text):
    if not text:
        return []

    results = []
    pattern = re.compile(
        r"<box>\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*</box>"
        r"(?:\s*([^<\n]+))?",
        re.IGNORECASE,
    )

    for match in pattern.finditer(str(text)):
        results.append({
            "box": [int(x) for x in match.group(1, 2, 3, 4)],
            "label": (match.group(5) or "").strip(),
        })
    return results
