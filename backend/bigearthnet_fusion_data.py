"""
Task 4 — BigEarthNet Optical + SAR Fusion Dataset

Uses the actual ben-ge-8k dataset structure:

root_dir/
    sentinel-2/
        <stored_s2_patch_id>/
            <stored_s2_patch_id>_B02.tif
            <stored_s2_patch_id>_B03.tif
            <stored_s2_patch_id>_B04.tif
            ...

    sentinel-1/
        <stored_s1_patch_id>/
            <stored_s1_patch_id>_VV.tif
            <stored_s1_patch_id>_VH.tif
            ...

The parquet patch_id may contain the longer Sentinel-2 naming form:

S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_26_57

while the extracted dataset stores:

S2A_MSIL2A_20170613T101031_26_57

The ben-ge-8k_meta.csv file provides the authoritative mapping.
"""

import os
import re

import numpy as np
import pandas as pd
import rasterio
from PIL import Image
from torch.utils.data import Dataset


# ============================================================
# PATHS
# ============================================================

from config import BIGEARTHNET_ROOT as DEFAULT_ROOT

DEFAULT_METADATA = os.path.join(
    DEFAULT_ROOT,
    "ben-ge-8k_meta.csv",
)

S1_NAME_COLUMN = "s1_name"


# ============================================================
# FUSION QUESTIONS
# ============================================================

FUSION_TEMPLATES = [
    (
        "Use the optical and SAR images together to identify "
        "built-up and water-covered regions."
    ),
    (
        "Does the SAR image confirm what the optical image "
        "shows about built-up areas here?"
    ),
    (
        "Which features are visible in the optical image but "
        "not clearly distinguishable in the SAR image, or "
        "vice versa?"
    ),
]


# ============================================================
# NAME NORMALIZATION
# ============================================================

def canonical_s2_name(patch_id):
    """
    Convert a parquet S2 patch ID to the shortened stored
    folder name.

    Example:

    S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_26_57

    becomes:

    S2A_MSIL2A_20170613T101031_26_57

    Already-short names are returned unchanged.
    """

    patch_id = str(patch_id)

    pattern = (
        r"^(S2[AB]_MSIL2A_[^_]+)"
        r"_N[^_]+"
        r"_R[^_]+"
        r"_T[^_]+"
        r"_(\d+)_(\d+)$"
    )

    match = re.match(pattern, patch_id)

    if match:
        prefix = match.group(1)
        row_a = match.group(2)
        row_b = match.group(3)

        return f"{prefix}_{row_a}_{row_b}"

    return patch_id


# ============================================================
# METADATA MAPPING
# ============================================================

def load_patch_mapping(metadata_path=DEFAULT_METADATA):
    """
    Load the authoritative S2 -> S1 mapping from
    ben-ge-8k_meta.csv.
    """

    if not os.path.exists(metadata_path):
        raise FileNotFoundError(
            "BigEarthNet metadata file not found:\n"
            f"{metadata_path}"
        )

    metadata = pd.read_csv(metadata_path)

    required_columns = [
        "patch_id",
        "patch_id_s1",
    ]

    missing = [
        col
        for col in required_columns
        if col not in metadata.columns
    ]

    if missing:
        raise ValueError(
            "Metadata is missing required columns: "
            f"{missing}"
        )

    mapping = {}

    for _, row in metadata.iterrows():

        s2_stored = str(
            row["patch_id"]
        ).strip()

        s1_stored = str(
            row["patch_id_s1"]
        ).strip()

        if not s2_stored or not s1_stored:
            continue

        mapping[s2_stored] = s1_stored

    if len(mapping) == 0:
        raise ValueError(
            "No valid S2 -> S1 mappings found in metadata."
        )

    print(
        f"Loaded {len(mapping):,} S2 -> S1 mappings from metadata."
    )

    return mapping


# ============================================================
# IMAGE NORMALIZATION
# ============================================================

def _normalize_to_uint8(array):
    """
    Robust per-image normalization using the
    2nd and 98th percentiles.
    """

    array = np.asarray(
        array,
        dtype=np.float32,
    )

    finite = np.isfinite(array)

    if not np.any(finite):
        return np.zeros(
            array.shape,
            dtype=np.uint8,
        )

    valid = array[finite]

    lower = np.percentile(
        valid,
        2,
    )

    upper = np.percentile(
        valid,
        98,
    )

    if upper <= lower:
        upper = lower + 1.0

    normalized = (
        (array - lower)
        / (upper - lower)
    )

    normalized = np.clip(
        normalized,
        0,
        1,
    )

    normalized = (
        normalized * 255
    ).astype(np.uint8)

    return normalized


# ============================================================
# SENTINEL-2 LOADER
# ============================================================

def load_s2_rgb(
    patch_id,
    root_dir,
    size=336,
):
    """
    Load Sentinel-2 RGB.

    B04 -> Red
    B03 -> Green
    B02 -> Blue
    """

    stored_patch_id = canonical_s2_name(
        patch_id
    )

    patch_dir = os.path.join(
        root_dir,
        "sentinel-2",
        stored_patch_id,
    )

    if not os.path.isdir(patch_dir):
        raise FileNotFoundError(
            "Sentinel-2 patch directory not found:\n"
            f"{patch_dir}\n\n"
            "Original parquet patch_id:\n"
            f"{patch_id}\n\n"
            "Resolved stored patch_id:\n"
            f"{stored_patch_id}"
        )

    bands = {}

    for band in [
        "B04",
        "B03",
        "B02",
    ]:

        band_path = os.path.join(
            patch_dir,
            f"{stored_patch_id}_{band}.tif",
        )

        if not os.path.exists(band_path):
            raise FileNotFoundError(
                "Missing Sentinel-2 band:\n"
                f"{band_path}"
            )

        with rasterio.open(band_path) as src:
            bands[band] = src.read(1).astype(
                np.float32
            )

    red = _normalize_to_uint8(
        bands["B04"]
    )

    green = _normalize_to_uint8(
        bands["B03"]
    )

    blue = _normalize_to_uint8(
        bands["B02"]
    )

    rgb = np.stack(
        [
            red,
            green,
            blue,
        ],
        axis=-1,
    )

    image = Image.fromarray(
        rgb,
        mode="RGB",
    )

    image = image.resize(
        (size, size),
        Image.BICUBIC,
    )

    return image


# ============================================================
# SENTINEL-1 LOADER
# ============================================================

def load_s1_grayscale(
    s1_name,
    root_dir,
    size=336,
):
    """
    Load Sentinel-1 SAR.

    Uses both:
        VV
        VH

    Each channel is normalized separately and then averaged
    to create a single grayscale SAR image.
    """

    s1_name = str(
        s1_name
    ).strip()

    patch_dir = os.path.join(
        root_dir,
        "sentinel-1",
        s1_name,
    )

    if not os.path.isdir(patch_dir):
        raise FileNotFoundError(
            "Sentinel-1 patch directory not found:\n"
            f"{patch_dir}"
        )

    vv_path = os.path.join(
        patch_dir,
        f"{s1_name}_VV.tif",
    )

    vh_path = os.path.join(
        patch_dir,
        f"{s1_name}_VH.tif",
    )

    if not os.path.exists(vv_path):
        raise FileNotFoundError(
            "Missing Sentinel-1 VV file:\n"
            f"{vv_path}"
        )

    if not os.path.exists(vh_path):
        raise FileNotFoundError(
            "Missing Sentinel-1 VH file:\n"
            f"{vh_path}"
        )

    with rasterio.open(vv_path) as src:
        vv = src.read(1).astype(
            np.float32
        )

    with rasterio.open(vh_path) as src:
        vh = src.read(1).astype(
            np.float32
        )

    vv_uint8 = _normalize_to_uint8(
        vv
    )

    vh_uint8 = _normalize_to_uint8(
        vh
    )

    sar_gray = (
        (
            vv_uint8.astype(np.float32)
            +
            vh_uint8.astype(np.float32)
        )
        / 2.0
    ).astype(np.uint8)

    sar_rgb = np.stack(
        [
            sar_gray,
            sar_gray,
            sar_gray,
        ],
        axis=-1,
    )

    image = Image.fromarray(
        sar_rgb,
        mode="RGB",
    )

    image = image.resize(
        (size, size),
        Image.BICUBIC,
    )

    return image


# ============================================================
# OPTICAL + SAR COMPOSITE
# ============================================================

def make_composite(
    optical_img,
    sar_img,
):
    """
    Create the Task 4 side-by-side image.

    Left  = Sentinel-2 optical
    Right = Sentinel-1 SAR
    """

    composite = Image.new(
        "RGB",
        (
            optical_img.width * 2,
            optical_img.height,
        ),
    )

    composite.paste(
        optical_img,
        (0, 0),
    )

    composite.paste(
        sar_img,
        (optical_img.width, 0),
    )

    return composite


# ============================================================
# TASK 4 DATASET
# ============================================================

class BigEarthFusionDataset(Dataset):
    """
    Optical + SAR fusion dataset for Task 4.
    """

    def __init__(
        self,
        dataframe,
        root_dir=DEFAULT_ROOT,
        split="train",
        fusion_ratio=0.0,
        metadata_path=None,
    ):

        self.df = (
            dataframe[
                dataframe["split"] == split
            ]
            .reset_index(drop=True)
        )

        self.root_dir = root_dir

        if metadata_path is None:
            metadata_path = os.path.join(
                root_dir,
                "ben-ge-8k_meta.csv",
            )

        self.patch_mapping = load_patch_mapping(
            metadata_path
        )

        self.records = self._build_records(
            fusion_ratio
        )

        if len(self.records) == 0:
            raise ValueError(
                f"No fusion records found for split '{split}'."
            )

        print(
            f"Fusion dataset [{split}] loaded with "
            f"{len(self.records):,} records"
        )

    def _build_records(
        self,
        fusion_ratio,
    ):

        records = []
        missing_mappings = 0

        for _, row in self.df.iterrows():

            if S1_NAME_COLUMN not in row:
                continue

            parquet_s1_name = str(
                row[S1_NAME_COLUMN]
            ).strip()

            if (
                not parquet_s1_name
                or parquet_s1_name.lower() == "nan"
            ):
                continue

            parquet_s2_name = str(
                row["patch_id"]
            ).strip()

            stored_s2_name = canonical_s2_name(
                parquet_s2_name
            )

            # The metadata provides the actual stored S1 name.
            stored_s1_name = self.patch_mapping.get(
                stored_s2_name
            )

            if stored_s1_name is None:

                # Try the original parquet S2 name too.
                stored_s1_name = self.patch_mapping.get(
                    parquet_s2_name
                )

            if stored_s1_name is None:
                missing_mappings += 1
                continue

            records.append(
                {
                    "parquet_patch_id": parquet_s2_name,
                    "patch_id": stored_s2_name,
                    "parquet_s1_name": parquet_s1_name,
                    "s1_name": stored_s1_name,
                    "question": str(row["input"]),
                    "answer": str(row["output"]),
                }
            )

        if missing_mappings:
            print(
                f"WARNING: {missing_mappings:,} rows "
                "could not be mapped through metadata."
            )

        # Optional templated questions.
        #
        # Disabled by default because these currently have
        # no genuine ground-truth answers.

        if fusion_ratio > 0:

            n_templated = int(
                len(records) * fusion_ratio
            )

            for i in range(
                min(
                    n_templated,
                    len(records),
                )
            ):

                base_record = records[i]

                records.append(
                    {
                        "parquet_patch_id":
                            base_record[
                                "parquet_patch_id"
                            ],
                        "patch_id":
                            base_record[
                                "patch_id"
                            ],
                        "parquet_s1_name":
                            base_record[
                                "parquet_s1_name"
                            ],
                        "s1_name":
                            base_record[
                                "s1_name"
                            ],
                        "question":
                            FUSION_TEMPLATES[
                                i % len(FUSION_TEMPLATES)
                            ],
                        "answer":
                            "__NEEDS_ANSWER__",
                    }
                )

            print(
                f"WARNING: added {n_templated:,} "
                "templated fusion records with "
                "placeholder answers."
            )

        return records

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):

        record = self.records[idx]

        optical = load_s2_rgb(
            record["patch_id"],
            self.root_dir,
        )

        sar = load_s1_grayscale(
            record["s1_name"],
            self.root_dir,
        )

        composite = make_composite(
            optical,
            sar,
        )

        prompt = (
            "USER: <image>\n"
            "The left half of this image is an optical "
            "view and the right half is the corresponding "
            "SAR view of the same area. "
            f"{record['question']}\n"
            "ASSISTANT:"
        )

        return {
            "image": composite,
            "prompt": prompt,
            "target": record["answer"],
            "answer": record["answer"],
        }


# ============================================================
# SMOKE TEST
# ============================================================

if __name__ == "__main__":

    PARQUET_PATH = (
        "/content/drive/MyDrive/"
        "satquery_pipeline/SatQueryAI/"
        "datasets/BigEarthNet.txt.parquet"
    )

    ROOT = "/content/ben-ge-8k/ben-ge-8k"

    print("=" * 70)
    print("TASK 4 — FUSION DATASET SMOKE TEST")
    print("=" * 70)

    print("\nLoading one train row from parquet...")

    df = pd.read_parquet(
        PARQUET_PATH,
        engine="pyarrow",
        columns=[
            "patch_id",
            "s1_name",
            "input",
            "output",
            "split",
        ],
    )

    train_df = (
        df[
            df["split"] == "train"
        ]
        .head(1)
        .copy()
    )

    if len(train_df) == 0:
        raise RuntimeError(
            "No train row found in parquet."
        )

    print("\nParquet patch_id:")
    print(
        train_df.iloc[0]["patch_id"]
    )

    print("\nParquet s1_name:")
    print(
        train_df.iloc[0]["s1_name"]
    )

    ds = BigEarthFusionDataset(
        train_df,
        root_dir=ROOT,
        split="train",
        fusion_ratio=0.0,
    )

    sample = ds[0]

    print("\n✅ Optical image loaded")
    print("✅ SAR image loaded")
    print("✅ Optical + SAR composite created")

    print(
        "Composite size:",
        sample["image"].size,
    )

    print("\nPrompt:")
    print(sample["prompt"])

    print("\nTarget:")
    print(sample["target"])

    print("\n" + "=" * 70)
    print("✅ TASK 4 FUSION DATASET SMOKE TEST PASSED")
    print("=" * 70)
    