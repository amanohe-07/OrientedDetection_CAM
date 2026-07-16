from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Point(BaseModel):
    x: float
    y: float


class OrientedBox(BaseModel):
    cx: float
    cy: float
    width: float
    height: float
    angle_rad: float
    angle_deg: float
    polygon: list[Point]


class Detection(BaseModel):
    id: str
    class_id: int
    class_name: str
    confidence: float
    box: OrientedBox


class InferenceResponse(BaseModel):
    id: str
    created_at: datetime
    image_url: str
    image_width: int
    image_height: int
    elapsed_ms: float
    model_name: str
    thresholds: dict[str, float]
    detections: list[Detection]


class SystemStatus(BaseModel):
    api: Literal["ready"] = "ready"
    model_state: Literal["ready", "missing", "dependency_missing", "error"]
    model_path: str
    dataset_ready: bool
    dataset_config: str
    device: str
    details: str | None = None


class EvaluationRequest(BaseModel):
    data_config: str | None = None
    split: Literal["train", "val", "test"] = "val"
    confidence: float = Field(default=0.25, ge=0, le=1)
    match_iou: float = Field(default=0.5, gt=0, le=1)
    image_size: int = Field(default=640, ge=256, le=2048)


class EvaluationJob(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    created_at: datetime
    finished_at: datetime | None = None
    metrics: dict[str, float | int] = Field(default_factory=dict)


class SampleRecord(BaseModel):
    id: str
    evaluation_id: str
    filename: str
    error_type: Literal["TP", "FP", "FN", "MIXED"]
    gt_count: int
    prediction_count: int
    tp_count: int
    fp_count: int
    fn_count: int
    mean_confidence: float
    source_path: str
    image_url: str
    overlay_url: str
    cam_url: str | None = None
    analysis: dict[str, str | bool | list[str]] = Field(default_factory=dict)


class SampleAnalysis(BaseModel):
    attention_on_target: bool | None = None
    background_interference: bool | None = None
    missed_key_features: bool | None = None
    causes: list[str] = Field(default_factory=list)
    conclusion: str = ""
    improvement: str = ""


class CamRequest(BaseModel):
    layer_index: int = -2
    opacity: float = Field(default=0.48, ge=0.1, le=0.9)
