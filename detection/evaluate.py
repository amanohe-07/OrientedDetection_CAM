from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a YOLO OBB checkpoint")
    parser.add_argument("--weights", type=Path, default=Path("weights/best.pt"))
    parser.add_argument("--data", type=Path, default=Path("datasets/dota_ship/dota_ship.yaml"))
    parser.add_argument("--split", choices=("train", "val", "test"), default="val")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", type=Path, default=Path("artifacts/cli-evaluation.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from ultralytics import YOLO

    metrics = YOLO(str(args.weights)).val(
        data=str(args.data.resolve()),
        split=args.split,
        imgsz=args.imgsz,
        device=args.device,
        plots=True,
        verbose=True,
    )
    result = {
        "map50": float(metrics.box.map50),
        "map50_95": float(metrics.box.map),
        "map75": float(metrics.box.map75),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
