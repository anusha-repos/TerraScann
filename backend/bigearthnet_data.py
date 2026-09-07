import os
import random
import numpy as np
import pandas as pd
import torch
from PIL import Image

import rasterio
from torch.utils.data import Dataset

from geochat_loader import (
    process_images,
    tokenizer_image_token,
    IMAGE_TOKEN_INDEX,
)


# ============================================================
# PATHS
# ============================================================

from config import BIGEARTHNET_ROOT

S1_ROOT = os.path.join(BIGEARTHNET_ROOT, "sentinel-1")
S2_ROOT = os.path.join(BIGEARTHNET_ROOT, "sentinel-2")

META_FILE = os.path.join(
    BIGEARTHNET_ROOT,
    "ben-ge-8k_meta.csv",
)

ERA5_FILE = os.path.join(
    BIGEARTHNET_ROOT,
    "ben-ge-8k_era-5.csv",
)

WORLDCOVER_FILE = os.path.join(
    BIGEARTHNET_ROOT,
    "ben-ge-8k_esaworldcover.csv",
)


# ============================================================
# BASIC HELPERS
# ============================================================

def load_qa_dataframe(parquet_path, columns=None, filters=None):
    """
    Kept for compatibility with the original pipeline.
    """

    if filters is None:
        return pd.read_parquet(parquet_path, columns=columns)

    df = pd.read_parquet(parquet_path, columns=columns)

    for column, operator, value in filters:
        if operator == "=":
            df = df[df[column] == value]
        elif operator == "in":
            df = df[df[column].isin(value)]
        elif operator == "!=":
            df = df[df[column] != value]
        else:
            raise ValueError(f"Unsupported filter operator: {operator}")

    return df.reset_index(drop=True)


def split_tasks(df):
    """
    Split a QA dataframe into task groups.
    Kept for compatibility with the existing pipeline.
    """

    result = {}

    if "task" in df.columns:
        for task_name, group in df.groupby("task"):
            result[task_name] = group.reset_index(drop=True)

    if "type" in df.columns:
        result["binary"] = df[df["type"] == "binary"].reset_index(drop=True)
        result["mcq"] = df[df["type"] == "mcq"].reset_index(drop=True)

    return result


def select_balanced_subset(
    df,
    n_total,
    category_column="type",
    random_state=42,
):
    """
    Balanced subset helper.
    """

    if n_total >= len(df):
        return df.sample(
            frac=1,
            random_state=random_state
        ).reset_index(drop=True)

    categories = df[category_column].dropna().unique()

    n_each = n_total // len(categories)

    pieces = []

    for category in categories:
        subset = df[df[category_column] == category]

        n = min(n_each, len(subset))

        pieces.append(
            subset.sample(
                n=n,
                random_state=random_state
            )
        )

    result = pd.concat(pieces, ignore_index=True)

    remaining = n_total - len(result)

    if remaining > 0:
        unused = df.drop(result.index, errors="ignore")

        if len(unused) > 0:
            extra = unused.sample(
                n=min(remaining, len(unused)),
                random_state=random_state
            )

            result = pd.concat(
                [result, extra],
                ignore_index=True
            )

    return result.sample(
        frac=1,
        random_state=random_state
    ).reset_index(drop=True)


# ============================================================
# TIFF HELPERS
# ============================================================

def read_tif(path):
    """
    Read a single-band GeoTIFF as float32.
    """

    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float32)

    arr = np.nan_to_num(
        arr,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    return arr


def percentile_normalize(
    arr,
    low=2,
    high=98,
):
    """
    Robust normalization to [0, 1].
    """

    arr = np.nan_to_num(
        arr,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    valid = arr[np.isfinite(arr)]

    if valid.size == 0:
        return np.zeros_like(arr, dtype=np.float32)

    lo = np.percentile(valid, low)
    hi = np.percentile(valid, high)

    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)

    arr = (arr - lo) / (hi - lo)

    return np.clip(
        arr,
        0.0,
        1.0
    ).astype(np.float32)


def to_uint8(arr):
    return np.clip(
        arr * 255.0,
        0,
        255
    ).astype(np.uint8)


# ============================================================
# SENTINEL-2
# ============================================================

def find_s2_file(patch_id, band):
    """
    Find:
    S2_ROOT / patch_id / patch_id_Bxx.tif
    """

    filename = f"{patch_id}_{band}.tif"

    path = os.path.join(
        S2_ROOT,
        patch_id,
        filename,
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Sentinel-2 file not found:\n{path}"
        )

    return path


def load_s2_rgb(patch_id):
    """
    Sentinel-2:
        B04 -> Red
        B03 -> Green
        B02 -> Blue
    """

    red = percentile_normalize(
        read_tif(find_s2_file(patch_id, "B04"))
    )

    green = percentile_normalize(
        read_tif(find_s2_file(patch_id, "B03"))
    )

    blue = percentile_normalize(
        read_tif(find_s2_file(patch_id, "B02"))
    )

    rgb = np.stack(
        [
            red,
            green,
            blue,
        ],
        axis=-1,
    )

    return to_uint8(rgb)


# ============================================================
# SENTINEL-1
# ============================================================

def find_s1_file(patch_id_s1, polarization):
    """
    Find:
    S1_ROOT / patch_id_s1 / patch_id_s1_VV.tif
    S1_ROOT / patch_id_s1 / patch_id_s1_VH.tif
    """

    filename = f"{patch_id_s1}_{polarization}.tif"

    path = os.path.join(
        S1_ROOT,
        patch_id_s1,
        filename,
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Sentinel-1 file not found:\n{path}"
        )

    return path


def load_s1_rgb(patch_id_s1):
    """
    Convert Sentinel-1 VV/VH into a 3-channel
    pseudo-RGB representation:

        R = VV
        G = VH
        B = mean(VV,VH)
    """

    vv = percentile_normalize(
        read_tif(
            find_s1_file(
                patch_id_s1,
                "VV"
            )
        )
    )

    vh = percentile_normalize(
        read_tif(
            find_s1_file(
                patch_id_s1,
                "VH"
            )
        )
    )

    mean_channel = (
        0.5 * vv +
        0.5 * vh
    )

    rgb = np.stack(
        [
            vv,
            vh,
            mean_channel,
        ],
        axis=-1,
    )

    return to_uint8(rgb)


# ============================================================
# S1 + S2 FUSION
# ============================================================

def make_dual_sensor_image(
    patch_id,
    patch_id_s1,
):
    """
    Create one RGB-compatible image:

        LEFT  = Sentinel-1
        RIGHT = Sentinel-2

    This allows the existing GeoChat vision encoder
    to consume both sensors without modifying the
    pretrained 3-channel architecture.
    """

    s1 = Image.fromarray(
        load_s1_rgb(patch_id_s1)
    ).convert("RGB")

    s2 = Image.fromarray(
        load_s2_rgb(patch_id)
    ).convert("RGB")

    # Make both images the same height.
    height = min(
        s1.height,
        s2.height
    )

    s1_ratio = s1.width / s1.height
    s2_ratio = s2.width / s2.height

    s1 = s1.resize(
        (
            max(1, int(height * s1_ratio)),
            height,
        ),
        Image.Resampling.BILINEAR,
    )

    s2 = s2.resize(
        (
            max(1, int(height * s2_ratio)),
            height,
        ),
        Image.Resampling.BILINEAR,
    )

    fused = Image.new(
        "RGB",
        (
            s1.width + s2.width,
            height,
        ),
    )

    fused.paste(s1, (0, 0))
    fused.paste(s2, (s1.width, 0))

    return fused


# ============================================================
# METADATA
# ============================================================

def load_benge_metadata():
    """
    Load and merge:
        main metadata
        ERA5
        ESA WorldCover
    """

    meta = pd.read_csv(META_FILE)
    era5 = pd.read_csv(ERA5_FILE)
    worldcover = pd.read_csv(WORLDCOVER_FILE)

    # Remove duplicate key columns before merge.
    era5 = era5.drop(
        columns=["patch_id_s1"],
        errors="ignore"
    )

    merged = meta.merge(
        era5,
        on="patch_id",
        how="left",
        suffixes=("", "_era5"),
    )

    worldcover = worldcover.drop(
        columns=["filename"],
        errors="ignore"
    )

    merged = merged.merge(
        worldcover,
        on="patch_id",
        how="left",
        suffixes=("", "_worldcover"),
    )

    return merged.reset_index(drop=True)


# ============================================================
# LAND-COVER LABEL
# ============================================================

WORLDCOVER_CLASSES = [
    "tree cover",
    "shrubland",
    "grassland",
    "cropland",
    "built-up",
    "bare/sparse vegetation",
    "snow and ice",
    "permanent water bodies",
    "herbaceous wetland",
    "mangroves",
    "moss and lichen",
]


def get_dominant_landcover(row):
    values = {}

    for name in WORLDCOVER_CLASSES:
        value = row.get(name, 0.0)

        try:
            value = float(value)
        except Exception:
            value = 0.0

        if not np.isfinite(value):
            value = 0.0

        values[name] = value

    return max(
        values,
        key=values.get
    )


def get_landcover_ranking(row):
    """
    Classes sorted by fraction, descending. Rank-based rather than
    threshold-based (e.g. "fraction > 0.15") on purpose — the actual 0-1
    vs 0-100 scale of the WorldCover CSV isn't confirmed, and a hardcoded
    threshold silently breaks if that assumption is wrong. Rank
    comparisons are correct regardless of scale.
    """
    values = {}
    for name in WORLDCOVER_CLASSES:
        value = row.get(name, 0.0)
        try:
            value = float(value)
        except Exception:
            value = 0.0
        if not np.isfinite(value):
            value = 0.0
        values[name] = value

    return sorted(values.items(), key=lambda kv: kv[1], reverse=True)


def load_s2_image(patch_id):
    """Single optical image, PIL, no compositing — for genuinely
    single-image Task 1 examples (make_dual_sensor_image always builds
    a composite; this is the plain image on its own)."""
    return Image.fromarray(load_s2_rgb(patch_id)).convert("RGB")


def load_s1_image(patch_id_s1):
    """Single SAR image, PIL, no compositing — same reasoning as
    load_s2_image above."""
    return Image.fromarray(load_s1_rgb(patch_id_s1)).convert("RGB")


# ============================================================
# NATURAL-LANGUAGE TRAINING EXAMPLES
# ============================================================

def make_training_examples(
    df,
    target_n=10000,
    random_state=42,
):
    """
    Generate high-quality image-grounded instruction
    examples from the paired S1/S2 dataset.

    Each image can contribute more than one question,
    allowing 10,000 examples from 8,000 paired images.
    """

    rng = random.Random(random_state)

    rows = df.to_dict("records")

    rng.shuffle(rows)

    examples = []

    question_templates = [
        "What is the dominant land-cover type in this satellite patch?",
        "Which land-cover class occupies the largest proportion of this area?",
        "Based on the satellite imagery, what is the main land-cover type?",
        "What is the temperature recorded for this paired Sentinel observation?",
        "What is the relative humidity associated with this observation?",
        "What is the atmospheric pressure level for this observation?",
        "What season is associated with the Sentinel-2 observation?",
        "What season is associated with the Sentinel-1 observation?",
        "What are the approximate longitude and latitude of this patch?",
        "Which land-cover type has the highest WorldCover proportion?",
    ]

    def random_input_mode():
        """
        40% single optical / 15% single SAR / 45% composite. Previously
        every example was forced through make_dual_sensor_image — the
        model never saw a genuinely single image during training, which
        doesn't match the mandatory single-image VQA task in the actual
        problem statement (single image is one of three defined input
        types, not a special case).
        """
        r = rng.random()
        if r < 0.40:
            return "single_optical"
        elif r < 0.55:
            return "single_sar"
        return "dual_sensor"

    for row in rows:

        if len(examples) >= target_n:
            break

        patch_id = row["patch_id"]
        patch_id_s1 = row["patch_id_s1"]

        dominant = get_dominant_landcover(row)

        # ----------------------------------------------------
        # 1. Dominant land cover
        # ----------------------------------------------------

        examples.append(
            {
                "patch_id": patch_id,
                "patch_id_s1": patch_id_s1,
                "question":
                    "What is the dominant land-cover type in this satellite patch?",
                "answer":
                    f"The dominant land-cover type is {dominant}.",
                "kind": "landcover",
                "input_mode": random_input_mode(),
            }
        )

        if len(examples) >= target_n:
            break

        # ----------------------------------------------------
        # 2. Temperature
        # ----------------------------------------------------

        temp = row.get("temperature_s2", np.nan)

        if pd.notna(temp):
            examples.append(
                {
                    "patch_id": patch_id,
                    "patch_id_s1": patch_id_s1,
                    "question":
                        "What is the temperature recorded for the Sentinel-2 observation?",
                    "answer":
                        f"The Sentinel-2 temperature is approximately {float(temp):.2f} K.",
                    "kind": "temperature",
                    "input_mode": random_input_mode(),
                }
            )

        if len(examples) >= target_n:
            break

        # ----------------------------------------------------
        # 3. Humidity
        # ----------------------------------------------------

        humidity = row.get(
            "relhumidity_s2",
            np.nan
        )

        if pd.notna(humidity):
            examples.append(
                {
                    "patch_id": patch_id,
                    "patch_id_s1": patch_id_s1,
                    "question":
                        "What is the relative humidity associated with this observation?",
                    "answer":
                        f"The relative humidity is approximately {float(humidity):.2f}%.",
                    "kind": "humidity",
                    "input_mode": random_input_mode(),
                }
            )

        if len(examples) >= target_n:
            break

        # ----------------------------------------------------
        # 4. Season
        # ----------------------------------------------------

        season = row.get(
            "season_s2",
            np.nan
        )

        if pd.notna(season):
            examples.append(
                {
                    "patch_id": patch_id,
                    "patch_id_s1": patch_id_s1,
                    "question":
                        "What season is associated with the Sentinel-2 observation?",
                    "answer":
                        f"The Sentinel-2 observation corresponds to season value {float(season):.3f}.",
                    "kind": "season",
                    "input_mode": random_input_mode(),
                }
            )

        if len(examples) >= target_n:
            break

        # ----------------------------------------------------
        # 5. Coordinates
        # ----------------------------------------------------

        lon = row.get("lon", np.nan)
        lat = row.get("lat", np.nan)

        if pd.notna(lon) and pd.notna(lat):
            examples.append(
                {
                    "patch_id": patch_id,
                    "patch_id_s1": patch_id_s1,
                    "question":
                        "What are the approximate geographic coordinates of this patch?",
                    "answer":
                        f"The approximate coordinates are longitude {float(lon):.5f}, latitude {float(lat):.5f}.",
                    "kind": "coordinates",
                    "input_mode": random_input_mode(),
                }
            )

        if len(examples) >= target_n:
            break

        # ----------------------------------------------------
        # 6. Dominant land-cover alternative wording
        # ----------------------------------------------------

        examples.append(
            {
                "patch_id": patch_id,
                "patch_id_s1": patch_id_s1,
                "question":
                    "Which land-cover class occupies the largest proportion of this area?",
                "answer":
                    f"The largest land-cover class is {dominant}.",
                "kind": "landcover_alt",
                "input_mode": random_input_mode(),
            }
        )

        if len(examples) >= target_n:
            break

        # ----------------------------------------------------
        # 7. GENUINE FUSION — always dual_sensor, and unlike blocks 1-6,
        # these can't be answered correctly from metadata alone without
        # attending to what the WorldCover ranking actually says about
        # this specific patch. Grounded in real ranking data, not fabricated.
        # ----------------------------------------------------

        ranking = get_landcover_ranking(row)
        top_2_classes = {name for name, _ in ranking[:2]}

        examples.append(
            {
                "patch_id": patch_id,
                "patch_id_s1": patch_id_s1,
                "question":
                    "Using the optical and SAR images together, what is the "
                    "dominant land-cover type in this scene?",
                "answer":
                    f"Combining the optical image's spectral appearance with "
                    f"the SAR image's structural signature, the dominant "
                    f"land-cover type is {dominant}.",
                "kind": "fusion_dominant",
                "input_mode": "dual_sensor",
            }
        )

        if len(examples) >= target_n:
            break

        built_up_prominent = "built-up" in top_2_classes
        examples.append(
            {
                "patch_id": patch_id,
                "patch_id_s1": patch_id_s1,
                "question":
                    "Based on both the optical and SAR imagery, is built-up "
                    "area one of the most prominent land-cover types here?",
                "answer": (
                    "Yes — built-up area ranks among the most prominent "
                    "land-cover types in this patch, consistent with both "
                    "the structures visible in the optical image and the "
                    "strong SAR backscatter typical of urban surfaces."
                    if built_up_prominent else
                    "No — built-up area is not among the dominant land-cover "
                    "types here; other classes account for more of this "
                    "patch in both the optical and SAR imagery."
                ),
                "kind": "fusion_builtup",
                "input_mode": "dual_sensor",
            }
        )

        if len(examples) >= target_n:
            break

        water_prominent = "permanent water bodies" in top_2_classes
        examples.append(
            {
                "patch_id": patch_id,
                "patch_id_s1": patch_id_s1,
                "question":
                    "Comparing the optical and SAR images, does this patch "
                    "contain a substantial water body?",
                "answer": (
                    "Yes — a substantial water body is present, visible as a "
                    "distinct region in the optical image and as a notably "
                    "smooth, low-backscatter area in the SAR image."
                    if water_prominent else
                    "No — there is no substantial permanent water body in "
                    "this patch based on both the optical and SAR observations."
                ),
                "kind": "fusion_water",
                "input_mode": "dual_sensor",
            }
        )

        if len(examples) >= target_n:
            break

        vegetation_classes = {"tree cover", "shrubland", "grassland", "cropland"}
        vegetation_dominant = dominant in vegetation_classes
        examples.append(
            {
                "patch_id": patch_id,
                "patch_id_s1": patch_id_s1,
                "question":
                    "Using both sensors together, how would you characterize "
                    "the vegetation cover in this area?",
                "answer": (
                    "Vegetation appears to be the dominant land cover in this "
                    "scene, consistent with the textures visible in the "
                    "optical image and the volume backscatter typical of "
                    "vegetated surfaces in the SAR image."
                    if vegetation_dominant else
                    "Vegetation is not the dominant feature in this scene; "
                    "other land-cover types are more prominent in both the "
                    "optical and SAR imagery."
                ),
                "kind": "fusion_vegetation",
                "input_mode": "dual_sensor",
            }
        )

    if len(examples) < target_n:
        raise RuntimeError(
            f"Only generated {len(examples)} examples, "
            f"but {target_n} were requested."
        )

    result = pd.DataFrame(
        examples[:target_n]
    )

    return result.sample(
        frac=1,
        random_state=random_state
    ).reset_index(drop=True)


# ============================================================
# DATASET
# ============================================================

class BigEarthVQADataset(Dataset):

    def __init__(
        self,
        dataframe,
        tokenizer=None,
    ):

        self.df = dataframe.reset_index(drop=True)
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.df)

    def __getitem__(self, index):

        row = self.df.iloc[index]

        # Backward-compatible default: any example without an input_mode
        # tag (e.g. old cached CSVs from before this fix) falls back to
        # the original always-composite behavior.
        mode = row.get("input_mode", "dual_sensor")

        if mode == "single_optical":
            image = load_s2_image(row["patch_id"])
        elif mode == "single_sar":
            image = load_s1_image(row["patch_id_s1"])
        else:
            image = make_dual_sensor_image(
                row["patch_id"],
                row["patch_id_s1"],
            )

        question = str(row["question"])
        answer = str(row["answer"])

        prompt = (
            "USER: <image>\n"
            f"{question}\n"
            "ASSISTANT:"
        )

        return {
            "image": image,
            "prompt": prompt,
            "answer": answer,
            "patch_id": row["patch_id"],
            "patch_id_s1": row["patch_id_s1"],
            "kind": row["kind"],
            "input_mode": mode,
        }


# ============================================================
# COLLATE
# ============================================================

def make_collate_fn(
    tokenizer,
    image_processor,
    model_cfg,
):
    """
    IMPORTANT FIX: the previous version only masked padding tokens from the
    loss, which means the model was being trained to predict the QUESTION
    text too, not just the answer. That's not a crash — it runs fine — but
    it dilutes every gradient step with an easy, useless sub-task (copying
    the prompt back out) instead of concentrating entirely on generating
    good answers. This version masks the prompt portion the same way the
    rest of this pipeline already does elsewhere (compute prompt-only
    token length, mask everything before the answer starts).
    """

    def collate_fn(batch):

        images = [
            item["image"]
            for item in batch
        ]

        processed_images = process_images(
            images,
            image_processor,
            model_cfg,
        )

        input_ids_list = []
        labels_list = []

        for item in batch:

            full_text = item["prompt"] + " " + item["answer"]

            full_ids = tokenizer_image_token(
                full_text,
                tokenizer,
                IMAGE_TOKEN_INDEX,
                return_tensors="pt",
            )

            # Prompt-only length, so we know exactly where the answer starts
            # and mask everything before it from the loss.
            prompt_ids = tokenizer_image_token(
                item["prompt"],
                tokenizer,
                IMAGE_TOKEN_INDEX,
                return_tensors="pt",
            )

            labels = full_ids.clone()
            labels[: prompt_ids.shape[0]] = -100

            input_ids_list.append(full_ids)
            labels_list.append(labels)

        max_len = max(
            x.shape[0]
            for x in input_ids_list
        )

        pad_id = (
            tokenizer.pad_token_id
            if tokenizer.pad_token_id is not None
            else tokenizer.eos_token_id
        )

        padded = torch.full(
            (len(input_ids_list), max_len),
            pad_id,
            dtype=torch.long,
        )

        padded_labels = torch.full(
            (len(labels_list), max_len),
            -100,
            dtype=torch.long,
        )

        attention_mask = torch.zeros_like(padded)

        for i, (ids, labels) in enumerate(zip(input_ids_list, labels_list)):
            length = ids.shape[0]
            padded[i, :length] = ids
            padded_labels[i, :length] = labels
            attention_mask[i, :length] = 1

        return {
            "input_ids": padded,
            "labels": padded_labels,
            "attention_mask": attention_mask,
            "images": processed_images,
        }

    return collate_fn