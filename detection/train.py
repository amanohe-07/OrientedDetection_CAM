from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLOv8n-OBB on the DOTA ship subset")
    parser.add_argument("--data", type=Path, default=Path("datasets/dota_ship/dota_ship.yaml"))
    parser.add_argument("--model", default="yolov8n-obb.pt")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--project", default="runs/dota_ship")
    parser.add_argument("--name", default="yolov8n-obb")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=str(args.data.resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=args.project,
        name=args.name,
        task="obb",
        pretrained=True,
        patience=20,
        cache=False,
        seed=42,
        deterministic=True,
        plots=True,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
