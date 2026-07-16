from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_tools.dota_ship import prepare_dota_ship  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a compact DOTA-v1.0 ship OBB subset")
    parser.add_argument("source", type=Path, help="DOTAv1.zip, extracted root, or ModelScope cache")
    parser.add_argument("--output", type=Path, default=Path("datasets/dota_ship"))
    parser.add_argument("--work-dir", type=Path, default=Path("datasets/dota_work"))
    parser.add_argument("--crop-size", type=int, default=1024)
    parser.add_argument("--gap", type=int, default=200)
    parser.add_argument("--negative-ratio", type=float, default=0.25)
    parser.add_argument("--max-train", type=int, default=2500)
    parser.add_argument("--max-val", type=int, default=600)
    parser.add_argument("--preview-count", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = prepare_dota_ship(
        args.source,
        args.output,
        work_dir=args.work_dir,
        crop_size=args.crop_size,
        gap=args.gap,
        negative_ratio=args.negative_ratio,
        max_train=args.max_train,
        max_val=args.max_val,
        preview_count=args.preview_count,
    )
    print(f"DOTA ship subset: {summary.output_root}")
    for split, values in summary.splits.items():
        print(
            f"{split}: {values.positives} positive patches, "
            f"{values.negatives} negatives, {values.objects} ships"
        )


if __name__ == "__main__":
    main()
