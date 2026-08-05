"""Materialize an annotated rice/maize dataset in Ultralytics YOLO detection format."""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
from collections import Counter
from pathlib import Path

import yaml
from PIL import Image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def slug(text: str) -> str:
    text = re.sub(r"^\d+[_ -]*", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def image_files(root: Path):
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)


def class_for(image: Path, source: Path) -> str | None:
    relative = image.relative_to(source)
    parts = relative.parts
    crop = slug(parts[0])
    if len(parts) == 3 and parts[1].lower() == "healthy":
        return None
    if len(parts) < 4 or parts[1].lower() not in {"disease", "insect-pests"}:
        raise ValueError(f"Unsupported source layout: {relative}")
    kind = "pest" if parts[1].lower() == "insect-pests" else "disease"
    return f"{crop}_{kind}_{slug(parts[2])}"


def labelme_boxes(json_path: Path, width: int, height: int, name_to_id: dict[str, int]):
    data = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for shape in data.get("shapes", []):
        label = slug(str(shape.get("label", "")))
        if label not in name_to_id:
            valid = ", ".join(name_to_id)
            raise ValueError(f"{json_path}: unknown label '{label}'. Use one of: {valid}")
        if shape.get("shape_type", "rectangle") != "rectangle" or len(shape.get("points", [])) != 2:
            raise ValueError(f"{json_path}: only two-point rectangle shapes are supported")
        (x1, y1), (x2, y2) = shape["points"]
        x1, x2 = sorted((max(0, x1), min(width, x2)))
        y1, y2 = sorted((max(0, y1), min(height, y2)))
        bw, bh = x2 - x1, y2 - y1
        if bw < 2 or bh < 2:
            continue
        rows.append(f"{name_to_id[label]} {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} {bw / width:.6f} {bh / height:.6f}")
    return rows


def split_by_class(records, seed: int):
    """Stratify positives; distribute negative examples with the same ratios."""
    groups: dict[str, list[tuple[Path, str | None]]] = {}
    for record in records:
        groups.setdefault(record[1] or "__negative__", []).append(record)
    rng = random.Random(seed)
    split = {"train": [], "val": [], "test": []}
    for group in groups.values():
        rng.shuffle(group)
        n = len(group)
        n_train = max(1, round(n * 0.70))
        n_val = max(1, round(n * 0.20)) if n >= 5 else 0
        n_train = min(n_train, n - n_val)
        split["train"].extend(group[:n_train])
        split["val"].extend(group[n_train:n_train + n_val])
        split["test"].extend(group[n_train + n_val:])
    return split


def find_coco_jsons(source: Path) -> dict[str, Path]:
    """Locate train and val COCO JSON files inside source directory."""
    jsons = list(source.rglob("*.json"))
    splits = {}
    for p in jsons:
        name = p.stem.lower()
        if "train" in name and "train" not in splits:
            splits["train"] = p
        elif "val" in name and "val" not in splits:
            splits["val"] = p
        elif "test" in name and "test" not in splits:
            splits["test"] = p
    return splits


def process_coco_dataset(source: Path, output: Path, coco_splits: dict[str, Path]):
    first_split = list(coco_splits.keys())[0]
    ref_data = json.loads(coco_splits[first_split].read_text(encoding="utf-8"))
    raw_cats = sorted(ref_data.get("categories", []), key=lambda c: c["id"])
    cat_id_to_yolo_id = {c["id"]: i for i, c in enumerate(raw_cats)}
    class_names = {i: c["name"] for i, c in enumerate(raw_cats)}

    print(f"COCO Dataset detected with {len(class_names)} categories:")
    for idx, name in class_names.items():
        print(f"  {idx}: {name}")

    report: dict[str, dict] = {"splits": {}, "classes": Counter()}

    try:
        for split_name, json_file in coco_splits.items():
            data = json.loads(json_file.read_text(encoding="utf-8"))
            img_id_map = {img["id"]: img for img in data.get("images", [])}

            anns_by_img: dict[int, list] = {}
            for ann in data.get("annotations", []):
                anns_by_img.setdefault(ann["image_id"], []).append(ann)

            img_dir = output / "images" / split_name
            lbl_dir = output / "labels" / split_name
            img_dir.mkdir(parents=True, exist_ok=True)
            lbl_dir.mkdir(parents=True, exist_ok=True)

            copied_count = 0
            for img_id, img_info in img_id_map.items():
                filename = img_info["file_name"]
                src_img = json_file.parent / filename
                if not src_img.exists():
                    src_img = source / filename
                if not src_img.exists():
                    matches = list(source.rglob(filename))
                    if matches:
                        src_img = matches[0]
                    else:
                        continue

                dst_img = img_dir / filename
                shutil.copy2(src_img, dst_img)
                copied_count += 1

                lbl_file = lbl_dir / f"{Path(filename).stem}.txt"
                w, h = img_info["width"], img_info["height"]
                rows = []
                for ann in anns_by_img.get(img_id, []):
                    cat_id = ann["category_id"]
                    if cat_id not in cat_id_to_yolo_id:
                        continue
                    yolo_cat = cat_id_to_yolo_id[cat_id]
                    bx, by, bw, bh = ann["bbox"]
                    bx, bw = max(0, bx), min(w - bx, bw)
                    by, bh = max(0, by), min(h - by, bh)
                    if bw < 2 or bh < 2:
                        continue
                    xc = (bx + bw / 2) / w
                    yc = (by + bh / 2) / h
                    nw = bw / w
                    nh = bh / h
                    rows.append(f"{yolo_cat} {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}")
                    report["classes"][class_names[yolo_cat]] += 1

                lbl_file.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")

            report["splits"][split_name] = copied_count

        config = {
            "path": str(output),
            "train": "images/train",
            "val": "images/val",
            "names": class_names
        }
        (output / "dataset.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        report["classes"] = dict(report["classes"])
        (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

        print(f"Successfully created YOLO11 detection dataset at: {output}")
        print(f"Splits: {report['splits']}")
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Convert dataset (COCO format or mirrored LabelMe annotations) to YOLO11 detection format.")
    parser.add_argument("--source", type=Path, required=True, help="Raw dataset directory")
    parser.add_argument("--annotations", type=Path, default=None, help="Mirrored LabelMe JSON annotation directory (optional for COCO datasets)")
    parser.add_argument("--output", type=Path, required=True, help="New YOLO output directory")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists():
        raise SystemExit(f"Output already exists: {output}. Choose a new path or remove it deliberately.")

    # Check for COCO dataset JSON format first
    coco_splits = find_coco_jsons(source)
    if coco_splits:
        process_coco_dataset(source, output, coco_splits)
        return

    if args.annotations is None:
        raise SystemExit("No COCO JSON files found in source. Please specify --annotations for LabelMe format datasets.")

    annotations = args.annotations.resolve()
    images = image_files(source)
    if not images:
        raise SystemExit(f"No images found under {source}")
    classes = sorted({c for p in images if (c := class_for(p, source))})
    name_to_id = {name: i for i, name in enumerate(classes)}
    print("Detection labels:")
    for name, idx in name_to_id.items():
        print(f"  {idx}: {name}")
    records = [(image, class_for(image, source)) for image in images]
    missing = []
    for image, target in records:
        if target is not None:
            json_path = annotations / image.relative_to(source).with_suffix(".json")
            if not json_path.exists():
                missing.append(json_path)
    if missing:
        sample = "\n  ".join(str(p) for p in missing[:10])
        raise SystemExit(f"Missing LabelMe boxes for {len(missing)} affected images. First missing:\n  {sample}")
    splits = split_by_class(records, args.seed)
    try:
        for split, members in splits.items():
            for index, (image, target) in enumerate(members):
                stem = f"{index:06d}_{image.stem}"
                destination = output / "images" / split / f"{stem}{image.suffix.lower()}"
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(image, destination)
                label_path = output / "labels" / split / f"{stem}.txt"
                label_path.parent.mkdir(parents=True, exist_ok=True)
                rows = []
                if target is not None:
                    with Image.open(image) as im:
                        rows = labelme_boxes(annotations / image.relative_to(source).with_suffix(".json"), *im.size, name_to_id)
                    if not rows:
                        raise ValueError(f"No valid boxes in annotation for affected image: {image}")
                label_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise
    config = {
        "path": str(output),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {i: n for i, n in enumerate(classes)}
    }
    (output / "dataset.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    report = {split: len(items) for split, items in splits.items()}
    report["classes"] = Counter(target or "healthy_negative" for _, target in records)
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Created {output} with splits: {dict((k, len(v)) for k, v in splits.items())}")


if __name__ == "__main__":
    main()
