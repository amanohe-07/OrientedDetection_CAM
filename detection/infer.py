from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CPU OBB inference")
    parser.add_argument("source", type=Path)
    parser.add_argument("--weights", type=Path, default=Path("weights/best.pt"))
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from ultralytics import YOLO

    YOLO(str(args.weights)).predict(
        source=str(args.source),
        imgsz=args.imgsz,
        conf=args.conf,
        device=args.device,
        save=True,
        project="runs/inference",
        name="latest",
    )


if __name__ == "__main__":
    main()
