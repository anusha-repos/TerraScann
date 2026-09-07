"""
SatQuery Task 4 — Optical + SAR Fusion Inference

Backend inference module for Task 4.

Input:
    - Sentinel-2 optical image
    - Sentinel-1 SAR image
    - user question

The two images are combined exactly like the Task 4
BigEarthNet fusion pipeline:

    Optical | SAR

The resulting composite is passed to GeoChat using
one <image> token.

The Task 4 LoRA adapter is selected through the shared
ModelManager.
"""

import torch

import geochat_loader

from geochat_loader import (
    process_images,
    tokenizer_image_token,
    IMAGE_TOKEN_INDEX,
)

from bigearthnet_fusion_data import (
    load_s2_rgb,
    load_s1_grayscale,
    make_composite,
)


# ============================================================
# IMAGE VALIDATION
# ============================================================

def validate_fusion_images(
    optical_image,
    sar_image,
):
    """
    Validate the two images required for Task 4.
    """

    if optical_image is None:
        raise ValueError(
            "Task 4 requires an optical Sentinel-2 image."
        )

    if sar_image is None:
        raise ValueError(
            "Task 4 requires a SAR Sentinel-1 image."
        )


# ============================================================
# BUILD FUSION IMAGE FROM PIL IMAGES
# ============================================================

def make_fusion_image(
    optical_image,
    sar_image,
):
    """
    Create the Task 4 optical + SAR composite.

    Left  = Sentinel-2 optical
    Right = Sentinel-1 SAR
    """

    validate_fusion_images(
        optical_image,
        sar_image,
    )

    return make_composite(
        optical_image,
        sar_image,
    )


# ============================================================
# LOAD FUSION IMAGE FROM BIGEARTHNET PATCH IDS
# ============================================================

def load_fusion_from_patch_ids(
    patch_id,
    s1_name,
    root_dir,
    size=336,
):
    """
    Load a Sentinel-2/Sentinel-1 pair directly from
    the BigEarthNet dataset.

    This follows the same loaders used by
    BigEarthFusionDataset.
    """

    if patch_id is None:
        raise ValueError(
            "patch_id is required."
        )

    if s1_name is None:
        raise ValueError(
            "s1_name is required."
        )

    optical_image = load_s2_rgb(
        patch_id=patch_id,
        root_dir=root_dir,
        size=size,
    )

    sar_image = load_s1_grayscale(
        s1_name=s1_name,
        root_dir=root_dir,
        size=size,
    )

    return make_fusion_image(
        optical_image,
        sar_image,
    )


# ============================================================
# GENERATE TASK 4 ANSWER
# ============================================================

def generate_fusion_answer(
    tokenizer,
    model,
    image_processor,
    image,
    question,
    max_new_tokens=80,
):
    """
    Generate a Task 4 answer using GeoChat + Task 4 LoRA.

    The optical + SAR pair is represented as one composite
    image, therefore the prompt contains exactly one <image>
    token.
    """

    if question is None:
        raise ValueError(
            "Task 4 question cannot be None."
        )

    question = str(
        question
    ).strip()

    if not question:
        raise ValueError(
            "Task 4 question cannot be empty."
        )

    prompt = (
        "USER: <image>\n"
        "The left half of this image is an optical "
        "view and the right half is the corresponding "
        "SAR view of the same area. "
        f"{question}\n"
        "ASSISTANT:"
    )

    image_tensor = process_images(
        [image],
        image_processor,
        model.config,
    )

    image_tensor = image_tensor.to(
        model.device,
        dtype=torch.float16,
    )

    input_ids = tokenizer_image_token(
        prompt,
        tokenizer,
        IMAGE_TOKEN_INDEX,
        return_tensors="pt",
    ).unsqueeze(0).to(model.device)

    with torch.inference_mode():

        output_ids = model.generate(
            input_ids=input_ids,
            images=image_tensor,
            do_sample=False,
            temperature=0,
            max_new_tokens=max_new_tokens,
            use_cache=True,
        )

    generated_ids = (
        output_ids[:, input_ids.shape[1]:]
    )

    answer = tokenizer.batch_decode(
        generated_ids,
        skip_special_tokens=True,
    )[0].strip()

    return answer


# ============================================================
# MAIN BACKEND ENTRY POINT
# ============================================================

def run_task4(
    model_manager,
    question,
    optical_image=None,
    sar_image=None,
    patch_id=None,
    s1_name=None,
    root_dir=None,
    max_new_tokens=80,
):
    """
    Main backend entry point for Task 4.

    Two input modes are supported.

    Mode 1 — Uploaded images:
        optical_image + sar_image

    Mode 2 — BigEarthNet patch IDs:
        patch_id + s1_name + root_dir

    Returns a standardized SatQuery response dictionary.
    """

    if question is None:
        raise ValueError(
            "Task 4 question cannot be None."
        )

    question = str(
        question
    ).strip()

    if not question:
        raise ValueError(
            "Task 4 question cannot be empty."
        )

    # --------------------------------------------------------
    # Resolve input images
    # --------------------------------------------------------

    if (
        optical_image is not None
        or sar_image is not None
    ):

        # Uploaded-image mode requires both images.
        validate_fusion_images(
            optical_image,
            sar_image,
        )

        fused_image = make_fusion_image(
            optical_image,
            sar_image,
        )

        input_source = "uploaded_images"

    else:

        # BigEarthNet patch mode.
        if patch_id is None:
            raise ValueError(
                "Provide either optical_image + sar_image "
                "or patch_id + s1_name."
            )

        if s1_name is None:
            raise ValueError(
                "s1_name is required when using patch_id."
            )

        if root_dir is None:
            from config import BIGEARTHNET_ROOT

            root_dir = BIGEARTHNET_ROOT

        fused_image = load_fusion_from_patch_ids(
            patch_id=patch_id,
            s1_name=s1_name,
            root_dir=root_dir,
        )

        input_source = "bigearthnet_patch"

    # --------------------------------------------------------
    # Load Task 4 model through shared ModelManager
    # --------------------------------------------------------

    model = model_manager.get_model(
        "task4"
    )

    tokenizer = model_manager.get_tokenizer()

    image_processor = (
        model_manager.get_image_processor()
    )

    # --------------------------------------------------------
    # Generate answer
    # --------------------------------------------------------

    answer = generate_fusion_answer(
        tokenizer=tokenizer,
        model=model,
        image_processor=image_processor,
        image=fused_image,
        question=question,
        max_new_tokens=max_new_tokens,
    )

    # --------------------------------------------------------
    # Standard backend response
    # --------------------------------------------------------

    return {
        "task": "task4",
        "input_mode": "optical_sar_fusion",
        "input_source": input_source,
        "question": question,
        "answer": answer,
    }


# ============================================================
# PATCH-ID CONVENIENCE ENTRY POINT
# ============================================================

def predict_fusion(
    model_manager,
    patch_id,
    s1_name,
    question,
    root_dir=None,
    max_new_tokens=80,
):
    """
    Convenience function for BigEarthNet-based callers.
    """

    return run_task4(
        model_manager=model_manager,
        question=question,
        patch_id=patch_id,
        s1_name=s1_name,
        root_dir=root_dir,
        max_new_tokens=max_new_tokens,
    )


# ============================================================
# UPLOADED-IMAGE CONVENIENCE ENTRY POINT
# ============================================================

def answer_fusion_question(
    model_manager,
    optical_image,
    sar_image,
    question,
    max_new_tokens=80,
):
    """
    Convenience function for frontend/API callers
    that provide two uploaded PIL images.
    """

    return run_task4(
        model_manager=model_manager,
        question=question,
        optical_image=optical_image,
        sar_image=sar_image,
        max_new_tokens=max_new_tokens,
    )
