import math

import pytest

from backend.app.geometry import cxcywha_to_polygon, match_detections, polygon_area, rotated_iou


def test_rotated_iou_is_one_for_identical_boxes() -> None:
    polygon = cxcywha_to_polygon(50, 50, 40, 12, math.radians(32))
    assert polygon_area(polygon) == pytest.approx(480)
    assert rotated_iou(polygon, polygon) == pytest.approx(1.0)


def test_rotated_iou_is_zero_for_disjoint_boxes() -> None:
    first = cxcywha_to_polygon(20, 20, 10, 10, 0)
    second = cxcywha_to_polygon(80, 80, 10, 10, math.radians(45))
    assert rotated_iou(first, second) == 0.0


def test_matching_is_one_to_one_and_class_aware() -> None:
    box = cxcywha_to_polygon(30, 30, 18, 8, 0.2)
    predictions = [
        {"class_id": 0, "confidence": 0.9, "polygon": box},
        {"class_id": 0, "confidence": 0.6, "polygon": box},
    ]
    truth = [{"class_id": 0, "polygon": box}]
    matches, fp, fn = match_detections(predictions, truth, 0.5)
    assert len(matches) == 1
    assert fp == [1]
    assert fn == []
