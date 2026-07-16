from pathlib import Path

from PIL import Image

from dataset_tools.dota_ship import (
    DOTA_CLASSES,
    find_modelscope_archive,
    parse_yolo_obb_label,
    prepare_dota_ship,
    write_dota_ship_yaml,
)


def test_dota_ship_class_index_matches_ultralytics_order() -> None:
    assert DOTA_CLASSES.index("ship") == 1
    assert len(DOTA_CLASSES) == 15


def test_parse_yolo_obb_label_ignores_invalid_lines(tmp_path: Path) -> None:
    label = tmp_path / "patch.txt"
    label.write_text(
        "1 0.1 0.2 0.3 0.2 0.3 0.4 0.1 0.4\nbroken label\n0 0.0 0.0 1.0 0.0 1.0 1.0 0.0 1.0\n",
        encoding="utf-8",
    )
    parsed = parse_yolo_obb_label(label)
    assert len(parsed) == 2
    assert parsed[0][0] == 1
    assert parsed[0][1] == [0.1, 0.2, 0.3, 0.2, 0.3, 0.4, 0.1, 0.4]


def test_missing_label_is_an_empty_background() -> None:
    assert parse_yolo_obb_label(Path("does-not-exist.txt")) == []


def test_prepared_dota_patches_are_filtered_to_ship_subset(tmp_path: Path) -> None:
    source = tmp_path / "dota"
    ship_line = "1 0.1 0.2 0.4 0.2 0.4 0.3 0.1 0.3"
    plane_line = "0 0.2 0.2 0.5 0.2 0.5 0.5 0.2 0.5"
    for split in ("train", "val"):
        image_dir = source / "images" / split
        label_dir = source / "labels" / split
        image_dir.mkdir(parents=True)
        label_dir.mkdir(parents=True)
        for name, label in (("positive", ship_line), ("negative", plane_line)):
            Image.new("RGB", (256, 256), "#233b36").save(image_dir / f"{name}.png")
            (label_dir / f"{name}.txt").write_text(label, encoding="utf-8")

    output = tmp_path / "ship_subset"
    summary = prepare_dota_ship(
        source,
        output,
        negative_ratio=1.0,
        max_train=10,
        max_val=10,
        preview_count=1,
    )

    assert summary.ship_class_id == 1
    assert summary.splits["train"].positives == 1
    assert summary.splits["train"].negatives == 1
    assert (output / "labels" / "train" / "positive.txt").read_text().startswith("0 ")
    assert (output / "labels" / "train" / "negative.txt").read_text() == ""
    assert (output / "previews" / "positive.jpg").exists()
    assert (output / "dota_ship.yaml").exists()

    relocated = tmp_path / "relocated"
    relocated.mkdir()
    for directory in ("images/train", "images/val", "labels/train", "labels/val"):
        (relocated / directory).mkdir(parents=True)
    yaml_path = write_dota_ship_yaml(relocated)
    assert relocated.resolve().as_posix() in yaml_path.read_text(encoding="utf-8")


def test_modelscope_archive_is_found_recursively(tmp_path: Path) -> None:
    archive = tmp_path / "hub" / "datasets" / "yolo_master" / "DOTAv1.zip"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"placeholder")
    assert find_modelscope_archive(tmp_path) == archive
