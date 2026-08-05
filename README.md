# 🌾 Rice & Maize Pest & Disease Detection: YOLO11 vs YOLO26

This repository provides a complete, end-to-end framework to build, train, benchmark, and deploy **YOLO11** and **YOLO26** models for crop pest and disease detection and classification.

---

## 📊 Model Comparison: YOLO11 vs. YOLO26

| Feature / Metric | **YOLO11** (Ultralytics late-2024) | **YOLO26** (Ultralytics 2025/2026) |
| :--- | :--- | :--- |
| **Primary Focus** | General accuracy & spatial attention | **Edge-First**, **NMS-Free**, & ultra-low latency |
| **Post-Processing** | Standard (requires NMS filtering) | **NMS-Free** (End-to-end direct box output) |
| **Architectural Modules** | C3k2 and C2PSA blocks | DFL removal, **ProgLoss**, **STAL** (Small Target Assign) |
| **Small-Pest Sensitivity** | High (with 1280px input) | Very High (STAL small-target label assigner) |
| **Throughput / Latency** | High performance baseline | **~40%+ faster** CPU/Edge throughput |
| **Default Model Weights** | `yolo11s.pt`, `yolo11s-cls.pt` | `yolo26s.pt`, `yolo26s-cls.pt` |

---

## 📁 Repository Structure

```text
ai compare/
├── RicePest-30-Dataset/                 # Raw image dataset organized by crop/disease/pest folders
├── dataset.yaml                          # YOLO dataset configuration
├── yolo11s.pt                            # Pretrained YOLO11 small detector checkpoint
├── yolo11s-cls.pt                        # Pretrained YOLO11 small classifier checkpoint
├── yolo26s.pt                            # Pretrained YOLO26 small detector checkpoint
│
├── prepare_yolo11_dataset.py             # Prepares YOLO11 detection dataset from LabelMe JSONs
├── prepare_yolo26_dataset.py             # Prepares YOLO26 detection dataset from LabelMe JSONs
├── train_yolo11.py                       # Trains YOLO11 detector (tuned for small pests @ 1280px)
├── train_yolo26.py                       # Trains YOLO26 detector (tuned for small pests @ 1280px)
│
├── prepare_yolo11_classification.py      # Prepares stratified classification dataset for YOLO11
├── prepare_yolo26_classification.py      # Prepares stratified classification dataset for YOLO26
├── train_yolo11_classify.py              # Trains YOLO11 image classifier
├── train_yolo26_classify.py              # Trains YOLO26 image classifier
│
├── compare_yolo11_yolo26.py              # Benchmarks latency, FPS, & post-processing for both models
├── predict_tiled.py                      # Performs high-resolution tiled inference for field photos
├── requirements.txt                      # Project dependencies
└── README.md                             # Documentation
```

---

## 🛠️ Step-by-Step Workflow

### 1. Installation & Environment Setup

```bash
python -m pip install -r requirements.txt
```

---

### 2. Image Annotation (Object Detection)

For object detection, annotate your dataset using tools like **LabelMe**, **CVAT**, **Roboflow**, or **Label Studio**. Draw tight bounding boxes around every pest insect or disease lesion.

Structure your annotations directory mirroring your dataset folder:

```text
annotations/Rice/Insect-pests/05_Leaf_folder/4c6ee278-....json
RicePest-30-Dataset/Rice/Insect-pests/05_Leaf_folder/4c6ee278-....jpg
```

---

### 3. Create Detection Datasets

Convert your mirrored LabelMe annotations into Ultralytics YOLO format:

```bash
# Prepare dataset for YOLO11:
python prepare_yolo11_dataset.py --source RicePest-30-Dataset --output yolo_dataset

# Prepare dataset for YOLO26:
python prepare_yolo26_dataset.py --source RicePest-30-Dataset --output yolo26_dataset
```

---

### 4. Train Object Detection Models

Both training scripts are configured with hyperparameter settings optimized for **small insects** (1280px resolution, mosaic, mixup, multi-scale):

```bash
# Train YOLO11:
python train_yolo11.py --data yolo_dataset/dataset.yaml --model yolo11s.pt --epochs 150

# Train YOLO26:
python train_yolo26.py --data yolo26_dataset/dataset.yaml --model yolo26s.pt --epochs 150
```

---

### 5. Benchmark & Compare Performance

Measure latency (ms), throughput (FPS), preprocessing, and NMS post-processing times side-by-side:

```bash
python compare_yolo11_yolo26.py --model1 yolo11s.pt --model2 yolo26s.pt --runs 50 --device cpu
```

---

### 6. Predict on Field Images using Tiling

For large field images with tiny pests, use tiled prediction to avoid scaling down fine details:

```bash
python predict_tiled.py --weights runs/pest_disease_yolo26/weights/best.pt --source path/to/field_photo.jpg
```

Outputs will be saved in `runs/tiled_predictions/`.

---

### 7. Image Classification Pipeline (Folder-Only Data)

If you only have image-level class folders without bounding boxes, use the classification pipeline:

```bash
# Prepare & train YOLO11 Classification:
python prepare_yolo11_classification.py --source RicePest-30-Dataset --output classification_dataset
python train_yolo11_classify.py --data classification_dataset --model yolo11s-cls.pt --epochs 100

# Prepare & train YOLO26 Classification:
python prepare_yolo26_classification.py --source RicePest-30-Dataset --output classification_dataset_yolo26
python train_yolo26_classify.py --data classification_dataset_yolo26 --model yolo26s-cls.pt --epochs 100
```
# ai-rice-pest-
# ai-rice-pest-
