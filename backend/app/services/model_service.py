from __future__ import annotations

import importlib.util
import math
import time
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from PIL import Image

from backend.app.config import Settings


class ModelUnavailableError(RuntimeError):
    pass


class ModelService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: Any | None = None
        self._load_error: str | None = None
        self._lock = Lock()

    def status(self) -> tuple[str, str | None]:
        if importlib.util.find_spec("ultralytics") is None:
            return "dependency_missing", "未安装机器学习依赖，请安装 requirements-ml.txt"
        if not self.settings.model_path.exists():
            return "missing", f"未找到模型权重：{self.settings.model_path}"
        if self._load_error:
            return "error", self._load_error
        return "ready", None

    def load(self) -> Any:
        state, detail = self.status()
        if state != "ready":
            raise ModelUnavailableError(detail or "模型不可用")
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from ultralytics import YOLO

                self._model = YOLO(str(self.settings.model_path))
            except Exception as exc:  # pragma: no cover - depends on local ML runtime
                self._load_error = f"模型加载失败：{exc}"
                raise ModelUnavailableError(self._load_error) from exc
        return self._model

    @property
    def model(self) -> Any:
        return self.load()

    def predict(
        self,
        image_path: Path,
        confidence: float | None = None,
        iou: float | None = None,
        image_size: int | None = None,
    ) -> dict[str, Any]:
        model = self.load()
        conf = confidence if confidence is not None else self.settings.model_confidence
        nms_iou = iou if iou is not None else self.settings.model_iou
        imgsz = image_size if image_size is not None else self.settings.model_image_size
        started = time.perf_counter()
        with self._lock:
            results = model.predict(
                source=str(image_path),
                conf=conf,
                iou=nms_iou,
                imgsz=imgsz,
                device=self.settings.model_device,
                verbose=False,
            )
        elapsed_ms = (time.perf_counter() - started) * 1000
        result = results[0]
        height, width = result.orig_shape
        detections: list[dict[str, Any]] = []
        obb = getattr(result, "obb", None)
        if obb is not None and len(obb) > 0:
            xywhr = obb.xywhr.detach().cpu().numpy()
            polygons = obb.xyxyxyxy.detach().cpu().numpy()
            confidences = obb.conf.detach().cpu().numpy()
            classes = obb.cls.detach().cpu().numpy().astype(int)
            names = result.names
            for index, (box, polygon, score, class_id) in enumerate(
                zip(xywhr, polygons, confidences, classes, strict=True)
            ):
                cx, cy, box_width, box_height, angle = [float(value) for value in box]
                detections.append(
                    {
                        "id": f"det-{index + 1}",
                        "class_id": int(class_id),
                        "class_name": str(names[int(class_id)]),
                        "confidence": float(score),
                        "box": {
                            "cx": cx,
                            "cy": cy,
                            "width": box_width,
                            "height": box_height,
                            "angle_rad": angle,
                            "angle_deg": math.degrees(angle),
                            "polygon": [
                                {"x": float(point[0]), "y": float(point[1])} for point in polygon
                            ],
                        },
                    }
                )
        return {
            "id": uuid4().hex,
            "image_width": width,
            "image_height": height,
            "elapsed_ms": round(elapsed_ms, 2),
            "model_name": self.settings.model_path.name,
            "thresholds": {"confidence": conf, "iou": nms_iou},
            "detections": detections,
        }


def image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size
