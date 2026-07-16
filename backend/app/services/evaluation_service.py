from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import yaml
from PIL import Image, ImageDraw, ImageFont

from backend.app.config import Settings
from backend.app.geometry import match_detections
from backend.app.services.model_service import ModelService
from backend.app.storage import JsonStore


class EvaluationService:
    def __init__(self, settings: Settings, model_service: ModelService, store: JsonStore) -> None:
        self.settings = settings
        self.model_service = model_service
        self.store = store
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = Lock()
        self._recover_interrupted_jobs()

    def _recover_interrupted_jobs(self) -> None:
        """Persisted background jobs cannot continue after a backend restart."""
        for job in self.list_jobs():
            if job.get("status") not in {"queued", "running"}:
                continue
            job.update(
                status="failed",
                message="后端已重启，原评估任务已中断，请重新创建任务",
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
            self.store.write(Path("evaluations") / job["id"] / "job.json", job)

    def create_job(self, request: dict[str, Any]) -> dict[str, Any]:
        job_id = uuid4().hex[:12]
        job = {
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "message": "等待执行",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "metrics": {},
            "request": request,
        }
        with self._lock:
            self._jobs[job_id] = job
        self.store.write(Path("evaluations") / job_id / "job.json", job)
        return job

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            in_memory = self._jobs.get(job_id)
        if in_memory:
            return in_memory.copy()
        return self.store.read(Path("evaluations") / job_id / "job.json")

    def list_jobs(self) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        root = self.settings.artifacts_dir / "evaluations"
        for job_path in sorted(root.glob("*/job.json"), reverse=True):
            try:
                relative = job_path.resolve().relative_to(self.settings.artifacts_dir.resolve())
                job = self.store.read(relative)
                if isinstance(job, dict):
                    jobs.append(job)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        jobs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return jobs

    def run(self, job_id: str) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        try:
            self._update(job_id, status="running", progress=2, message="正在读取数据集")
            request = job["request"]
            config_path = Path(request.get("data_config") or self.settings.dataset_config).resolve()
            images = resolve_dataset_images(config_path, request.get("split", "test"))
            if not images:
                raise FileNotFoundError(f"数据集中没有找到图像：{config_path}")
            records: list[dict[str, Any]] = []
            total_tp = total_fp = total_fn = 0
            for index, image_path in enumerate(images):
                inference = self.model_service.predict(
                    image_path,
                    confidence=float(request.get("confidence", 0.25)),
                    image_size=int(request.get("image_size", 640)),
                )
                predictions = [
                    {
                        "class_id": item["class_id"],
                        "confidence": item["confidence"],
                        "polygon": [(p["x"], p["y"]) for p in item["box"]["polygon"]],
                    }
                    for item in inference["detections"]
                ]
                truth = load_yolo_obb_labels(
                    image_path, inference["image_width"], inference["image_height"]
                )
                matches, fp, fn = match_detections(
                    predictions, truth, float(request.get("match_iou", 0.5))
                )
                total_tp += len(matches)
                total_fp += len(fp)
                total_fn += len(fn)
                record = self._make_sample(job_id, image_path, predictions, truth, matches, fp, fn)
                records.append(record)
                progress = 5 + int((index + 1) / len(images) * 82)
                self._update(
                    job_id,
                    progress=progress,
                    message=f"正在分析 {index + 1}/{len(images)}",
                )

            precision = total_tp / max(total_tp + total_fp, 1)
            recall = total_tp / max(total_tp + total_fn, 1)
            metrics: dict[str, float | int] = {
                "images": len(images),
                "tp": total_tp,
                "fp": total_fp,
                "fn": total_fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(2 * precision * recall / max(precision + recall, 1e-9), 4),
            }
            self._update(job_id, progress=90, message="正在计算官方 OBB mAP")
            metrics.update(self._official_metrics(config_path, request.get("split", "test")))
            self.store.write(Path("evaluations") / job_id / "samples.json", records)
            self._update(
                job_id,
                status="completed",
                progress=100,
                message="评估完成",
                metrics=metrics,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as exc:  # pragma: no cover - exercised by integration environments
            self._update(
                job_id,
                status="failed",
                message=str(exc),
                finished_at=datetime.now(timezone.utc).isoformat(),
            )

    def samples(self, evaluation_id: str | None = None) -> list[dict[str, Any]]:
        if evaluation_id:
            return self.store.read(Path("evaluations") / evaluation_id / "samples.json", [])
        records: list[dict[str, Any]] = []
        for job in self.list_jobs():
            records.extend(self.store.read(Path("evaluations") / job["id"] / "samples.json", []))
        return records

    def save_sample(self, sample: dict[str, Any]) -> None:
        records = self.samples(sample["evaluation_id"])
        updated = [sample if item["id"] == sample["id"] else item for item in records]
        self.store.write(Path("evaluations") / sample["evaluation_id"] / "samples.json", updated)

    def _make_sample(
        self,
        job_id: str,
        source: Path,
        predictions: list[dict],
        truth: list[dict],
        matches: list[tuple[int, int, float]],
        fp: list[int],
        fn: list[int],
    ) -> dict[str, Any]:
        sample_id = f"{source.stem}-{uuid4().hex[:6]}"
        directory = self.settings.artifacts_dir / "evaluations" / job_id / "images"
        directory.mkdir(parents=True, exist_ok=True)
        image_target = directory / f"{sample_id}{source.suffix.lower()}"
        overlay_target = directory / f"{sample_id}-overlay.jpg"
        shutil.copy2(source, image_target)
        draw_overlay(source, overlay_target, truth, predictions, matches, fp, fn)
        error_type = "MIXED" if fp and fn else "FP" if fp else "FN" if fn else "TP"
        return {
            "id": sample_id,
            "evaluation_id": job_id,
            "filename": source.name,
            "error_type": error_type,
            "gt_count": len(truth),
            "prediction_count": len(predictions),
            "tp_count": len(matches),
            "fp_count": len(fp),
            "fn_count": len(fn),
            "mean_confidence": round(
                sum(item["confidence"] for item in predictions) / max(len(predictions), 1), 4
            ),
            "source_path": str(source.resolve()),
            "image_url": self._artifact_url(image_target),
            "overlay_url": self._artifact_url(overlay_target),
            "cam_url": None,
            "analysis": {},
        }

    def _official_metrics(self, config: Path, split: str) -> dict[str, float]:
        with self.model_service._lock:
            result = self.model_service.model.val(
                data=str(config),
                split=split,
                device=self.settings.model_device,
                imgsz=self.settings.model_image_size,
                plots=False,
                verbose=False,
            )
        box = getattr(result, "box", None)
        if box is None:
            return {}
        return {
            "map50": round(float(box.map50), 4),
            "map50_95": round(float(box.map), 4),
        }

    def _update(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id) or self.store.read(
                Path("evaluations") / job_id / "job.json", {}
            )
            job.update(changes)
            self._jobs[job_id] = job
        self.store.write(Path("evaluations") / job_id / "job.json", job)

    def _artifact_url(self, path: Path) -> str:
        relative = path.resolve().relative_to(self.settings.artifacts_dir.resolve())
        return "/artifacts/" + relative.as_posix()


def resolve_dataset_images(config_path: Path, split: str) -> list[Path]:
    if not config_path.exists():
        raise FileNotFoundError(f"数据配置不存在：{config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    root = Path(config.get("path", config_path.parent))
    if not root.is_absolute():
        root = (config_path.parent / root).resolve()
    source_value = config.get(split)
    if not source_value:
        raise ValueError(f"数据配置缺少 {split} 字段")
    sources = source_value if isinstance(source_value, list) else [source_value]
    images: list[Path] = []
    for source in sources:
        path = Path(source)
        if not path.is_absolute():
            path = root / path
        if path.is_dir():
            images.extend(
                item
                for item in path.rglob("*")
                if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
            )
        elif path.suffix.lower() == ".txt" and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                item = Path(line.strip())
                if not item.is_absolute():
                    item = root / item
                if item.exists():
                    images.append(item)
    return sorted(set(item.resolve() for item in images))


def load_yolo_obb_labels(image_path: Path, width: int, height: int) -> list[dict[str, Any]]:
    parts = list(image_path.parts)
    try:
        image_index = max(index for index, value in enumerate(parts) if value == "images")
        parts[image_index] = "labels"
        label_path = Path(*parts).with_suffix(".txt")
    except ValueError:
        label_path = (
            image_path.parent.parent / "labels" / image_path.parent.name / f"{image_path.stem}.txt"
        )
    if not label_path.exists():
        return []
    labels: list[dict[str, Any]] = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        values = line.split()
        if len(values) != 9:
            continue
        coordinates = [float(value) for value in values[1:]]
        labels.append(
            {
                "class_id": int(values[0]),
                "polygon": [
                    (coordinates[index] * width, coordinates[index + 1] * height)
                    for index in range(0, 8, 2)
                ],
            }
        )
    return labels


def draw_overlay(
    source: Path,
    destination: Path,
    truth: list[dict],
    predictions: list[dict],
    matches: list[tuple[int, int, float]],
    fp: list[int],
    fn: list[int],
) -> None:
    with Image.open(source) as image:
        canvas = image.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    matched_predictions = {item[0] for item in matches}
    matched_truth = {item[1] for item in matches}
    for index, item in enumerate(truth):
        color = "#31b98b" if index in matched_truth else "#ffb020"
        polygon = item["polygon"] + [item["polygon"][0]]
        draw.line(polygon, fill=color, width=3)
        draw.text(
            item["polygon"][0], "GT" if index in matched_truth else "FN", fill=color, font=font
        )
    for index, item in enumerate(predictions):
        color = "#22a7f0" if index in matched_predictions else "#ef5b5b"
        polygon = item["polygon"] + [item["polygon"][0]]
        draw.line(polygon, fill=color, width=3)
        label = (
            f"TP {item['confidence']:.2f}"
            if index in matched_predictions
            else f"FP {item['confidence']:.2f}"
        )
        draw.text(item["polygon"][0], label, fill=color, font=font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, quality=92)
