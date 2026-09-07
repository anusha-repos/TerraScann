import torch
import numpy as np
from PIL import Image

from bigearthnet_data import (
    load_s1_image,
    load_s2_image,
    make_dual_sensor_image,
)
from geochat_loader import (
    process_images,
    tokenizer_image_token,
    IMAGE_TOKEN_INDEX,
    build_prompt,
)


SUPPORTED_INPUT_MODES = {
    "single_optical",
    "single_sar",
    "dual_sensor",
}


def load_task12_image(
    input_mode,
    image=None,
    patch_id=None,
    patch_id_s1=None,
):
    if image is not None:
        return image

    if input_mode == "single_optical":
        if not patch_id:
            raise ValueError("patch_id is required for single_optical input.")
        return load_s2_image(patch_id)

    if input_mode == "single_sar":
        if not patch_id_s1:
            raise ValueError("patch_id_s1 is required for single_sar input.")
        return load_s1_image(patch_id_s1)

    if input_mode == "dual_sensor":
        if not patch_id or not patch_id_s1:
            raise ValueError(
                "patch_id and patch_id_s1 are required for dual_sensor input."
            )
        return make_dual_sensor_image(patch_id, patch_id_s1)

    raise ValueError(
        f"Unsupported Task 1/2 input mode: {input_mode}"
    )


def generate_task12_answer(
    tokenizer,
    model,
    image_processor,
    image,
    question,
    max_new_tokens=128,
):
    question = str(question).strip()
    if not question:
        raise ValueError("Task 1/2 question cannot be empty.")

    prompt = build_prompt(question)

    # GeoChat process_images expects PIL images.
    if isinstance(image, np.ndarray):
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        image = Image.fromarray(image)

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


def run_task12(
    model_manager,
    question,
    image=None,
    input_mode="dual_sensor",
    patch_id=None,
    patch_id_s1=None,
    max_new_tokens=128,
):
    question = str(question).strip()
    if not question:
        raise ValueError("Task 1/2 question cannot be empty.")

    if input_mode not in SUPPORTED_INPUT_MODES:
        raise ValueError(
            f"Unsupported Task 1/2 input mode: {input_mode}"
        )

    resolved_image = load_task12_image(
        input_mode=input_mode,
        image=image,
        patch_id=patch_id,
        patch_id_s1=patch_id_s1,
    )

    model = model_manager.get_model("task12")
    tokenizer = model_manager.get_tokenizer()
    image_processor = model_manager.get_image_processor()

    answer = generate_task12_answer(
        tokenizer=tokenizer,
        model=model,
        image_processor=image_processor,
        image=resolved_image,
        question=question,
        max_new_tokens=max_new_tokens,
    )

    return {
        "task": "task12",
        "input_mode": input_mode,
        "question": question,
        "answer": answer,
    }


def answer_question(
    model_manager,
    question,
    image,
    max_new_tokens=128,
):
    return run_task12(
        model_manager=model_manager,
        question=question,
        image=image,
        input_mode="dual_sensor",
        max_new_tokens=max_new_tokens,
    )
