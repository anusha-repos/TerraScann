import os
import threading
from typing import Optional

import torch
from peft import PeftModel

import geochat_loader
from config import (
    GEOCHAT_MODEL_PATH,
    TASK12_ADAPTER_PATH,
    TASK3_ADAPTER_PATH,
    TASK4_ADAPTER_PATH,
    DEVICE,
)


class ModelManager:
    """Single shared GeoChat model + named task adapters."""

    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.image_processor = None
        self.context_len = None
        self.loaded_adapter: Optional[str] = None

        self.adapter_paths = {
            "task12": TASK12_ADAPTER_PATH,
            "task3": TASK3_ADAPTER_PATH,
            "task4": TASK4_ADAPTER_PATH,
        }

        # Adapter switching changes shared model state.
        # This lock must cover the entire inference request.
        self.inference_lock = threading.RLock()
        self._load_lock = threading.RLock()

    def load_base_model(self):
        with self._load_lock:
            if self.model is not None:
                return

            if not os.path.isdir(GEOCHAT_MODEL_PATH):
                raise RuntimeError(
                    f"GeoChat model directory not found: {GEOCHAT_MODEL_PATH}"
                )

            (
                self.tokenizer,
                self.model,
                self.image_processor,
                self.context_len,
            ) = geochat_loader.load_geochat_model(
                model_path=GEOCHAT_MODEL_PATH,
                load_4bit=True,
                load_8bit=False,
            )

            self.model.eval()

    def _validate_adapter(self, task_name: str):
        if task_name not in self.adapter_paths:
            raise ValueError(
                f"Unknown task: {task_name}. "
                f"Expected: {sorted(self.adapter_paths)}"
            )

        adapter_path = self.adapter_paths[task_name]

        if not os.path.isdir(adapter_path):
            raise RuntimeError(
                f"LoRA adapter directory not found for {task_name}: {adapter_path}"
            )

        if not os.path.isfile(os.path.join(adapter_path, "adapter_config.json")):
            raise RuntimeError(
                f"adapter_config.json not found in {adapter_path}"
            )

        return adapter_path

    def load_adapter(self, task_name: str):
        with self._load_lock:
            self.load_base_model()
            adapter_path = self._validate_adapter(task_name)

            if self.loaded_adapter == task_name:
                return self.model

            adapter_name = task_name

            if not isinstance(self.model, PeftModel):
                self.model = PeftModel.from_pretrained(
                    self.model,
                    adapter_path,
                    adapter_name=adapter_name,
                    is_trainable=False,
                )
            else:
                existing = getattr(self.model, "peft_config", {})
                if adapter_name not in existing:
                    self.model.load_adapter(
                        adapter_path,
                        adapter_name=adapter_name,
                        is_trainable=False,
                    )

            registered = getattr(self.model, "peft_config", {})
            if adapter_name not in registered:
                raise RuntimeError(
                    f"Adapter '{adapter_name}' failed to register."
                )

            self.model.set_adapter(adapter_name)
            self.model.eval()
            self.loaded_adapter = task_name
            return self.model

    def get_model(self, task_name: str):
        return self.load_adapter(task_name)

    def get_tokenizer(self):
        self.load_base_model()
        return self.tokenizer

    def get_image_processor(self):
        self.load_base_model()
        return self.image_processor

    def get_context_length(self):
        self.load_base_model()
        return self.context_len

    def get_active_adapter(self):
        return self.loaded_adapter

    def get_device(self):
        if self.model is None:
            self.load_base_model()
        try:
            return next(self.model.parameters()).device
        except StopIteration:
            return torch.device(DEVICE)


model_manager = ModelManager()
