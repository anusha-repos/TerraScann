
"""
SatQuery AI — Task 3: Change Detection

Backend inference module.

Task 3 input:
    - BEFORE image
    - AFTER image
    - question

Task 3 output:
    - generated change-detection answer

The base GeoChat-7B model and Task 3 LoRA adapter
are managed by ModelManager.

This file contains only backend inference logic.
Training and evaluation remain in their respective files.
"""

import torch

from PIL import Image
from typing import Any, Dict

# Import geochat_loader first so that its GeoChat repository
# path setup is performed before importing GeoChat components.
import geochat_loader

from geochat_loader import (
    process_images,
    tokenizer_image_token,
    IMAGE_TOKEN_INDEX,
)


# ---------------------------------------------------------------------
# INFERENCE DTYPE
# ---------------------------------------------------------------------

# GeoChat is loaded in 4-bit mode.
#
# IMPORTANT:
# Quantized weight dtype must NOT be used as the attention
# computation dtype.
#
# In particular, do NOT use:
#
#     module.weight.dtype
#
# for Q/K/V outputs because quantized weights may be uint8.
#
# FP16 is the computation dtype used by the tested Task 3 pipeline.

ATTENTION_COMPUTE_DTYPE = torch.float16


# ---------------------------------------------------------------------
# DTYPE COMPATIBILITY HOOKS
# ---------------------------------------------------------------------

def register_dtype_compatibility_hooks(model) -> None:
    """
    Register the dtype fixes required by the Task 3
    4-bit GeoChat inference path.

    Q/K/V projection outputs are forced to FP16.

    lm_head inputs are also kept in a safe floating-point
    computation dtype.

    Hooks are registered only once per model instance.
    """

    # -------------------------------------------------------------
    # Prevent duplicate hook registration.
    # -------------------------------------------------------------

    if getattr(
        model,
        "_satquery_task3_dtype_hooks_registered",
        False,
    ):
        return

    # -------------------------------------------------------------
    # Q/K/V projection output hook
    # -------------------------------------------------------------

    def cast_attention_projection_output(
        module,
        inputs,
        output,
    ):
        """
        Keep attention projection outputs in FP16.

        Never use module.weight.dtype here.
        """

        if output is None:
            return output

        target_dtype = ATTENTION_COMPUTE_DTYPE

        if torch.is_tensor(output):

            if output.dtype != target_dtype:
                return output.to(dtype=target_dtype)

            return output

        if isinstance(output, tuple):

            converted = []

            for value in output:

                if (
                    torch.is_tensor(value)
                    and value.dtype != target_dtype
                ):
                    value = value.to(
                        dtype=target_dtype
                    )

                converted.append(value)

            return tuple(converted)

        return output

    attention_hook_count = 0

    # -------------------------------------------------------------
    # Find Q/K/V projection modules.
    # -------------------------------------------------------------

    for name, module in model.named_modules():

        if name.endswith("self_attn.q_proj"):

            module.register_forward_hook(
                cast_attention_projection_output
            )

            attention_hook_count += 1

        elif name.endswith("self_attn.k_proj"):

            module.register_forward_hook(
                cast_attention_projection_output
            )

            attention_hook_count += 1

        elif name.endswith("self_attn.v_proj"):

            module.register_forward_hook(
                cast_attention_projection_output
            )

            attention_hook_count += 1

    print(
        f"✓ Registered {attention_hook_count} "
        "Q/K/V FP16 hooks."
    )

    # -------------------------------------------------------------
    # Locate lm_head.
    # -------------------------------------------------------------

    base_model = None

    try:
        base_model = model.get_base_model()
    except Exception:
        base_model = None

    lm_head = None

    if base_model is not None:

        lm_head = getattr(
            base_model,
            "lm_head",
            None,
        )

    if lm_head is None:

        lm_head = getattr(
            model,
            "lm_head",
            None,
        )

    if lm_head is None:

        print(
            "⚠ Could not locate lm_head. "
            "Continuing without lm_head hook."
        )

        model._satquery_task3_dtype_hooks_registered = True
        return

    # -------------------------------------------------------------
    # Determine safe lm_head computation dtype.
    # -------------------------------------------------------------

    lm_head_dtype = None

    if hasattr(lm_head, "weight"):

        weight_dtype = lm_head.weight.dtype

        floating_dtypes = {
            torch.float16,
            torch.float32,
            torch.bfloat16,
        }

        if weight_dtype in floating_dtypes:

            lm_head_dtype = weight_dtype

        else:

            # Quantized/integer weight.
            #
            # Never cast hidden states to Byte.

            lm_head_dtype = (
                ATTENTION_COMPUTE_DTYPE
            )

    if lm_head_dtype is None:

        lm_head_dtype = (
            ATTENTION_COMPUTE_DTYPE
        )

    # -------------------------------------------------------------
    # lm_head input hook.
    # -------------------------------------------------------------

    def cast_lm_head_input(
        module,
        inputs,
    ):

        if not inputs:
            return inputs

        hidden_states = inputs[0]

        if not torch.is_tensor(
            hidden_states
        ):
            return inputs

        if (
            hidden_states.dtype
            != lm_head_dtype
        ):

            hidden_states = hidden_states.to(
                dtype=lm_head_dtype
            )

        return (
            hidden_states,
            *inputs[1:],
        )

    lm_head.register_forward_pre_hook(
        cast_lm_head_input
    )

    print(
        "✓ Registered lm_head "
        f"dtype hook → {lm_head_dtype}."
    )

    model._satquery_task3_dtype_hooks_registered = True


# ---------------------------------------------------------------------
# IMAGE VALIDATION
# ---------------------------------------------------------------------

def validate_change_images(
    before_image: Image.Image,
    after_image: Image.Image,
) -> None:
    """
    Validate the two images supplied to Task 3.
    """

    if not isinstance(
        before_image,
        Image.Image,
    ):
        raise TypeError(
            "before_image must be a PIL Image."
        )

    if not isinstance(
        after_image,
        Image.Image,
    ):
        raise TypeError(
            "after_image must be a PIL Image."
        )


# ---------------------------------------------------------------------
# IMAGE PROCESSING
# ---------------------------------------------------------------------

def prepare_change_images(
    before_image: Image.Image,
    after_image: Image.Image,
    image_processor,
    model,
):
    """
    Process BEFORE and AFTER images using GeoChat's
    existing image-processing pipeline.

    Returns:

        [2, C, H, W]
    """

    validate_change_images(
        before_image,
        after_image,
    )

    # Make image dimensions identical.

    if (
        before_image.size
        != after_image.size
    ):

        after_image = after_image.resize(
            before_image.size,
            Image.Resampling.BILINEAR,
        )

    image_tensor = process_images(
        [
            before_image,
            after_image,
        ],
        image_processor,
        model.config,
    )

    if image_tensor.ndim != 4:

        raise RuntimeError(
            "Expected processed Task 3 image tensor "
            "[2,C,H,W], got "
            f"{tuple(image_tensor.shape)}"
        )

    if image_tensor.shape[0] != 2:

        raise RuntimeError(
            "Task 3 requires exactly two images "
            "(before + after), got "
            f"{image_tensor.shape[0]}"
        )

    return image_tensor


# ---------------------------------------------------------------------
# GENERATION
# ---------------------------------------------------------------------

def generate_change_answer(
    tokenizer,
    model,
    image_processor,
    before_image: Image.Image,
    after_image: Image.Image,
    question: str,
    max_new_tokens: int = 20,
) -> str:
    """
    Generate a Task 3 change-detection answer.

    GeoChat receives:

        one <image> token
        +
        two processed images

    The two images represent:

        image 0 = BEFORE
        image 1 = AFTER
    """

    # -------------------------------------------------------------
    # Question validation.
    # -------------------------------------------------------------

    if question is None:

        raise ValueError(
            "Task 3 question cannot be None."
        )

    question = str(question).strip()

    if not question:

        raise ValueError(
            "Task 3 question cannot be empty."
        )

    # -------------------------------------------------------------
    # Make sure dtype hooks are active.
    # -------------------------------------------------------------

    register_dtype_compatibility_hooks(
        model
    )

    # -------------------------------------------------------------
    # Process BEFORE + AFTER.
    # -------------------------------------------------------------

    image_tensor = prepare_change_images(
        before_image=before_image,
        after_image=after_image,
        image_processor=image_processor,
        model=model,
    )

    # -------------------------------------------------------------
    # Task 3 prompt.
    #
    # IMPORTANT:
    # Exactly ONE <image> token.
    #
    # The image tensor itself contains two images.
    # -------------------------------------------------------------

    prompt = (
        "<image>\n"
        "The left image is the BEFORE scene and "
        "the right image is the AFTER scene. "
        f"{question}"
    )

    input_ids = tokenizer_image_token(
        prompt,
        tokenizer,
        IMAGE_TOKEN_INDEX,
        return_tensors="pt",
    )

    # -------------------------------------------------------------
    # Verify exactly one image token.
    # -------------------------------------------------------------

    image_token_count = (
        input_ids == IMAGE_TOKEN_INDEX
    ).sum().item()

    if image_token_count != 1:

        raise RuntimeError(
            "Expected exactly ONE <image> token "
            "for the before/after pair, "
            f"but found {image_token_count}."
        )

    # -------------------------------------------------------------
    # Add batch dimension.
    # -------------------------------------------------------------

    input_ids = input_ids.unsqueeze(0)

    image_tensor = image_tensor.unsqueeze(0)

    # Expected:
    #
    # input_ids:
    #     [1, sequence_length]
    #
    # images:
    #     [1, 2, C, H, W]

    if image_tensor.ndim != 5:

        raise RuntimeError(
            "Expected Task 3 image tensor "
            "[1,2,C,H,W], got "
            f"{tuple(image_tensor.shape)}"
        )

    if image_tensor.shape[1] != 2:

        raise RuntimeError(
            "Expected exactly two images "
            "for Task 3, got shape "
            f"{tuple(image_tensor.shape)}"
        )

    # -------------------------------------------------------------
    # Device.
    # -------------------------------------------------------------

    try:

        device = next(
            model.parameters()
        ).device

    except StopIteration:

        device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

    input_ids = input_ids.to(device)

    image_tensor = image_tensor.to(device)

    # -------------------------------------------------------------
    # Image dtype.
    # -------------------------------------------------------------

    if not image_tensor.is_floating_point():

        image_tensor = image_tensor.float()

    if (
        image_tensor.device.type == "cuda"
        and image_tensor.dtype != torch.float16
    ):

        image_tensor = image_tensor.to(
            dtype=torch.float16
        )

    # -------------------------------------------------------------
    # Generate.
    # -------------------------------------------------------------

    with torch.inference_mode():

        output_ids = model.generate(
            input_ids=input_ids,
            images=image_tensor,
            do_sample=False,
            max_new_tokens=max_new_tokens,
            use_cache=True,
        )

    # -------------------------------------------------------------
    # Remove prompt tokens.
    # -------------------------------------------------------------

    generated_ids = output_ids[
        0,
        input_ids.shape[1]:,
    ]

    # -------------------------------------------------------------
    # Decode.
    # -------------------------------------------------------------

    prediction = tokenizer.decode(
        generated_ids,
        skip_special_tokens=True,
    )

    return prediction.strip()


# ---------------------------------------------------------------------
# BACKEND ENTRY POINT
# ---------------------------------------------------------------------

def run_task3(
    model_manager,
    before_image: Image.Image,
    after_image: Image.Image,
    question: str,
    max_new_tokens: int = 20,
) -> Dict[str, Any]:
    """
    Main backend interface for Task 3.

    Parameters
    ----------
    model_manager:
        Shared SatQuery ModelManager instance.

    before_image:
        BEFORE-event PIL image.

    after_image:
        AFTER-event PIL image.

    question:
        User's change-detection question.

    Returns
    -------
    Dictionary suitable for the response builder/router.
    """

    if before_image is None:

        raise ValueError(
            "Task 3 requires a BEFORE image."
        )

    if after_image is None:

        raise ValueError(
            "Task 3 requires an AFTER image."
        )

    if question is None:

        raise ValueError(
            "Task 3 question cannot be None."
        )

    question = str(question).strip()

    if not question:

        raise ValueError(
            "Task 3 question cannot be empty."
        )

    # -------------------------------------------------------------
    # Load the Task 3 adapter through the shared model manager.
    # -------------------------------------------------------------

    model = model_manager.get_model(
        "task3"
    )

    tokenizer = (
        model_manager.get_tokenizer()
    )

    image_processor = (
        model_manager.get_image_processor()
    )

    # -------------------------------------------------------------
    # Register Task 3-specific dtype compatibility.
    # -------------------------------------------------------------

    register_dtype_compatibility_hooks(
        model
    )

    # -------------------------------------------------------------
    # Generate answer.
    # -------------------------------------------------------------

    answer = generate_change_answer(
        tokenizer=tokenizer,
        model=model,
        image_processor=image_processor,
        before_image=before_image,
        after_image=after_image,
        question=question,
        max_new_tokens=max_new_tokens,
    )

    # -------------------------------------------------------------
    # Backend response.
    # -------------------------------------------------------------

    return {
        "task": "task3_change_detection",
        "question": question,
        "answer": answer,
    }


# ---------------------------------------------------------------------
# OPTIONAL ALIAS
# ---------------------------------------------------------------------

def predict_change(
    model_manager,
    before_image: Image.Image,
    after_image: Image.Image,
    question: str,
    max_new_tokens: int = 20,
) -> Dict[str, Any]:
    """
    Alias for run_task3().

    Useful when the router uses a generic
    predict_* naming convention.
    """

    return run_task3(
        model_manager=model_manager,
        before_image=before_image,
        after_image=after_image,
        question=question,
        max_new_tokens=max_new_tokens,
    )

