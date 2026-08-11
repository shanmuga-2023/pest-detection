"""
Drone / UAV Aerial Field Scanning & Orthomosaic Tiled Inference Pipeline.

Processes high-resolution aerial photography & orthomosaic field imagery,
divides large images into overlapping tiles, performs YOLO11/YOLO26 inference,
merges spatial detections across tile borders, generates pest/disease density heatmaps,
and exports geotagged spatial zone reports with automated farmer advisory alerts.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from ultralytics import YOLO

from advisory_system import get_treatment_advisory, generate_sms_alert


def iou(boxA: Tuple[float, float, float, float], boxB: Tuple[float, float, float, float]) -> float:
    """Calculate Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    unionArea = boxAArea + boxBArea - interArea
    return interArea / max(1.0, unionArea)


def run_drone_orthomosaic_scan(
    image_path: Path,
    weights_path: str,
    tile_size: int = 1280,
    overlap: float = 0.25,
    conf_thresh: float = 0.25,
    iou_thresh: float = 0.45,
    output_dir: Path = Path("runs/drone_orthomosaic_scans")
) -> Dict[str, Any]:
    """Execute high-resolution tiled aerial scanning and pest density mapping."""
    print(f"\n🛸 Launching Drone Aerial Orthomosaic Scan: {image_path.name}")
    if not image_path.exists():
        raise FileNotFoundError(f"Orthomosaic image not found: {image_path}")

    model = YOLO(weights_path)
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    print(f"  • Image Dimensions: {width}x{height} pixels")
    print(f"  • Tile Resolution : {tile_size}px (Overlap: {int(overlap*100)}%)")

    step = max(1, int(tile_size * (1 - overlap)))
    raw_boxes: List[Tuple[List[float], float, int]] = []

    tile_count = 0
    for top in range(0, height, step):
        for left in range(0, width, step):
            tile_count += 1
            right = min(left + tile_size, width)
            bottom = min(top + tile_size, height)
            
            crop = image.crop((left, top, right, bottom))
            results = model(crop, imgsz=tile_size, conf=conf_thresh, verbose=False)[0]

            for box in results.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                score = float(box.conf[0])
                cls_id = int(box.cls[0])
                # Shift coordinates back to full image space
                global_box = [x1 + left, y1 + top, x2 + left, y2 + bottom]
                raw_boxes.append((global_box, score, cls_id))

    print(f"  • Processed {tile_count} tiles, found {len(raw_boxes)} candidate detections.")

    # Spatial Non-Maximum Suppression across overlapping tile boundaries
    raw_boxes.sort(key=lambda item: item[1], reverse=True)
    merged_boxes: List[Tuple[List[float], float, int]] = []
    for candidate in raw_boxes:
        c_box, c_score, c_cls = candidate
        keep = True
        for chosen in merged_boxes:
            ch_box, _, ch_cls = chosen
            if c_cls == ch_cls and iou(c_box, ch_box) >= iou_thresh:
                keep = False
                break
        if keep:
            merged_boxes.append(candidate)

    print(f"  • Merged Spatial Detections (NMS): {len(merged_boxes)} unique targets.")

    # Generate Spatial Density Heatmap
    heatmap = np.zeros((height, width), dtype=np.float32)
    class_counts: Dict[str, int] = {}
    
    draw_img = image.copy()
    draw = ImageDraw.Draw(draw_img)
    names = model.names

    quadrants = {"North-West": 0, "North-East": 0, "South-West": 0, "South-East": 0}
    half_w, half_h = width / 2, height / 2

    for (x1, y1, x2, y2), score, cls_id in merged_boxes:
        cls_name = names.get(cls_id, str(cls_id))
        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

        # Quadrant assignment
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if cx < half_w and cy < half_h:
            quadrants["North-West"] += 1
        elif cx >= half_w and cy < half_h:
            quadrants["North-East"] += 1
        elif cx < half_w and cy >= half_h:
            quadrants["South-West"] += 1
        else:
            quadrants["South-East"] += 1

        # Draw box
        draw.rectangle((x1, y1, x2, y2), outline="#FF3838", width=max(2, int(width/800)))
        draw.text((x1, max(0, y1 - 18)), f"{cls_name} {score:.2f}", fill="#FF3838")

        # Accumulate heatmap density
        ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
        heatmap[iy1:iy2, ix1:ix2] += 1.0

    # Save Output Artifacts
    output_dir.mkdir(parents=True, exist_ok=True)
    out_annotated = output_dir / f"{image_path.stem}_drone_detections.jpg"
    draw_img.save(out_annotated)

    # Convert heatmap array to RGB color map overlay
    if heatmap.max() > 0:
        norm_heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8)
    else:
        norm_heatmap = heatmap.astype(np.uint8)

    heat_pil = Image.fromarray(norm_heatmap).resize((width, height), Image.Resampling.BILINEAR)
    heat_colored = Image.new("RGB", (width, height), (0, 0, 0))
    # Green-Yellow-Red gradient
    for y in range(0, height, 10):
        for x in range(0, width, 10):
            val = norm_heatmap[y, x]
            if val > 0:
                color = (int(val), int(255 - val), 0)
                heat_colored.paste(color, (x, y, x+10, y+10))

    blend_img = Image.blend(image, heat_colored, alpha=0.35)
    out_heatmap = output_dir / f"{image_path.stem}_density_heatmap.jpg"
    blend_img.save(out_heatmap)

    # Format advisory recommendation & SMS alert for drone findings
    top_class = max(class_counts, key=class_counts.get) if class_counts else "None"
    advisory = get_treatment_advisory(top_class) if top_class != "None" else {}
    sms_alert = generate_sms_alert(
        [{"class": top_class, "confidence": 0.92}] if top_class != "None" else [],
        farmer_name="Drone Field Manager"
    )

    report = {
        "orthomosaic_file": str(image_path),
        "resolution": f"{width}x{height}",
        "tiles_scanned": tile_count,
        "total_infections_detected": len(merged_boxes),
        "target_class_breakdown": class_counts,
        "spatial_quadrant_distribution": quadrants,
        "primary_threat": top_class,
        "agronomic_advisory": advisory,
        "sms_alert_payload": sms_alert,
        "output_annotated_image": str(out_annotated),
        "output_density_heatmap": str(out_heatmap)
    }

    report_json_path = output_dir / f"{image_path.stem}_scan_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Drone Orthomosaic Scan Finished successfully!")
    print(f"     • Annotated Image: {out_annotated}")
    print(f"     • Density Heatmap: {out_heatmap}")
    print(f"     • JSON Report    : {report_json_path}\n")

    return report


def main():
    parser = argparse.ArgumentParser(description="Drone Aerial Orthomosaic Tiled Inference Scanner.")
    parser.add_argument("--source", type=Path, required=True, help="Path to aerial orthomosaic field image")
    parser.add_argument("--weights", default="yolo26s.pt", help="YOLO checkpoint path")
    parser.add_argument("--tile", type=int, default=1280, help="Tile resolution")
    parser.add_argument("--overlap", type=float, default=0.25, help="Tile overlap fraction")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--output", type=Path, default=Path("runs/drone_orthomosaic_scans"))
    args = parser.parse_args()

    run_drone_orthomosaic_scan(
        image_path=args.source,
        weights_path=args.weights,
        tile_size=args.tile,
        overlap=args.overlap,
        conf_thresh=args.conf,
        output_dir=args.output
    )


if __name__ == "__main__":
    main()
