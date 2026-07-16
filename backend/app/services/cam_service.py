from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
from PIL import Image

from backend.app.services.model_service import ModelService


def _first_tensor(value: Any) -> Any | None:
    if hasattr(value, "ndim") and value.ndim == 4:
        return value
    if isinstance(value, list | tuple):
        for item in value:
            tensor = _first_tensor(item)
            if tensor is not None:
                return tensor
    if isinstance(value, dict):
        for item in value.values():
            tensor = _first_tensor(item)
            if tensor is not None:
                return tensor
    return None


class CamService:
    def __init__(self, model_service: ModelService) -> None:
        self.model_service = model_service
        self._lock = Lock()

    def generate(
        self, source: Path, destination: Path, layer_index: int = -2, opacity: float = 0.48
    ) -> Path:
        model = self.model_service.model
        layers = list(model.model.model)
        if not layers:
            raise RuntimeError("无法读取模型特征层")
        if not -len(layers) <= layer_index < len(layers):
            raise ValueError(f"特征层索引超出范围：{layer_index}")
        captured: dict[str, Any] = {}

        def hook(_module: Any, _inputs: Any, output: Any) -> None:
            tensor = _first_tensor(output)
            if tensor is not None:
                captured["activation"] = tensor.detach().float().cpu()

        with self._lock:
            handle = layers[layer_index].register_forward_hook(hook)
            try:
                self.model_service.predict(source, confidence=0.01)
            finally:
                handle.remove()

        activation = captured.get("activation")
        if activation is None:
            raise RuntimeError("指定特征层没有产生二维特征图，请尝试调整 layer_index")
        feature = activation[0].numpy().transpose(1, 2, 0)
        matrix = feature.reshape(-1, feature.shape[-1])
        matrix -= matrix.mean(axis=0, keepdims=True)
        _, _, components = np.linalg.svd(matrix, full_matrices=False)
        cam = matrix @ components[0]
        cam = cam.reshape(feature.shape[:2])
        if cam.mean() < 0:
            cam = -cam
        cam = np.maximum(cam, 0)
        low, high = np.percentile(cam, [1, 99])
        cam = np.clip((cam - low) / max(high - low, 1e-8), 0, 1)

        with Image.open(source) as source_image:
            base = source_image.convert("RGB")
        heat = Image.fromarray(_colorize(cam), mode="RGB").resize(
            base.size, Image.Resampling.BILINEAR
        )
        mask = Image.fromarray((cam * 255).astype(np.uint8), mode="L").resize(
            base.size, Image.Resampling.BILINEAR
        )
        alpha = mask.point(lambda value: int(value * opacity))
        result = Image.composite(heat, base, alpha)
        destination.parent.mkdir(parents=True, exist_ok=True)
        result.save(destination, quality=92)
        return destination


def _colorize(cam: np.ndarray) -> np.ndarray:
    """Compact blue-cyan-yellow-red heatmap without an OpenCV dependency."""
    x = np.clip(cam, 0, 1)
    red = np.clip(1.8 * x - 0.35, 0, 1)
    green = np.clip(1.7 - np.abs(3.2 * x - 1.7), 0, 1)
    blue = np.clip(1.25 - 2.1 * x, 0, 1)
    return (np.stack([red, green, blue], axis=-1) * 255).astype(np.uint8)
