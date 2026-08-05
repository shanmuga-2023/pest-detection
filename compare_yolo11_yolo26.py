"""
Benchmark and Compare YOLO11 vs YOLO26 Models

This script compares model architecture specs (parameters, layers) and measures
inference speed (FPS, latency breakdown) for YOLO11 vs YOLO26 checkpoints.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
import numpy as np
import torch
from ultralytics import YOLO


def benchmark_model(model_path: str | Path, imgsz: int = 640, runs: int = 50, device: str = "cpu"):
    """Benchmark a YOLO model checkpoint for parameters, FLOPS, and inference speed."""
    print(f"\n{'=' * 60}")
    print(f"  Benchmarking: {Path(model_path).name}")
    print(f"{'=' * 60}")

    if not Path(model_path).exists():
        print(f"Checkpoint '{model_path}' not found. Downloading/Loading from Ultralytics...")

    model = YOLO(model_path)
    
    # Model architecture stats
    info = model.info(verbose=False)
    
    # Warmup runs
    dummy_input = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
    print(f"Warming up ({device.upper()})...")
    for _ in range(10):
        _ = model.predict(dummy_input, imgsz=imgsz, device=device, verbose=False)

    # Benchmark timing
    latencies = []
    for _ in range(runs):
        start = time.perf_counter()
        results = model.predict(dummy_input, imgsz=imgsz, device=device, verbose=False)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms

    avg_latency = np.mean(latencies)
    std_latency = np.std(latencies)
    fps = 1000 / avg_latency if avg_latency > 0 else 0

    speed_info = results[0].speed if results else {}

    print("\n📊 Model Comparison Stats:")
    print(f"  • Checkpoint File   : {model_path}")
    print(f"  • Device            : {device.upper()}")
    print(f"  • Image Size        : {imgsz}x{imgsz}")
    print(f"  • Avg Total Latency : {avg_latency:.2f} ms ± {std_latency:.2f} ms")
    print(f"  • Throughput        : {fps:.2f} FPS")
    if speed_info:
        print(f"  • Preprocess        : {speed_info.get('preprocess', 0):.2f} ms")
        print(f"  • Inference         : {speed_info.get('inference', 0):.2f} ms")
        print(f"  • Postprocess (NMS) : {speed_info.get('postprocess', 0):.2f} ms")

    return {
        "model": str(model_path),
        "avg_latency_ms": avg_latency,
        "fps": fps,
        "speed_info": speed_info
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark and Compare YOLO11 vs YOLO26.")
    parser.add_argument("--model1", default="yolo11s.pt", help="First model checkpoint path or name")
    parser.add_argument("--model2", default="yolo26s.pt", help="Second model checkpoint path or name")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference resolution")
    parser.add_argument("--runs", type=int, default=50, help="Number of benchmark iterations")
    parser.add_argument("--device", default="cpu", help="Device to benchmark on ('cpu', '0', 'mps')")
    args = parser.parse_args()

    res1 = benchmark_model(args.model1, imgsz=args.imgsz, runs=args.runs, device=args.device)
    res2 = benchmark_model(args.model2, imgsz=args.imgsz, runs=args.runs, device=args.device)

    print(f"\n{'=' * 60}")
    print("  SUMMARY COMPARISON RESULTS")
    print(f"{'=' * 60}")
    print(f"{'Metric':<25} | {'YOLO11 (' + Path(args.model1).name + ')':<20} | {'YOLO26 (' + Path(args.model2).name + ')':<20}")
    print("-" * 73)
    print(f"{'Avg Latency (ms)':<25} | {res1['avg_latency_ms']:<20.2f} | {res2['avg_latency_ms']:<20.2f}")
    print(f"{'Throughput (FPS)':<25} | {res1['fps']:<20.2f} | {res2['fps']:<20.2f}")
    
    post1 = res1['speed_info'].get('postprocess', 0)
    post2 = res2['speed_info'].get('postprocess', 0)
    print(f"{'Postprocess/NMS (ms)':<25} | {post1:<20.2f} | {post2:<20.2f}")
    
    diff_fps = ((res2['fps'] - res1['fps']) / res1['fps']) * 100 if res1['fps'] > 0 else 0
    print("-" * 73)
    print(f"Speed Difference: YOLO26 is {diff_fps:+.1f}% {'faster' if diff_fps > 0 else 'slower'} in throughput.")
    print("=" * 60)


if __name__ == "__main__":
    main()
