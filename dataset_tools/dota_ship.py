from __future__ import annotations

import json
import os
import random
import shutil
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

DOTA_CLASSES = (
    "plane",
    "ship",
    "storage-tank",
    "baseball-diamond",
    "tennis-court",
    "basketball-court",
    "ground-track-field",
    "harbor",
    "bridge",
    "large-vehicle",
    "small-vehicle",
    "helicopter",
    "roundabout",
    "soccer-ball-field",
    "swimming-pool",
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class SplitSummary:
    positives: int
    negatives: int
    objects: int


@dataclass(frozen=True)
class DotaShipSummary:
    source_root: str
    prepared_root: str
    output_root: str
    ship_class_id: int
    crop_size: int
    gap: int
    splits: dict[str, SplitSummary]


def prepare_dota_ship(
    source: Path,
    output: Path,
    *,
    work_dir: Path | None = None,
    crop_size: int = 1024,
    gap: int = 200,
    negative_ratio: float = 0.25,
    max_train: int = 2500,
    max_val: int = 600,
    seed: int = 42,
    preview_count: int = 12,
) -> DotaShipSummary:
    """Create a compact single-class ship subset from a DOTA-v1.0 repository or zip."""
    source = source.resolve()
    output = output.resolve()
    work_dir = (work_dir or output.parent / "dota_work").resolve()
    if not source.exists():
        raise FileNotFoundError(f"DOTA source does not exist: {source}")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output}")
    if crop_size <= gap:
        raise ValueError("crop_size must be greater than gap")
    if not 0 <= negative_ratio <= 2:
        raise ValueError("negative_ratio must be between 0 and 2")

    extracted = _extract_if_needed(source, work_dir / "modelscope_extracted")
    dota_root = _find_dota_root(extracted)
    _ensure_yolo_labels(dota_root)
    prepared_root = _ensure_patches(dota_root, work_dir / "dota_patches", crop_size, gap)
    ship_class_id = _detect_ship_class_id(prepared_root)

    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    split_summaries: dict[str, SplitSummary] = {}
    limits = {"train": max_train, "val": max_val}
    for split in ("train", "val"):
        split_summaries[split] = _build_split(
            prepared_root,
            output,
            split,
            ship_class_id,
            negative_ratio,
            limits[split],
            rng,
        )
    write_dota_ship_yaml(output)
    summary = DotaShipSummary(
        source_root=str(source),
        prepared_root=str(prepared_root),
        output_root=str(output),
        ship_class_id=ship_class_id,
        crop_size=crop_size,
        gap=gap,
        splits=split_summaries,
    )
    (output / "manifest.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_previews(output, preview_count)
    return summary


def find_modelscope_archive(cache_dir: Path) -> Path:
    matches = sorted(
        cache_dir.rglob("DOTAv1.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError(f"DOTAv1.zip was not found under {cache_dir}")
    return matches[0]


def parse_yolo_obb_label(path: Path) -> list[tuple[int, list[float]]]:
    if not path.exists():
        return []
    labels: list[tuple[int, list[float]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 9:
            continue
        try:
            labels.append((int(float(parts[0])), [float(value) for value in parts[1:]]))
        except ValueError:
            continue
    return labels


def _extract_if_needed(source: Path, destination: Path) -> Path:
    if source.is_dir():
        if _find_dota_root_optional(source):
            return source
        archive = find_modelscope_archive(source)
        source = archive
    if not zipfile.is_zipfile(source):
        raise ValueError(f"Source is not a DOTA directory or zip archive: {source}")
    marker = destination / ".extracted"
    if marker.exists():
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if destination_root not in target.parents and target != destination_root:
                raise ValueError(f"Unsafe path in DOTA archive: {member.filename}")
        archive.extractall(destination)
    marker.write_text(str(source), encoding="utf-8")
    return destination


def _find_dota_root(source: Path) -> Path:
    root = _find_dota_root_optional(source)
    if root is None:
        raise FileNotFoundError(
            "Could not find images/train, images/val and labels under the extracted DOTA archive"
        )
    return root


def _find_dota_root_optional(source: Path) -> Path | None:
    candidates = [source, *(path.parent for path in source.rglob("images") if path.is_dir())]
    for root in candidates:
        if (
            (root / "images" / "train").is_dir()
            and (root / "images" / "val").is_dir()
            and (root / "labels").is_dir()
        ):
            return root
    return None


def _ensure_yolo_labels(dota_root: Path) -> None:
    if (dota_root / "labels" / "train").is_dir() and (dota_root / "labels" / "val").is_dir():
        return
    if not (dota_root / "labels" / "train_original").is_dir():
        raise FileNotFoundError("DOTA labels/train or labels/train_original was not found")
    try:
        from ultralytics.data.converter import convert_dota_to_yolo_obb
    except ImportError as exc:
        raise RuntimeError("Install requirements-ml.txt before converting raw DOTA labels") from exc
    convert_dota_to_yolo_obb(str(dota_root))


def _ensure_patches(dota_root: Path, patch_root: Path, crop_size: int, gap: int) -> Path:
    dimensions = _sample_dimensions(dota_root / "images" / "train", limit=24)
    if dimensions and max(max(size) for size in dimensions) <= crop_size:
        return dota_root
    patch_directories = [
        patch_root / "images" / "train",
        patch_root / "images" / "val",
        patch_root / "labels" / "train",
        patch_root / "labels" / "val",
    ]
    if all(path.is_dir() and any(path.iterdir()) for path in patch_directories):
        return patch_root
    try:
        from ultralytics.data.split_dota import split_trainval
    except ImportError as exc:
        raise RuntimeError(
            "Install requirements-ml.txt before splitting large DOTA images"
        ) from exc
    split_trainval(
        data_root=str(dota_root),
        save_dir=str(patch_root),
        crop_size=crop_size,
        gap=gap,
        rates=(1.0,),
    )
    return patch_root


def _sample_dimensions(directory: Path, limit: int) -> list[tuple[int, int]]:
    images = [path for path in directory.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES]
    dimensions = []
    for path in images[:limit]:
        with Image.open(path) as image:
            dimensions.append(image.size)
    return dimensions


def _detect_ship_class_id(root: Path) -> int:
    for yaml_path in root.glob("*.yaml"):
        config = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        names = config.get("names", {})
        entries = names.items() if isinstance(names, dict) else enumerate(names)
        for class_id, name in entries:
            if str(name).lower().replace("-", " ") == "ship":
                return int(class_id)
    return DOTA_CLASSES.index("ship")


def _build_split(
    source_root: Path,
    output_root: Path,
    split: str,
    ship_class_id: int,
    negative_ratio: float,
    max_images: int,
    rng: random.Random,
) -> SplitSummary:
    image_dir = source_root / "images" / split
    label_dir = source_root / "labels" / split
    image_paths = sorted(
        path for path in image_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES
    )
    positives: list[tuple[Path, list[list[float]]]] = []
    negatives: list[Path] = []
    for image_path in image_paths:
        labels = parse_yolo_obb_label(label_dir / f"{image_path.stem}.txt")
        ship_labels = [coords for class_id, coords in labels if class_id == ship_class_id]
        if ship_labels:
            positives.append((image_path, ship_labels))
        else:
            negatives.append(image_path)

    if not positives:
        raise ValueError(f"No ship labels were found in the DOTA {split} split")
    positive_limit = (
        max(1, int(max_images / (1 + negative_ratio))) if max_images else len(positives)
    )
    if len(positives) > positive_limit:
        positives = rng.sample(positives, positive_limit)
    negative_count = min(len(negatives), round(len(positives) * negative_ratio))
    if max_images:
        negative_count = min(negative_count, max_images - len(positives))
    selected_negatives = rng.sample(negatives, negative_count) if negative_count else []

    target_images = output_root / "images" / split
    target_labels = output_root / "labels" / split
    target_images.mkdir(parents=True, exist_ok=True)
    target_labels.mkdir(parents=True, exist_ok=True)
    object_count = 0
    for image_path, ship_labels in positives:
        _link_or_copy(image_path, target_images / image_path.name)
        object_count += len(ship_labels)
        lines = ["0 " + " ".join(f"{value:.8f}" for value in coords) for coords in ship_labels]
        (target_labels / f"{image_path.stem}.txt").write_text("\n".join(lines), encoding="utf-8")
    for image_path in selected_negatives:
        _link_or_copy(image_path, target_images / image_path.name)
        (target_labels / f"{image_path.stem}.txt").write_text("", encoding="utf-8")
    return SplitSummary(
        positives=len(positives),
        negatives=len(selected_negatives),
        objects=object_count,
    )


def _link_or_copy(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def write_dota_ship_yaml(output: Path) -> Path:
    output = output.resolve()
    required = [
        output / "images" / "train",
        output / "images" / "val",
        output / "labels" / "train",
        output / "labels" / "val",
    ]
    if not all(path.is_dir() for path in required):
        raise FileNotFoundError(f"DOTA ship subset is incomplete: {output}")
    content = (
        f"path: {output.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/val\n\n"
        "names:\n"
        "  0: ship\n"
    )
    destination = output / "dota_ship.yaml"
    destination.write_text(content, encoding="utf-8")
    return destination


def _write_previews(output: Path, preview_count: int) -> None:
    preview_dir = output / "previews"
    preview_dir.mkdir(exist_ok=True)
    image_paths = sorted(
        (output / "images" / "train").iterdir(),
        key=lambda path: (
            not bool(parse_yolo_obb_label(output / "labels" / "train" / f"{path.stem}.txt")),
            path.name,
        ),
    )[:preview_count]
    for image_path in image_paths:
        with Image.open(image_path) as image:
            canvas = image.convert("RGB")
        draw = ImageDraw.Draw(canvas)
        labels = parse_yolo_obb_label(output / "labels" / "train" / f"{image_path.stem}.txt")
        for _, coords in labels:
            polygon = [
                (coords[index] * canvas.width, coords[index + 1] * canvas.height)
                for index in range(0, 8, 2)
            ]
            draw.line(polygon + [polygon[0]], fill="#00e5a8", width=3)
        canvas.save(preview_dir / f"{image_path.stem}.jpg", quality=90)
