from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_tools.dota_ship import write_dota_ship_yaml  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewrite DOTA ship YAML for its current location")
    parser.add_argument("dataset", type=Path, nargs="?", default=Path("datasets/dota_ship"))
    args = parser.parse_args()
    destination = write_dota_ship_yaml(args.dataset)
    print(f"Dataset config: {destination}")


if __name__ == "__main__":
    main()
