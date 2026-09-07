
import re


# ============================================================
# PROMPT HELPERS
# ============================================================

def build_geochat_prompt(question: str) -> str:
    """
    Build the standard GeoChat prompt for a single image.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    return (
        f"USER: <image>\n"
        f"{question.strip()}\n"
        f"ASSISTANT:"
    )


def build_geochat_pair_prompt(question: str) -> str:
    """
    Build the GeoChat prompt for a pre/post image pair.

    GeoChat's pair-image handling expects one <image> token
    for the image pair.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    return (
        f"USER: <image>\n"
        f"{question.strip()}\n"
        f"ASSISTANT:"
    )


# ============================================================
# ANSWER CLEANING
# ============================================================

def clean_geochat_answer(answer: str) -> str:
    """
    Clean the text returned by GeoChat.
    """

    if answer is None:
        return ""

    answer = str(answer).strip()

    # Remove accidental assistant prefixes.
    answer = re.sub(
        r"^\s*ASSISTANT\s*:\s*",
        "",
        answer,
        flags=re.IGNORECASE,
    )

    # Remove surrounding whitespace.
    answer = answer.strip()

    return answer


# ============================================================
# ANSWER NORMALIZATION
# ============================================================

def normalize_geochat_answer(answer: str) -> str:
    """
    Normalize a GeoChat answer for downstream processing.
    """

    answer = clean_geochat_answer(answer)

    # Normalize repeated whitespace.
    answer = re.sub(
        r"\s+",
        " ",
        answer,
    )

    return answer.strip()


# ============================================================
# GROUNDING BOX PARSING
# ============================================================

def parse_grounding_boxes(text: str):
    """
    Extract GeoChat grounding boxes from generated text.

    Returns a list of:
        {
            "box": [x1, y1, x2, y2],
            "label": "..."
        }
    """

    if not text:
        return []

    results = []

    pattern = re.compile(
        r"<box>\s*"
        r"(\d+)\s*,\s*"
        r"(\d+)\s*,\s*"
        r"(\d+)\s*,\s*"
        r"(\d+)"
        r"\s*</box>"
        r"(?:\s*([^<\n]+))?",
        re.IGNORECASE,
    )

    for match in pattern.finditer(text):

        x1, y1, x2, y2 = map(
            int,
            match.group(1, 2, 3, 4),
        )

        label = (
            match.group(5).strip()
            if match.group(5)
            else ""
        )

        results.append(
            {
                "box": [
                    x1,
                    y1,
                    x2,
                    y2,
                ],
                "label": label,
            }
        )

    return results


# ============================================================
# RESPONSE TYPE HELPERS
# ============================================================

def is_empty_answer(answer: str) -> bool:
    """
    Check whether GeoChat returned an empty answer.
    """

    return not bool(
        clean_geochat_answer(answer)
    )


def answer_to_string(answer) -> str:
    """
    Safely convert a GeoChat response to a string.
    """

    if answer is None:
        return ""

    if isinstance(answer, str):
        return answer.strip()

    return str(answer).strip()
