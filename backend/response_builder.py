"""
SatQuery AI — Response Builder

Converts internal task results into a consistent API response.

The task modules remain responsible for inference.
The router remains responsible for routing.
The executor remains responsible for execution.

This module is responsible only for response formatting.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


class ResponseBuilder:
    """
    Builds consistent responses for the SatQuery API.
    """

    @staticmethod
    def _clean_answer(answer: Any) -> str:
        """
        Convert the model answer into a clean string.
        """

        if answer is None:
            return ""

        return str(answer).strip()

    @staticmethod
    def build_success(
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a successful API response.

        The original task result is preserved so that task-specific
        information is not lost.
        """

        if not isinstance(result, dict):
            raise TypeError(
                "Task result must be a dictionary."
            )

        response = dict(result)

        answer = ResponseBuilder._clean_answer(
            response.get("answer")
        )

        response["answer"] = answer
        response["status"] = "success"

        return response

    @staticmethod
    def build_error(
        message: str,
        error_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a consistent error response.
        """

        message = str(message).strip()

        response = {
            "status": "error",
            "answer": "",
            "error": message,
        }

        if error_type:
            response["error_type"] = str(
                error_type
            )

        return response

    @staticmethod
    def build_health(
        model_loaded: bool,
        active_adapter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build the backend health response.
        """

        return {
            "status": "ok",
            "service": "SatQuery AI",
            "model_loaded": bool(model_loaded),
            "active_adapter": active_adapter,
        }


def build_response(
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Public helper for successful task responses.
    """

    return ResponseBuilder.build_success(result)


def build_error_response(
    message: str,
    error_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Public helper for error responses.
    """

    return ResponseBuilder.build_error(
        message=message,
        error_type=error_type,
    )
