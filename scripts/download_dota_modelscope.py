from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_tools.dota_ship import find_modelscope_archive  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download DOTAv1 from ModelScope")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("datasets/modelscope-cache"),
        help="ModelScope cache directory",
    )
    parser.add_argument("--workers", type=int, default=4, help="Parallel download workers")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache_dir = args.cache_dir.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MODELSCOPE_CACHE"] = str(cache_dir)
    try:
        from modelscope.hub.snapshot_download import dataset_snapshot_download
    except ImportError as exc:
        raise SystemExit("Install requirements-data.txt before downloading DOTAv1") from exc

    dataset_snapshot_download(
        dataset_id="yolo_master/DOTAv1",
        local_dir=str(cache_dir),
        allow_file_pattern="datasets/yolo_master/DOTAv1.zip",
        max_workers=args.workers,
    )
    archive = find_modelscope_archive(cache_dir)
    print(f"DOTAv1 archive: {archive}")
    print(f"Size: {archive.stat().st_size / (1024**3):.2f} GiB")


if __name__ == "__main__":
    main()
