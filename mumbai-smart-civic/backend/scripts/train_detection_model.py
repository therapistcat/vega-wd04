from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

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
RF_HASH_PATTERN = re.compile(r"\.rf\.[a-z0-9]+$", re.IGNORECASE)
TRAIN_AUG_SUFFIX_PATTERN = re.compile(r"_(rain|quality|minority)\d*$", re.IGNORECASE)


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
    parser.add_argument("--model", type=str, default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=896)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--patience", type=int, default=40)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--optimizer", type=str, default="AdamW")
    parser.add_argument("--device", type=str, default="")
    parser.add_argument("--cache", action="store_true", help="Enable Ultralytics image cache during training.")
    parser.add_argument("--rain-aug-ratio", type=float, default=0.25)
    parser.add_argument("--quality-aug-ratio", type=float, default=0.35)
    parser.add_argument("--minority-aug-ratio", type=float, default=0.60)
    parser.add_argument("--project", type=str, default="runs/detection")
    parser.add_argument("--name", type=str, default="garbage_pothole")
    parser.add_argument("--copy-best-to", type=Path, default=Path("app/ml_models/best.pt"))
    parser.add_argument("--thresholds-output", type=Path, default=Path("app/ml_models/autotag_thresholds.json"))
    parser.add_argument("--skip-autotag-calibration", action="store_true")
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
    for row in path.read_text(encoding="utf-8", errors="ignore").splitlines():
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


def _normalize_label_lines(lines: list[str]) -> tuple[str, ...]:
    normalized = [" ".join(row.strip().split()) for row in lines if row.strip()]
    return tuple(sorted(normalized))


def _sample_class_ids(sample: Sample) -> set[int]:
    class_ids: set[int] = set()
    for row in sample.yolo_lines:
        parts = row.split()
        if parts:
            try:
                class_ids.add(int(parts[0]))
            except ValueError:
                continue
    return class_ids


def _sample_box_counts(sample: Sample) -> Counter[int]:
    counts: Counter[int] = Counter()
    for row in sample.yolo_lines:
        parts = row.split()
        if parts:
            try:
                counts[int(parts[0])] += 1
            except ValueError:
                continue
    return counts


def _canonical_image_key(path: Path) -> str:
    stem = RF_HASH_PATTERN.sub("", path.stem)
    stem = TRAIN_AUG_SUFFIX_PATTERN.sub("", stem)
    return stem.lower()


def dedupe_samples(samples: list[Sample]) -> tuple[list[Sample], int]:
    deduped: list[Sample] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    removed = 0
    for sample in samples:
        try:
            digest = hashlib.sha1(sample.image_path.read_bytes()).hexdigest()
        except Exception:
            continue
        labels = _normalize_label_lines(sample.yolo_lines)
        key = (digest, labels)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        deduped.append(sample)
    return deduped, removed


def _count_boxes(samples: list[Sample]) -> Counter[int]:
    counts: Counter[int] = Counter()
    for sample in samples:
        counts.update(_sample_box_counts(sample))
    return counts


def _print_class_distribution(title: str, samples: list[Sample]) -> None:
    counts = _count_boxes(samples)
    total = sum(counts.values())
    if total == 0:
        print(f"{title}: no boxes")
        return
    formatted = ", ".join(
        f"class_{cls}={cnt} ({(cnt / total) * 100:.1f}%)" for cls, cnt in sorted(counts.items())
    )
    print(f"{title}: boxes={total} -> {formatted}")


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
        lines: list[str] = []
        for _, xc, yc, bw, bh in raw_boxes:
            cleaned = _sanitize_yolo_bbox(xc, yc, bw, bh)
            if cleaned is None:
                continue
            s_xc, s_yc, s_bw, s_bh = cleaned
            lines.append(f"{class_id} {s_xc:.6f} {s_yc:.6f} {s_bw:.6f} {s_bh:.6f}")
        if not lines:
            continue
        samples.append(Sample(image_path=image_path, yolo_lines=lines))
    return samples


def split_samples(samples: list[Sample], seed: int) -> dict[str, list[Sample]]:
    rng = random.Random(seed)
    groups: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        groups[_canonical_image_key(sample.image_path)].append(sample)

    group_keys = list(groups.keys())
    rng.shuffle(group_keys)

    total_samples = len(samples)
    targets = {
        "train": int(total_samples * 0.7),
        "val": int(total_samples * 0.2),
    }
    targets["test"] = total_samples - targets["train"] - targets["val"]

    split_map: dict[str, list[Sample]] = {"train": [], "val": [], "test": []}
    split_counts = {"train": 0, "val": 0, "test": 0}

    for key in group_keys:
        group_rows = groups[key]
        remaining = {
            split: targets[split] - split_counts[split]
            for split in ("train", "val", "test")
        }
        target_split = max(remaining, key=lambda split: remaining[split])
        split_map[target_split].extend(group_rows)
        split_counts[target_split] += len(group_rows)

    return split_map


def _parse_sample_boxes(sample: Sample) -> tuple[list[list[float]], list[int]]:
    class_labels: list[int] = []
    bboxes: list[list[float]] = []
    for row in sample.yolo_lines:
        parts = row.split()
        if len(parts) != 5:
            continue
        try:
            cls = int(parts[0])
            xc, yc, bw, bh = map(float, parts[1:])
        except ValueError:
            continue
        cleaned = _sanitize_yolo_bbox(xc, yc, bw, bh)
        if cleaned is None:
            continue
        c_xc, c_yc, c_bw, c_bh = cleaned
        class_labels.append(cls)
        bboxes.append([c_xc, c_yc, c_bw, c_bh])
    return bboxes, class_labels


def _save_augmented_sample(
    *,
    augmented: dict,
    split_name: str,
    image_index: int,
    img_dir: Path,
    lbl_dir: Path,
) -> bool:
    aug_lines: list[str] = []
    for cls, box in zip(augmented["class_labels"], augmented["bboxes"]):
        xc, yc, bw, bh = map(float, box)
        cleaned = _sanitize_yolo_bbox(xc, yc, bw, bh)
        if cleaned is None:
            continue
        c_xc, c_yc, c_bw, c_bh = cleaned
        aug_lines.append(f"{int(cls)} {c_xc:.6f} {c_yc:.6f} {c_bw:.6f} {c_bh:.6f}")
    if not aug_lines:
        return False

    out_img = img_dir / f"{split_name}_{image_index:07d}.jpg"
    out_lbl = lbl_dir / f"{split_name}_{image_index:07d}.txt"
    cv2.imwrite(str(out_img), augmented["image"])
    out_lbl.write_text("\n".join(aug_lines) + "\n", encoding="utf-8")
    return True


def write_split_dataset(
    split_map: dict[str, list[Sample]],
    output_dir: Path,
    rain_aug_ratio: float,
    quality_aug_ratio: float,
    minority_aug_ratio: float,
    seed: int,
) -> None:
    ensure_clean_dir(output_dir)
    rng = random.Random(seed)

    rain_aug = A.Compose(
        [
            A.RandomRain(brightness_coefficient=0.9, drop_width=1, blur_value=3, p=0.8),
            A.MotionBlur(blur_limit=5, p=0.5),
            A.RandomBrightnessContrast(p=0.6),
        ],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]),
    )
    quality_aug = A.Compose(
        [
            A.OneOf(
                [
                    A.GaussianBlur(blur_limit=(3, 5), p=1.0),
                    A.MotionBlur(blur_limit=5, p=1.0),
                    A.GaussNoise(var_limit=(8.0, 45.0), p=1.0),
                ],
                p=0.7,
            ),
            A.RandomBrightnessContrast(brightness_limit=0.25, contrast_limit=0.25, p=0.7),
            A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=25, val_shift_limit=20, p=0.6),
            A.ImageCompression(quality_lower=45, quality_upper=95, p=0.45),
        ],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]),
    )

    train_counts = _count_boxes(split_map.get("train", []))
    minority_class: int | None = None
    if len(train_counts) >= 2:
        major = max(train_counts.values())
        minor_cls, minor_count = min(train_counts.items(), key=lambda item: item[1])
        if minor_count > 0 and (minor_count / major) < 0.75:
            minority_class = int(minor_cls)
            print(f"Minority class detected for targeted augmentation: class_{minority_class}")

    for split_name, samples in split_map.items():
        img_dir = output_dir / "images" / split_name
        lbl_dir = output_dir / "labels" / split_name
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        image_index = 0
        for sample in samples:
            ext = sample.image_path.suffix.lower()
            out_img = img_dir / f"{split_name}_{image_index:07d}{ext}"
            out_lbl = lbl_dir / f"{split_name}_{image_index:07d}.txt"
            image_index += 1

            shutil.copy2(sample.image_path, out_img)
            out_lbl.write_text("\n".join(sample.yolo_lines) + "\n", encoding="utf-8")

            if split_name != "train":
                continue

            bboxes, class_labels = _parse_sample_boxes(sample)
            if not bboxes:
                continue

            needs_aug = (
                rng.random() <= rain_aug_ratio
                or rng.random() <= quality_aug_ratio
                or (minority_class is not None and minority_class in class_labels and rng.random() <= minority_aug_ratio)
            )
            if not needs_aug:
                continue

            image = cv2.imread(str(sample.image_path))
            if image is None:
                continue

            if rng.random() <= rain_aug_ratio:
                augmented = rain_aug(image=image, bboxes=bboxes, class_labels=class_labels)
                if _save_augmented_sample(
                    augmented=augmented,
                    split_name=split_name,
                    image_index=image_index,
                    img_dir=img_dir,
                    lbl_dir=lbl_dir,
                ):
                    image_index += 1

            if rng.random() <= quality_aug_ratio:
                augmented = quality_aug(image=image, bboxes=bboxes, class_labels=class_labels)
                if _save_augmented_sample(
                    augmented=augmented,
                    split_name=split_name,
                    image_index=image_index,
                    img_dir=img_dir,
                    lbl_dir=lbl_dir,
                ):
                    image_index += 1

            if minority_class is not None and minority_class in class_labels and rng.random() <= minority_aug_ratio:
                augmented = quality_aug(image=image, bboxes=bboxes, class_labels=class_labels)
                if _save_augmented_sample(
                    augmented=augmented,
                    split_name=split_name,
                    image_index=image_index,
                    img_dir=img_dir,
                    lbl_dir=lbl_dir,
                ):
                    image_index += 1


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


def _resolve_device(device_arg: str) -> str:
    if device_arg.strip():
        return device_arg.strip()
    return "0" if torch.cuda.is_available() else "cpu"


def _print_eval_metrics(prefix: str, metrics: object) -> None:
    print(f"=== {prefix} Metrics ===")
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall: {metrics.box.mr:.4f}")


def train_model(args: argparse.Namespace, data_yaml: Path) -> Path:
    device = _resolve_device(args.device)
    model = YOLO(args.model)
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
        device=device,
        patience=args.patience,
        optimizer=args.optimizer,
        cache=args.cache,
        workers=args.workers,
        cos_lr=True,
        close_mosaic=10,
        degrees=10.0,
        fliplr=0.5,
        flipud=0.05,
        hsv_h=0.015,
        hsv_s=0.6,
        hsv_v=0.45,
        translate=0.08,
        scale=0.35,
        shear=3.0,
        perspective=0.0007,
        mosaic=0.8,
        mixup=0.1,
    )

    best_path = Path(model.trainer.best).resolve()
    best_model = YOLO(str(best_path))
    val_metrics = best_model.val(data=str(data_yaml), split="val", device=device)
    test_metrics = best_model.val(data=str(data_yaml), split="test", device=device)
    _print_eval_metrics("Validation", val_metrics)
    _print_eval_metrics("Test", test_metrics)
    return best_path


def _load_model_names(model: YOLO) -> dict[int, str]:
    raw_names = getattr(model, "names", None)
    if isinstance(raw_names, dict):
        return {int(k): str(v) for k, v in raw_names.items()}
    if isinstance(raw_names, list):
        return {idx: str(name) for idx, name in enumerate(raw_names)}
    return {0: "garbage", 1: "pothole"}


def _binary_best_threshold(y_true: list[int], y_score: list[float]) -> tuple[float, float, float, float]:
    best_threshold = 0.5
    best_f1 = -1.0
    best_precision = 0.0
    best_recall = 0.0
    for threshold in [round(v * 0.05, 2) for v in range(2, 20)]:
        tp = sum(1 for t, s in zip(y_true, y_score) if t == 1 and s >= threshold)
        fp = sum(1 for t, s in zip(y_true, y_score) if t == 0 and s >= threshold)
        fn = sum(1 for t, s in zip(y_true, y_score) if t == 1 and s < threshold)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_precision = precision
            best_recall = recall
    return best_threshold, best_f1, best_precision, best_recall


def calibrate_autotag_thresholds(model: YOLO, dataset_root: Path) -> dict[str, float]:
    names = _load_model_names(model)
    class_ids = sorted(names.keys())

    image_dir = dataset_root / "images" / "val"
    label_dir = dataset_root / "labels" / "val"
    if not image_dir.exists() or not label_dir.exists():
        return {}
    image_paths = sorted([p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES])

    truth: dict[int, list[int]] = {cid: [] for cid in class_ids}
    scores: dict[int, list[float]] = {cid: [] for cid in class_ids}

    for image_path in image_paths:
        label_path = label_dir / f"{image_path.stem}.txt"
        gt_classes = {cls for cls, _, _, _, _ in read_yolo_txt(label_path)}

        result = model.predict(
            source=str(image_path),
            conf=0.01,
            iou=0.5,
            max_det=100,
            verbose=False,
        )
        best_conf_by_class: dict[int, float] = defaultdict(float)
        if result and result[0].boxes is not None:
            cls_list = result[0].boxes.cls.cpu().tolist()
            conf_list = result[0].boxes.conf.cpu().tolist()
            for cls, conf in zip(cls_list, conf_list):
                class_id = int(cls)
                best_conf_by_class[class_id] = max(best_conf_by_class[class_id], float(conf))

        for class_id in class_ids:
            truth[class_id].append(1 if class_id in gt_classes else 0)
            scores[class_id].append(best_conf_by_class.get(class_id, 0.0))

    thresholds: dict[str, float] = {}
    print("=== Auto-tag Threshold Calibration (val split) ===")
    for class_id in class_ids:
        class_name = names[class_id]
        y_true = truth[class_id]
        y_score = scores[class_id]
        if not y_true:
            continue
        threshold, f1, precision, recall = _binary_best_threshold(y_true, y_score)
        thresholds[class_name] = threshold
        support = sum(y_true)
        print(
            f"{class_name}: threshold={threshold:.2f}, f1={f1:.4f}, "
            f"precision={precision:.4f}, recall={recall:.4f}, positives={support}"
        )
    return thresholds


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


def _resolve_output_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return Path.cwd() / path


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    args.work_dir.mkdir(parents=True, exist_ok=True)
    all_samples = collect_samples(args)
    print(f"Loaded samples: {len(all_samples)}")

    deduped, removed = dedupe_samples(all_samples)
    print(f"Removed exact duplicates: {removed}")
    print(f"Samples after dedupe: {len(deduped)}")
    _print_class_distribution("All samples", deduped)

    split_map = split_samples(deduped, seed=args.seed)
    for split_name, rows in split_map.items():
        print(f"{split_name}: {len(rows)}")
        _print_class_distribution(f"{split_name} distribution", rows)

    write_split_dataset(
        split_map=split_map,
        output_dir=args.output_dir,
        rain_aug_ratio=args.rain_aug_ratio,
        quality_aug_ratio=args.quality_aug_ratio,
        minority_aug_ratio=args.minority_aug_ratio,
        seed=args.seed,
    )
    data_yaml = write_data_yaml(args.output_dir)
    best_pt = train_model(args, data_yaml)

    copy_target = _resolve_output_path(args.copy_best_to)
    copy_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_pt, copy_target)

    thresholds_payload: dict[str, float] = {}
    if not args.skip_autotag_calibration:
        best_model = YOLO(str(best_pt))
        thresholds_payload = calibrate_autotag_thresholds(best_model, args.output_dir.resolve())
        thresholds_path = _resolve_output_path(args.thresholds_output)
        thresholds_path.parent.mkdir(parents=True, exist_ok=True)
        thresholds_path.write_text(json.dumps(thresholds_payload, indent=2), encoding="utf-8")
        print(f"Saved threshold recommendations to: {thresholds_path}")

    print("=== Training Complete ===")
    print(f"Best weights: {best_pt}")
    print(f"Copied weights to: {copy_target}")
    if thresholds_payload:
        if "garbage" in thresholds_payload:
            print(f"Recommended DETECTION_AUTOTAG_THRESHOLD_GARBAGE={thresholds_payload['garbage']:.2f}")
        if "pothole" in thresholds_payload:
            print(f"Recommended DETECTION_AUTOTAG_THRESHOLD_POTHOLE={thresholds_payload['pothole']:.2f}")


if __name__ == "__main__":
    main()
