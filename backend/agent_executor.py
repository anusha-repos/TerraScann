from typing import Any, Dict, Optional

from agent_router import route_request
from model_manager import model_manager


class AgentExecutor:
    """Single execution boundary for routed SatQuery inference."""

    def execute(
        self,
        task: str,
        question: str,
        image: Any = None,
        input_mode: str = "dual_sensor",
        patch_id: Optional[str] = None,
        patch_id_s1: Optional[str] = None,
        before_image: Any = None,
        after_image: Any = None,
        optical_image: Any = None,
        sar_image: Any = None,
        s1_name: Optional[str] = None,
        root_dir: Optional[str] = None,
        max_new_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:

        if task is None or not str(task).strip():
            raise ValueError("Task must be provided.")

        if question is None or not str(question).strip():
            raise ValueError("Question must be provided.")

        with model_manager.inference_lock:
            return route_request(
                task=str(task).strip().lower(),
                question=str(question).strip(),
                image=image,
                input_mode=input_mode,
                patch_id=patch_id,
                patch_id_s1=patch_id_s1,
                before_image=before_image,
                after_image=after_image,
                optical_image=optical_image,
                sar_image=sar_image,
                s1_name=s1_name,
                root_dir=root_dir,
                max_new_tokens=max_new_tokens,
            )


agent_executor = AgentExecutor()


def execute_request(**kwargs):
    return agent_executor.execute(**kwargs)
