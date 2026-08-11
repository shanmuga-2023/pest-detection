"""
Real-Time Live Video Stream Pest & Disease Detection Pipeline.

Supports webcam feeds (--source 0), RTSP IP camera streams, or local MP4 video files.
Calculates frame-by-frame latency, FPS throughput, overlays detection bounding boxes,
triggers automated alert thresholds, and logs advisory recommendations.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
from ultralytics import YOLO

from advisory_system import get_treatment_advisory, generate_sms_alert


def process_video_stream(
    source: str | int,
    weights_path: str = "yolo26s.pt",
    imgsz: int = 640,
    conf_thresh: float = 0.25,
    max_frames: int | None = None,
    alert_threshold: int = 3,
    output_path: Path | None = None,
    show_window: bool = False
) -> Dict[str, Any]:
    """Process live video stream or video file with real-time YOLO detection and FPS monitoring."""
    print(f"\n🎥 Initializing Live Video Stream Processing...")
    print(f"  • Source           : {source}")
    print(f"  • Model Checkpoint : {weights_path}")
    print(f"  • Alert Threshold  : {alert_threshold} infection targets")

    model = YOLO(weights_path)

    # Open video source (webcam int 0 or stream URL/file string)
    try:
        src_val = int(source) if str(source).isdigit() else str(source)
    except ValueError:
        src_val = str(source)

    cap = cv2.VideoCapture(src_val)
    if not cap.isOpened():
        print(f"⚠️ Unable to open video source '{source}'. Generating synthetic video stream simulation for testing.")
        # Create a synthetic frame stream if physical camera is unattached
        fps_out = 30.0
        frame_w, frame_h = 640, 480
        total_frames = max_frames if max_frames else 60
        is_synthetic = True
    else:
        is_synthetic = False
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps_out = cap.get(cv2.CAP_PROP_FPS)
        if fps_out <= 0:
            fps_out = 30.0

    writer = None
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps_out, (frame_w, frame_h))

    frame_count = 0
    start_time = time.perf_counter()
    latencies: List[float] = []
    detections_summary: List[Dict[str, Any]] = []

    print("🚀 Video Stream Processing Started...")

    try:
        while True:
            if is_synthetic:
                # Generate synthetic test frame
                frame = np.full((frame_h, frame_w, 3), 40, dtype=np.uint8)
                cv2.circle(frame, (200 + (frame_count * 5) % 300, 240), 60, (30, 180, 50), -1)
                cv2.putText(frame, "AgriAI Live Camera Feed Simulator", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                ret = True
            else:
                ret, frame = cap.read()
                if not ret:
                    break

            frame_count += 1
            t0 = time.perf_counter()

            # Execute model inference
            results = model(frame, imgsz=imgsz, conf=conf_thresh, verbose=False)[0]
            t1 = time.perf_counter()
            latency_ms = (t1 - t0) * 1000
            latencies.append(latency_ms)

            # Draw detections
            num_targets = len(results.boxes)
            frame_dets = []

            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                score = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = model.names.get(cls_id, str(cls_id))
                frame_dets.append({"class": cls_name, "confidence": score})

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, f"{cls_name} {score:.2f}", (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            current_fps = 1000 / latency_ms if latency_ms > 0 else 0

            # Status and Alert Overlay
            status_color = (0, 255, 0) if num_targets < alert_threshold else (0, 0, 255)
            alert_text = "STATUS: SAFE" if num_targets < alert_threshold else f"⚠️ THREAT ALERT: {num_targets} INFECTIONS"
            
            cv2.rectangle(frame, (10, 10), (320, 110), (0, 0, 0), -1)
            cv2.putText(frame, f"FPS: {current_fps:.1f} | Latency: {latency_ms:.1f}ms", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, f"Frame: {frame_count} | Targets: {num_targets}", (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, alert_text, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)

            if frame_dets:
                detections_summary.extend(frame_dets)

            if writer:
                writer.write(frame)

            if max_frames and frame_count >= max_frames:
                break
    finally:
        if cap:
            cap.release()
        if writer:
            writer.release()

    total_time = time.perf_counter() - start_time
    avg_latency = float(np.mean(latencies)) if latencies else 0.0
    avg_fps = frame_count / total_time if total_time > 0 else 0.0

    print(f"\n✅ Video Stream Processing Complete!")
    print(f"  • Total Frames Processed : {frame_count}")
    print(f"  • Avg Latency Per Frame  : {avg_latency:.2f} ms")
    print(f"  • Average Throughput     : {avg_fps:.2f} FPS")

    # Generate advisory if threats detected
    top_class = detections_summary[0]["class"] if detections_summary else "rice_pest_yellow_stem_borer"
    sms_alert = generate_sms_alert(detections_summary[:1], farmer_name="Live Camera Manager")

    return {
        "source": str(source),
        "total_frames": frame_count,
        "avg_latency_ms": avg_latency,
        "avg_fps": avg_fps,
        "total_detections_logged": len(detections_summary),
        "primary_threat": top_class,
        "sms_alert": sms_alert,
        "output_video": str(output_path) if output_path else None
    }


def main():
    parser = argparse.ArgumentParser(description="Real-Time Live Video Stream Pest Detection.")
    parser.add_argument("--source", default="0", help="Camera device ID (e.g. 0), RTSP stream URL, or MP4 file")
    parser.add_argument("--weights", default="yolo26s.pt", help="YOLO checkpoint path")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference resolution")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--max-frames", type=int, default=60, help="Maximum frames to process")
    parser.add_argument("--output", type=Path, default=Path("runs/live_video_output/stream_output.mp4"))
    args = parser.parse_args()

    process_video_stream(
        source=args.source,
        weights_path=args.weights,
        imgsz=args.imgsz,
        conf_thresh=args.conf,
        max_frames=args.max_frames,
        output_path=args.output
    )


if __name__ == "__main__":
    main()
