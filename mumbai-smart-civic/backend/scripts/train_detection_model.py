from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET

import albumentations as A
import cv2
import torch
import yaml
from ultralytics import YOLO


CLASS_TO_ID = {"garbage": 0, "pothole": 1}
POTHOLE_ALIASES = {"d40", "pothole", "potholes"}
GARBAGE_ALIASES = {
    "trash",
    "garbage",
    "litter",
    "plastic",
    "paper",
    "metal",
    "glass",
    "waste",
    "can",
    "bottle",
    "cup",
    "wrapper",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class Sample:
    image_path: Path
    yolo_lines: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train garbage + pothole detector with YOLOv8")
    parser.add_argument("--work-dir", type=Path, default=Path("data/detection_work"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/garbage_pothole_yolo"))
    parser.add_argument("--rdd-dir", type=Path, default=None, help="RDD2022 root (VOC/XML format)")
    parser.add_argument("--pothole-yolo-dir", type=Path, default=None, help="Optional pothole dataset in YOLO format")
    parser.add_argument("--taco-json", type=Path, default=None, help="COCO json for garbage data (e.g., TACO)")
    parser.add_argument("--taco-images", type=Path, default=None, help="Image folder for COCO dataset")
    parser.add_argument("--garbage-yolo-dir", type=Path, default=None, help="Optional garbage dataset in YOLO format")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--rain-aug-ratio", type=float, default=0.2)
    parser.add_argument("--project", type=str, default="runs/detection")
    parser.add_argument("--name", type=str, default="garbage_pothole")
    parser.add_argument("--copy-best-to", type=Path, default=Path("app/ml_models/best.pt"))
    return parser.parse_args()


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def yolo_line_from_xyxy(class_id: int, x1: float, y1: float, x2: float, y2: float, w: float, h: float) -> str | None:
    x1 = max(0.0, min(x1, w))
    y1 = max(0.0, min(y1, h))
    x2 = max(0.0, min(x2, w))
    y2 = max(0.0, min(y2, h))
    bw = x2 - x1
    bh = y2 - y1
    if bw <= 1 or bh <= 1:
        return None
    xc = (x1 + x2) / 2.0 / w
    yc = (y1 + y2) / 2.0 / h
    bw_n = bw / w
    bh_n = bh / h
    return f"{class_id} {xc:.6f} {yc:.6f} {bw_n:.6f} {bh_n:.6f}"


def read_yolo_txt(path: Path) -> list[tuple[int, float, float, float, float]]:
    boxes: list[tuple[int, float, float, float, float]] = []
    if not path.exists():
        return boxes
    for row in path.read_text(encoding="utf-8").splitlines():
        row = row.strip()
        if not row:
            continue
        parts = row.split()
        if len(parts) != 5:
            continue
        try:
            cls = int(parts[0])
            boxes.append((cls, float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
        except ValueError:
            continue
    return boxes


def _sanitize_yolo_bbox(xc: float, yc: float, bw: float, bh: float) -> tuple[float, float, float, float] | None:
    xc = float(max(0.0, min(1.0, xc)))
    yc = float(max(0.0, min(1.0, yc)))
    bw = float(max(1e-6, min(1.0, bw)))
    bh = float(max(1e-6, min(1.0, bh)))

    x1 = max(0.0, xc - bw / 2.0)
    y1 = max(0.0, yc - bh / 2.0)
    x2 = min(1.0, xc + bw / 2.0)
    y2 = min(1.0, yc + bh / 2.0)
    new_bw = x2 - x1
    new_bh = y2 - y1
    if new_bw <= 1e-5 or new_bh <= 1e-5:
        return None
    new_xc = (x1 + x2) / 2.0
    new_yc = (y1 + y2) / 2.0
    return new_xc, new_yc, new_bw, new_bh


def load_rdd_samples(rdd_root: Path) -> list[Sample]:
    samples: list[Sample] = []
    xml_files = list(rdd_root.rglob("*.xml"))
    for xml_path in xml_files:
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except Exception:
            continue

        filename = root.findtext("filename")
        if not filename:
            continue
        image_path = xml_path.with_name(filename)
        if not image_path.exists():
            for suffix in IMAGE_SUFFIXES:
                candidate = xml_path.with_suffix(suffix)
                if candidate.exists():
                    image_path = candidate
                    break
        if not image_path.exists():
            continue

        size = root.find("size")
        if size is None:
            continue
        w = float(size.findtext("width", "0"))
        h = float(size.findtext("height", "0"))
        if w <= 0 or h <= 0:
            continue

        lines: list[str] = []
        for obj in root.findall("object"):
            cls_name = (obj.findtext("name") or "").strip().lower()
            if cls_name not in POTHOLE_ALIASES:
                continue
            bbox = obj.find("bndbox")
            if bbox is None:
                continue
            try:
                x1 = float(bbox.findtext("xmin", "0"))
                y1 = float(bbox.findtext("ymin", "0"))
                x2 = float(bbox.findtext("xmax", "0"))
                y2 = float(bbox.findtext("ymax", "0"))
            except ValueError:
                continue
            line = yolo_line_from_xyxy(CLASS_TO_ID["pothole"], x1, y1, x2, y2, w, h)
            if line:
                lines.append(line)

        if lines:
            samples.append(Sample(image_path=image_path, yolo_lines=lines))
    return samples


def load_coco_samples(coco_json: Path, images_root: Path) -> list[Sample]:
    data = json.loads(coco_json.read_text(encoding="utf-8"))
    images_by_id = {int(im["id"]): im for im in data.get("images", [])}
    cats_by_id = {int(cat["id"]): str(cat["name"]).strip().lower() for cat in data.get("categories", [])}
    ann_by_image: dict[int, list[dict]] = defaultdict(list)
    for ann in data.get("annotations", []):
        ann_by_image[int(ann["image_id"])].append(ann)

    samples: list[Sample] = []
    for image_id, img in images_by_id.items():
        img_path = images_root / str(img["file_name"])
        if not img_path.exists():
            continue
        w = float(img.get("width", 0))
        h = float(img.get("height", 0))
        if w <= 0 or h <= 0:
            continue

        lines: list[str] = []
        for ann in ann_by_image.get(image_id, []):
            cat_name = cats_by_id.get(int(ann.get("category_id", -1)), "")
            if not any(alias in cat_name for alias in GARBAGE_ALIASES):
                continue
            bbox = ann.get("bbox") or []
            if len(bbox) != 4:
                continue
            x, y, bw, bh = map(float, bbox)
            line = yolo_line_from_xyxy(CLASS_TO_ID["garbage"], x, y, x + bw, y + bh, w, h)
            if line:
                lines.append(line)
        if lines:
            samples.append(Sample(image_path=img_path, yolo_lines=lines))
    return samples


def _guess_dataset_kind(path: Path) -> str:
    lower = str(path).lower()
    if "pothole" in lower or "rdd" in lower:
        return "pothole"
    return "garbage"


def load_yolo_samples(yolo_root: Path) -> list[Sample]:
    """
    Generic YOLO loader. Assumes:
      - images/** and labels/** structure OR
      - images and labels in same tree with matching filenames.
    """
    kind = _guess_dataset_kind(yolo_root)
    class_id = CLASS_TO_ID["pothole"] if kind == "pothole" else CLASS_TO_ID["garbage"]
    samples: list[Sample] = []
    image_files = [p for p in yolo_root.rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES]
    for image_path in image_files:
        label_path = image_path.with_suffix(".txt")
        if "images" in image_path.parts:
            try:
                idx = image_path.parts.index("images")
                label_path = Path(*image_path.parts[:idx], "labels", *image_path.parts[idx + 1 :]).with_suffix(".txt")
            except Exception:
                pass
        if not label_path.exists():
            continue
        raw_boxes = read_yolo_txt(label_path)
        if not raw_boxes:
            continue
        # Remap all boxes from source classes to unified class for this dataset kind.
        lines = [f"{class_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}" for _, xc, yc, bw, bh in raw_boxes]
        sanitized: list[str] = []
        for _, xc, yc, bw, bh in raw_boxes:
            cleaned = _sanitize_yolo_bbox(xc, yc, bw, bh)
            if cleaned is None:
                continue
            s_xc, s_yc, s_bw, s_bh = cleaned
            sanitized.append(f"{class_id} {s_xc:.6f} {s_yc:.6f} {s_bw:.6f} {s_bh:.6f}")
        lines = sanitized
        if not lines:
            continue
        samples.append(Sample(image_path=image_path, yolo_lines=lines))
    return samples


def split_samples(samples: list[Sample], seed: int) -> dict[str, list[Sample]]:
    rng = random.Random(seed)
    shuffled = samples[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * 0.7)
    n_val = int(n * 0.2)
    return {
        "train": shuffled[:n_train],
        "val": shuffled[n_train : n_train + n_val],
        "test": shuffled[n_train + n_val :],
    }


def write_split_dataset(
    split_map: dict[str, list[Sample]],
    output_dir: Path,
    rain_aug_ratio: float,
    seed: int,
) -> None:
    ensure_clean_dir(output_dir)
    rng = random.Random(seed)

    rain_aug = A.Compose(
        [
            A.RandomRain(
                brightness_coefficient=0.9,
                drop_width=1,
                blur_value=3,
                p=0.8,
            ),
            A.MotionBlur(blur_limit=5, p=0.4),
            A.RandomBrightnessContrast(p=0.4),
        ],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]),
    )

    for split_name, samples in split_map.items():
        img_dir = output_dir / "images" / split_name
        lbl_dir = output_dir / "labels" / split_name
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for idx, sample in enumerate(samples):
            ext = sample.image_path.suffix.lower()
            out_img = img_dir / f"{split_name}_{idx:07d}{ext}"
            out_lbl = lbl_dir / f"{split_name}_{idx:07d}.txt"
            shutil.copy2(sample.image_path, out_img)
            out_lbl.write_text("\n".join(sample.yolo_lines) + "\n", encoding="utf-8")

            # Rain/blur brightness augmentation only on train split.
            if split_name != "train" or rng.random() > rain_aug_ratio:
                continue

            image = cv2.imread(str(out_img))
            if image is None:
                continue
            parsed = [row.split() for row in sample.yolo_lines]
            class_labels: list[int] = []
            bboxes: list[list[float]] = []
            for parts in parsed:
                cls = int(parts[0])
                xc, yc, bw, bh = map(float, parts[1:])
                cleaned = _sanitize_yolo_bbox(xc, yc, bw, bh)
                if cleaned is None:
                    continue
                c_xc, c_yc, c_bw, c_bh = cleaned
                class_labels.append(cls)
                bboxes.append([c_xc, c_yc, c_bw, c_bh])
            if not bboxes:
                continue

            augmented = rain_aug(image=image, bboxes=bboxes, class_labels=class_labels)
            aug_img = img_dir / f"{split_name}_{idx:07d}_rain{ext}"
            aug_lbl = lbl_dir / f"{split_name}_{idx:07d}_rain.txt"
            cv2.imwrite(str(aug_img), augmented["image"])

            aug_lines: list[str] = []
            for cls, box in zip(augmented["class_labels"], augmented["bboxes"]):
                xc, yc, bw, bh = box
                aug_lines.append(f"{int(cls)} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
            if aug_lines:
                aug_lbl.write_text("\n".join(aug_lines) + "\n", encoding="utf-8")


def write_data_yaml(output_dir: Path) -> Path:
    data_yaml = {
        "path": str(output_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {0: "garbage", 1: "pothole"},
    }
    yaml_path = output_dir / "data.yaml"
    yaml_path.write_text(yaml.safe_dump(data_yaml, sort_keys=False), encoding="utf-8")
    return yaml_path


def train_model(args: argparse.Namespace, data_yaml: Path) -> Path:
    model = YOLO("yolov8n.pt")
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
        device=0 if torch.cuda.is_available() else "cpu",
        degrees=8.0,
        fliplr=0.5,
        flipud=0.05,
        hsv_h=0.015,
        hsv_s=0.6,
        hsv_v=0.45,
        translate=0.08,
        scale=0.35,
        shear=3.0,
        perspective=0.0005,
        mosaic=0.8,
        mixup=0.1,
        workers=8,
    )

    metrics = model.val(data=str(data_yaml), split="test")
    print("=== Evaluation Metrics ===")
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall: {metrics.box.mr:.4f}")

    best_path = Path(model.trainer.best).resolve()
    return best_path


def collect_samples(args: argparse.Namespace) -> list[Sample]:
    all_samples: list[Sample] = []
    if args.rdd_dir and args.rdd_dir.exists():
        all_samples.extend(load_rdd_samples(args.rdd_dir))
    if args.pothole_yolo_dir and args.pothole_yolo_dir.exists():
        all_samples.extend(load_yolo_samples(args.pothole_yolo_dir))
    if args.taco_json and args.taco_images and args.taco_json.exists() and args.taco_images.exists():
        all_samples.extend(load_coco_samples(args.taco_json, args.taco_images))
    if args.garbage_yolo_dir and args.garbage_yolo_dir.exists():
        all_samples.extend(load_yolo_samples(args.garbage_yolo_dir))

    if not all_samples:
        raise RuntimeError(
            "No samples found. Provide at least one dataset source "
            "(--rdd-dir / --pothole-yolo-dir / --taco-json + --taco-images / --garbage-yolo-dir)."
        )
    return all_samples


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    args.work_dir.mkdir(parents=True, exist_ok=True)
    all_samples = collect_samples(args)
    print(f"Loaded samples: {len(all_samples)}")

    split_map = split_samples(all_samples, seed=args.seed)
    for split_name, rows in split_map.items():
        print(f"{split_name}: {len(rows)}")

    write_split_dataset(
        split_map=split_map,
        output_dir=args.output_dir,
        rain_aug_ratio=args.rain_aug_ratio,
        seed=args.seed,
    )
    data_yaml = write_data_yaml(args.output_dir)
    best_pt = train_model(args, data_yaml)

    copy_target = args.copy_best_to
    if not copy_target.is_absolute():
        copy_target = Path.cwd() / copy_target
    copy_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_pt, copy_target)

    print("=== Training Complete ===")
    print(f"Best weights: {best_pt}")
    print(f"Copied weights to: {copy_target}")


if __name__ == "__main__":
    main()
