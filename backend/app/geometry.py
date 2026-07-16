from __future__ import annotations

import math
from collections.abc import Iterable

PointTuple = tuple[float, float]


def cxcywha_to_polygon(
    cx: float, cy: float, width: float, height: float, angle_rad: float
) -> list[PointTuple]:
    """Convert a center-size-angle box to clockwise image-coordinate corners."""
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    half_w = width / 2.0
    half_h = height / 2.0
    corners = [(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)]
    return [(cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a) for dx, dy in corners]


def polygon_area(points: Iterable[PointTuple]) -> float:
    pts = list(points)
    if len(pts) < 3:
        return 0.0
    return (
        abs(
            sum(
                pts[index][0] * pts[(index + 1) % len(pts)][1]
                - pts[(index + 1) % len(pts)][0] * pts[index][1]
                for index in range(len(pts))
            )
        )
        / 2.0
    )


def _signed_area(points: list[PointTuple]) -> float:
    return (
        sum(
            points[index][0] * points[(index + 1) % len(points)][1]
            - points[(index + 1) % len(points)][0] * points[index][1]
            for index in range(len(points))
        )
        / 2.0
    )


def _inside(point: PointTuple, edge_a: PointTuple, edge_b: PointTuple, sign: float) -> bool:
    cross = (edge_b[0] - edge_a[0]) * (point[1] - edge_a[1]) - (edge_b[1] - edge_a[1]) * (
        point[0] - edge_a[0]
    )
    return cross * sign >= -1e-9


def _intersection(
    start: PointTuple, end: PointTuple, edge_a: PointTuple, edge_b: PointTuple
) -> PointTuple:
    dx1, dy1 = end[0] - start[0], end[1] - start[1]
    dx2, dy2 = edge_b[0] - edge_a[0], edge_b[1] - edge_a[1]
    denominator = dx1 * dy2 - dy1 * dx2
    if abs(denominator) < 1e-12:
        return end
    t = ((edge_a[0] - start[0]) * dy2 - (edge_a[1] - start[1]) * dx2) / denominator
    return start[0] + t * dx1, start[1] + t * dy1


def convex_polygon_intersection(
    subject: list[PointTuple], clip: list[PointTuple]
) -> list[PointTuple]:
    if len(subject) < 3 or len(clip) < 3:
        return []
    output = subject[:]
    sign = 1.0 if _signed_area(clip) >= 0 else -1.0
    for index, edge_a in enumerate(clip):
        edge_b = clip[(index + 1) % len(clip)]
        input_points = output
        output = []
        if not input_points:
            break
        start = input_points[-1]
        for end in input_points:
            end_inside = _inside(end, edge_a, edge_b, sign)
            start_inside = _inside(start, edge_a, edge_b, sign)
            if end_inside:
                if not start_inside:
                    output.append(_intersection(start, end, edge_a, edge_b))
                output.append(end)
            elif start_inside:
                output.append(_intersection(start, end, edge_a, edge_b))
            start = end
    return output


def rotated_iou(a: list[PointTuple], b: list[PointTuple]) -> float:
    area_a = polygon_area(a)
    area_b = polygon_area(b)
    if area_a <= 0 or area_b <= 0:
        return 0.0
    intersection_area = polygon_area(convex_polygon_intersection(a, b))
    union = area_a + area_b - intersection_area
    return intersection_area / union if union > 0 else 0.0


def match_detections(
    predictions: list[dict], ground_truth: list[dict], iou_threshold: float
) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    """Greedily match confidence-sorted predictions to same-class ground truth."""
    used_truth: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    prediction_order = sorted(
        range(len(predictions)),
        key=lambda index: predictions[index].get("confidence", 0.0),
        reverse=True,
    )
    for pred_index in prediction_order:
        prediction = predictions[pred_index]
        candidates: list[tuple[float, int]] = []
        for gt_index, truth in enumerate(ground_truth):
            if gt_index in used_truth or prediction["class_id"] != truth["class_id"]:
                continue
            iou = rotated_iou(prediction["polygon"], truth["polygon"])
            if iou >= iou_threshold:
                candidates.append((iou, gt_index))
        if not candidates:
            continue
        iou, gt_index = max(candidates)
        used_truth.add(gt_index)
        matches.append((pred_index, gt_index, iou))
    used_predictions = {item[0] for item in matches}
    fp = [index for index in range(len(predictions)) if index not in used_predictions]
    fn = [index for index in range(len(ground_truth)) if index not in used_truth]
    return matches, fp, fn
