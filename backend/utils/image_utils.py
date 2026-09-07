
import os

from PIL import Image


# ============================================================
# IMAGE VALIDATION
# ============================================================

def validate_image_path(image_path: str) -> str:
    """
    Validate that an image path exists and points to a file.
    """

    if not image_path:
        raise ValueError("Image path cannot be empty.")

    if not os.path.isfile(image_path):
        raise FileNotFoundError(
            f"Image file not found:\n{image_path}"
        )

    return image_path


# ============================================================
# LOAD IMAGE
# ============================================================

def load_image(image_path: str) -> Image.Image:
    """
    Load an image and convert it to RGB.
    """

    validate_image_path(image_path)

    image = Image.open(image_path)

    return image.convert("RGB")


# ============================================================
# LOAD MULTIPLE IMAGES
# ============================================================

def load_images(image_paths):
    """
    Load multiple images and convert them to RGB.

    Parameters
    ----------
    image_paths : list[str]
        List of image file paths.

    Returns
    -------
    list[PIL.Image.Image]
        Loaded RGB images.
    """

    if not image_paths:
        raise ValueError("No image paths provided.")

    return [
        load_image(image_path)
        for image_path in image_paths
    ]


# ============================================================
# VALIDATE IMAGE OBJECT
# ============================================================

def validate_image(image) -> Image.Image:
    """
    Validate an already-loaded PIL image and convert it to RGB.
    """

    if not isinstance(image, Image.Image):
        raise TypeError(
            "Expected a PIL.Image.Image object."
        )

    return image.convert("RGB")


# ============================================================
# IMAGE DIMENSIONS
# ============================================================

def get_image_size(image) -> tuple:
    """
    Return image dimensions as (width, height).
    """

    image = validate_image(image)

    return image.size
