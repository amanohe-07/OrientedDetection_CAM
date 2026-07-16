from pathlib import Path

from backend.app.config import Settings
from backend.app.services.evaluation_service import EvaluationService
from backend.app.storage import JsonStore


def test_json_store_retries_windows_replace_conflict(tmp_path, monkeypatch) -> None:
    store = JsonStore(tmp_path)
    original_replace = Path.replace
    attempts = 0

    def flaky_replace(source: Path, destination: Path) -> Path:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError(5, "Access is denied")
        return original_replace(source, destination)

    monkeypatch.setattr(Path, "replace", flaky_replace)

    destination = store.write("evaluations/job.json", {"status": "running"})

    assert attempts == 3
    assert destination.exists()
    assert store.read("evaluations/job.json") == {"status": "running"}


def test_evaluation_service_marks_interrupted_jobs_failed(tmp_path) -> None:
    store = JsonStore(tmp_path)
    store.write(
        "evaluations/interrupted/job.json",
        {
            "id": "interrupted",
            "status": "running",
            "progress": 28,
            "message": "正在分析 160/600",
            "created_at": "2026-07-14T00:00:00+00:00",
            "finished_at": None,
            "metrics": {},
        },
    )
    settings = Settings(
        artifacts_dir=tmp_path,
        model_path=tmp_path / "best.pt",
        dataset_config=tmp_path / "dataset.yaml",
    )

    service = EvaluationService(settings, object(), store)  # type: ignore[arg-type]
    recovered = service.get_job("interrupted")

    assert recovered is not None
    assert recovered["status"] == "failed"
    assert recovered["progress"] == 28
    assert "后端已重启" in recovered["message"]
    assert recovered["finished_at"] is not None
