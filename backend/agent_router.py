
"""
SatQuery AI — Agent Router

Single routing layer for all SatQuery tasks.

Flow:

    User Request
         ↓
    AgentRouter
         ↓
    ┌──────────┬──────────┬──────────┐
    │ Task 1/2 │  Task 3  │  Task 4  │
    │   VQA    │  Change  │  Fusion  │
    └──────────┴──────────┴──────────┘
         ↓
    ModelManager
         ↓
    GeoChat-7B + correct LoRA
"""

from typing import Any, Dict, Optional

from model_manager import model_manager

from tasks.task12_vqa import run_task12
from tasks.task3_change import run_task3
from tasks.task4_fusion import run_task4


class AgentRouter:
    """
    Routes incoming requests to the correct SatQuery task.

    Supported tasks:

        task12
            Task 1 / Task 2 VQA

        task3
            Change Detection

        task4
            Optical + SAR Fusion
    """

    SUPPORTED_TASKS = {
        "task12",
        "task3",
        "task4",
    }

    SUPPORTED_TASK12_MODES = {
        "single_optical",
        "single_sar",
        "dual_sensor",
    }

    def __init__(self, manager=None):
        self.model_manager = (
            manager
            if manager is not None
            else model_manager
        )

    # ========================================================
    # TASK VALIDATION
    # ========================================================

    def validate_task(
        self,
        task: str,
    ) -> str:
        """
        Validate and normalize the requested task.
        """

        if task is None:
            raise ValueError(
                "Task must be provided."
            )

        task = str(
            task
        ).strip().lower()

        if task not in self.SUPPORTED_TASKS:
            raise ValueError(
                f"Unsupported task: {task}. "
                f"Expected one of: "
                f"{sorted(self.SUPPORTED_TASKS)}"
            )

        return task

    # ========================================================
    # TASK 1 / 2 INPUT MODE VALIDATION
    # ========================================================

    def validate_task12_input_mode(
        self,
        input_mode: str,
    ) -> str:
        """
        Validate Task 1/2 input mode.

        Supported modes:

            single_optical
            single_sar
            dual_sensor
        """

        if input_mode is None:
            raise ValueError(
                "Task 1/2 input_mode must be provided."
            )

        input_mode = str(
            input_mode
        ).strip().lower()

        if input_mode not in self.SUPPORTED_TASK12_MODES:
            raise ValueError(
                f"Unsupported Task 1/2 input mode: "
                f"{input_mode}. "
                f"Expected one of: "
                f"{sorted(self.SUPPORTED_TASK12_MODES)}"
            )

        return input_mode

    # ========================================================
    # MAIN ROUTING FUNCTION
    # ========================================================

    def route(
        self,
        task: str,
        question: str,

        # ----------------------------------------------------
        # Task 1 / 2
        # ----------------------------------------------------

        image: Any = None,
        input_mode: str = "dual_sensor",
        patch_id: Optional[str] = None,
        patch_id_s1: Optional[str] = None,

        # ----------------------------------------------------
        # Task 3
        # ----------------------------------------------------

        before_image: Any = None,
        after_image: Any = None,

        # ----------------------------------------------------
        # Task 4
        # ----------------------------------------------------

        optical_image: Any = None,
        sar_image: Any = None,
        s1_name: Optional[str] = None,
        root_dir: Optional[str] = None,

        # ----------------------------------------------------
        # Generation
        # ----------------------------------------------------

        max_new_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Route one request to the appropriate SatQuery task.

        Task 1/2:
            image
            OR BigEarthNet patch IDs.

        Task 3:
            before_image + after_image.

        Task 4:
            optical_image + sar_image
            OR patch_id + s1_name.
        """

        task = self.validate_task(task)
        question = str(question).strip()
        if not question:
            raise ValueError("Question cannot be empty.")

        # ====================================================
        # TASK 1 / 2 — VQA
        # ====================================================

        if task == "task12":

            input_mode = (
                self.validate_task12_input_mode(
                    input_mode
                )
            )

            kwargs = {
                "model_manager": self.model_manager,
                "question": question,
                "image": image,
                "input_mode": input_mode,
                "patch_id": patch_id,
                "patch_id_s1": patch_id_s1,
            }

            if max_new_tokens is not None:
                kwargs["max_new_tokens"] = (
                    max_new_tokens
                )

            return run_task12(**kwargs)

        # ====================================================
        # TASK 3 — CHANGE DETECTION
        # ====================================================

        if task == "task3":

            if before_image is None:
                raise ValueError(
                    "Task 3 requires before_image."
                )

            if after_image is None:
                raise ValueError(
                    "Task 3 requires after_image."
                )

            kwargs = {
                "model_manager": self.model_manager,
                "before_image": before_image,
                "after_image": after_image,
                "question": question,
            }

            if max_new_tokens is not None:
                kwargs["max_new_tokens"] = (
                    max_new_tokens
                )

            return run_task3(**kwargs)

        # ====================================================
        # TASK 4 — OPTICAL + SAR FUSION
        # ====================================================

        if task == "task4":

            kwargs = {
                "model_manager": self.model_manager,
                "question": question,

                "optical_image": optical_image,
                "sar_image": sar_image,

                "patch_id": patch_id,
                "s1_name": s1_name,
                "root_dir": root_dir,
            }

            if max_new_tokens is not None:
                kwargs["max_new_tokens"] = (
                    max_new_tokens
                )

            return run_task4(**kwargs)

        # ====================================================
        # SAFETY CHECK
        # ====================================================

        raise RuntimeError(
            f"Router reached an invalid task: {task}"
        )


# ============================================================
# SINGLE GLOBAL ROUTER
# ============================================================

agent_router = AgentRouter()


# ============================================================
# SIMPLE FUNCTION API
# ============================================================

def route_request(
    task: str,
    question: str,

    # --------------------------------------------------------
    # Task 1 / 2
    # --------------------------------------------------------

    image: Any = None,
    input_mode: str = "dual_sensor",
    patch_id: Optional[str] = None,
    patch_id_s1: Optional[str] = None,

    # --------------------------------------------------------
    # Task 3
    # --------------------------------------------------------

    before_image: Any = None,
    after_image: Any = None,

    # --------------------------------------------------------
    # Task 4
    # --------------------------------------------------------

    optical_image: Any = None,
    sar_image: Any = None,
    s1_name: Optional[str] = None,
    root_dir: Optional[str] = None,

    # --------------------------------------------------------
    # Generation
    # --------------------------------------------------------

    max_new_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Convenience function for app.py and other backend callers.

    This is the main application-facing routing function.
    """

    return agent_router.route(
        task=task,
        question=question,

        # Task 1 / 2
        image=image,
        input_mode=input_mode,
        patch_id=patch_id,
        patch_id_s1=patch_id_s1,

        # Task 3
        before_image=before_image,
        after_image=after_image,

        # Task 4
        optical_image=optical_image,
        sar_image=sar_image,

        s1_name=s1_name,
        root_dir=root_dir,

        # Generation
        max_new_tokens=max_new_tokens,
    )

