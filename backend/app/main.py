from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from backend.app.config import get_settings
from backend.app.schemas import CamRequest, EvaluationRequest, SampleAnalysis
from backend.app.services.cam_service import CamService
from backend.app.services.evaluation_service import EvaluationService
from backend.app.services.model_service import ModelService, ModelUnavailableError
from backend.app.storage import JsonStore

settings = get_settings()
store = JsonStore(settings.artifacts_dir)
model_service = ModelService(settings)
cam_service = CamService(model_service)
evaluation_service = EvaluationService(settings, model_service, store)

app = FastAPI(
    title="OrientedDetection CAM API",
    description="DOTA-v1.0 ship subset detection and attribution analysis service",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5190"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/artifacts", StaticFiles(directory=settings.artifacts_dir), name="artifacts")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/system")
def system_status() -> dict:
    model_state, details = model_service.status()
    return {
        "api": "ready",
        "model_state": model_state,
        "model_path": str(settings.model_path),
        "dataset_ready": settings.dataset_config.exists(),
        "dataset_config": str(settings.dataset_config),
        "device": settings.model_device,
        "details": details,
    }


@app.post("/api/inference")
def inference(
    image: UploadFile = File(...),
    confidence: float = Form(default=0.25),
    iou: float = Form(default=0.45),
    image_size: int = Form(default=640),
) -> dict:
    if not 0 <= confidence <= 1 or not 0 < iou <= 1:
        raise HTTPException(status_code=422, detail="阈值必须在 0 到 1 之间")
    suffix = Path(image.filename or "upload.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}:
        raise HTTPException(status_code=415, detail="不支持的图像格式")
    upload_id = uuid4().hex
    destination = settings.artifacts_dir / "uploads" / f"{upload_id}{suffix}"
    with destination.open("wb") as output:
        shutil.copyfileobj(image.file, output)
    try:
        with Image.open(destination) as loaded:
            loaded.verify()
    except (UnidentifiedImageError, OSError) as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=415, detail="上传文件不是有效图像") from exc
    try:
        result = model_service.predict(destination, confidence, iou, image_size)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    result["created_at"] = datetime.now(timezone.utc).isoformat()
    result["image_url"] = f"/artifacts/uploads/{destination.name}"
    store.write(Path("inferences") / f"{result['id']}.json", result)
    return result


@app.get("/api/evaluations")
def list_evaluations() -> list[dict]:
    return evaluation_service.list_jobs()


@app.post("/api/evaluations", status_code=202)
def create_evaluation(request: EvaluationRequest, background_tasks: BackgroundTasks) -> dict:
    job = evaluation_service.create_job(request.model_dump())
    background_tasks.add_task(evaluation_service.run, job["id"])
    return job


@app.get("/api/evaluations/{job_id}")
def get_evaluation(job_id: str) -> dict:
    job = evaluation_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="评估任务不存在")
    return job


@app.get("/api/samples")
def list_samples(
    evaluation_id: str | None = None,
    error_type: str | None = Query(default=None, pattern="^(TP|FP|FN|MIXED)$"),
    search: str | None = None,
) -> list[dict]:
    samples = evaluation_service.samples(evaluation_id)
    if error_type:
        samples = [item for item in samples if item["error_type"] == error_type]
    if search:
        needle = search.lower()
        samples = [item for item in samples if needle in item["filename"].lower()]
    return samples


def _find_sample(sample_id: str) -> dict:
    for sample in evaluation_service.samples():
        if sample["id"] == sample_id:
            return sample
    raise HTTPException(status_code=404, detail="样本不存在")


@app.put("/api/samples/{sample_id}/analysis")
def save_analysis(sample_id: str, analysis: SampleAnalysis) -> dict:
    sample = _find_sample(sample_id)
    sample["analysis"] = analysis.model_dump()
    evaluation_service.save_sample(sample)
    return sample


@app.post("/api/samples/{sample_id}/cam")
def generate_cam(sample_id: str, request: CamRequest) -> dict:
    sample = _find_sample(sample_id)
    source = Path(sample["source_path"])
    if not source.exists():
        raise HTTPException(status_code=404, detail="原始图像不存在")
    destination = settings.artifacts_dir / "cams" / f"{sample_id}.jpg"
    try:
        cam_service.generate(source, destination, request.layer_index, request.opacity)
    except (ModelUnavailableError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    sample["cam_url"] = f"/artifacts/cams/{destination.name}"
    evaluation_service.save_sample(sample)
    return sample


@app.get("/api/statistics")
def statistics() -> dict:
    samples = evaluation_service.samples()
    counts = {"TP": 0, "FP": 0, "FN": 0, "MIXED": 0}
    cause_counts: dict[str, int] = {}
    for sample in samples:
        counts[sample["error_type"]] += 1
        for cause in sample.get("analysis", {}).get("causes", []):
            cause_counts[cause] = cause_counts.get(cause, 0) + 1
    latest = evaluation_service.list_jobs()
    return {
        "sample_count": len(samples),
        "counts": counts,
        "causes": cause_counts,
        "latest_evaluation": latest[0] if latest else None,
    }


@app.get("/api/reports/{evaluation_id}")
def export_report(evaluation_id: str) -> FileResponse:
    job = evaluation_service.get_job(evaluation_id)
    if not job:
        raise HTTPException(status_code=404, detail="评估任务不存在")
    report = {
        "evaluation": job,
        "samples": evaluation_service.samples(evaluation_id),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    path = store.write(Path("evaluations") / evaluation_id / "report.json", report)
    return FileResponse(path, filename=f"dota-ship-report-{evaluation_id}.json")
