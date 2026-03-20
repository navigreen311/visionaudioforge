"""Annotation service — CRUD, import/export, statistics."""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import Annotation
from app.models.asset import Asset


VALID_TYPES = {"bbox", "polygon", "keypoint", "segment", "label", "text"}


class AnnotationService:
    """Service layer for annotation CRUD, export/import, and stats."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def create_annotation(
        db: AsyncSession,
        asset_id: uuid.UUID,
        annotation_type: str,
        data: dict[str, Any],
        user_id: uuid.UUID,
        dataset_id: Optional[uuid.UUID] = None,
    ) -> Annotation:
        """Create a new annotation for an asset."""
        if annotation_type not in VALID_TYPES:
            raise ValueError(f"Invalid annotation_type '{annotation_type}'. Must be one of {VALID_TYPES}")

        annotation = Annotation(
            asset_id=asset_id,
            dataset_id=dataset_id,
            user_id=user_id,
            annotation_type=annotation_type,
            data=data,
        )
        db.add(annotation)
        await db.commit()
        await db.refresh(annotation)
        return annotation

    @staticmethod
    async def get_annotations(
        db: AsyncSession,
        asset_id: uuid.UUID,
    ) -> list[Annotation]:
        """Get all annotations for a specific asset."""
        result = await db.execute(
            select(Annotation).where(Annotation.asset_id == asset_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_annotation(
        db: AsyncSession,
        annotation_id: uuid.UUID,
        data: dict[str, Any],
    ) -> Annotation:
        """Update an annotation's data."""
        result = await db.execute(
            select(Annotation).where(Annotation.id == annotation_id)
        )
        annotation = result.scalar_one_or_none()
        if annotation is None:
            raise ValueError(f"Annotation {annotation_id} not found")

        annotation.data = data
        await db.commit()
        await db.refresh(annotation)
        return annotation

    @staticmethod
    async def delete_annotation(
        db: AsyncSession,
        annotation_id: uuid.UUID,
    ) -> bool:
        """Delete an annotation by ID."""
        result = await db.execute(
            select(Annotation).where(Annotation.id == annotation_id)
        )
        annotation = result.scalar_one_or_none()
        if annotation is None:
            return False

        await db.delete(annotation)
        await db.commit()
        return True

    @staticmethod
    async def get_dataset_annotations(
        db: AsyncSession,
        dataset_id: uuid.UUID,
    ) -> list[Annotation]:
        """Get all annotations for a dataset."""
        result = await db.execute(
            select(Annotation).where(Annotation.dataset_id == dataset_id)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    @staticmethod
    async def export_annotations(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        format: str = "coco",
    ) -> dict[str, Any]:
        """Export annotations in COCO, YOLO, or VOC format."""
        result = await db.execute(
            select(Annotation).where(Annotation.dataset_id == dataset_id)
        )
        annotations = list(result.scalars().all())

        # Gather unique asset IDs to build image entries
        asset_ids = list({a.asset_id for a in annotations})
        assets_result = await db.execute(
            select(Asset).where(Asset.id.in_(asset_ids))
        )
        assets = {a.id: a for a in assets_result.scalars().all()}

        if format == "coco":
            return AnnotationService._export_coco(annotations, assets)
        elif format == "yolo":
            return AnnotationService._export_yolo(annotations, assets)
        elif format == "voc":
            return AnnotationService._export_voc(annotations, assets)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    @staticmethod
    def _export_coco(
        annotations: list[Annotation],
        assets: dict[uuid.UUID, Asset],
    ) -> dict[str, Any]:
        """Convert annotations to COCO JSON format."""
        # Build category mapping from unique labels
        label_set: set[str] = set()
        for ann in annotations:
            if isinstance(ann.data, dict) and "label" in ann.data:
                label_set.add(ann.data["label"])
        label_to_id = {label: idx + 1 for idx, label in enumerate(sorted(label_set))}

        categories = [
            {"id": cid, "name": name, "supercategory": "none"}
            for name, cid in label_to_id.items()
        ]

        images = []
        for idx, (aid, asset) in enumerate(assets.items()):
            meta = asset.metadata_ or {}
            images.append({
                "id": idx + 1,
                "file_name": asset.filename,
                "width": meta.get("width", 0),
                "height": meta.get("height", 0),
            })
        asset_to_img_id = {aid: idx + 1 for idx, aid in enumerate(assets.keys())}

        coco_annotations = []
        for ann_idx, ann in enumerate(annotations):
            data = ann.data or {}
            label = data.get("label", "unknown")
            cat_id = label_to_id.get(label, 0)
            image_id = asset_to_img_id.get(ann.asset_id, 0)

            coco_ann: dict[str, Any] = {
                "id": ann_idx + 1,
                "image_id": image_id,
                "category_id": cat_id,
            }

            if ann.annotation_type == "bbox":
                coco_ann["bbox"] = [data.get("x", 0), data.get("y", 0), data.get("width", 0), data.get("height", 0)]
                coco_ann["area"] = data.get("width", 0) * data.get("height", 0)
                coco_ann["iscrowd"] = 0
            elif ann.annotation_type == "polygon":
                points = data.get("points", [])
                coco_ann["segmentation"] = [[c for pt in points for c in pt]]
                coco_ann["iscrowd"] = 0
            elif ann.annotation_type == "keypoint":
                kps = data.get("points", [])
                coco_ann["keypoints"] = []
                for kp in kps:
                    coco_ann["keypoints"].extend([kp.get("x", 0), kp.get("y", 0), 2])
                coco_ann["num_keypoints"] = len(kps)

            coco_annotations.append(coco_ann)

        return {
            "images": images,
            "annotations": coco_annotations,
            "categories": categories,
        }

    @staticmethod
    def _export_yolo(
        annotations: list[Annotation],
        assets: dict[uuid.UUID, Asset],
    ) -> dict[str, Any]:
        """Convert bbox annotations to YOLO format (class cx cy w h, normalized)."""
        label_set: set[str] = set()
        for ann in annotations:
            if isinstance(ann.data, dict) and "label" in ann.data:
                label_set.add(ann.data["label"])
        label_to_id = {label: idx for idx, label in enumerate(sorted(label_set))}

        files: dict[str, str] = {}
        for ann in annotations:
            if ann.annotation_type != "bbox":
                continue
            data = ann.data or {}
            asset = assets.get(ann.asset_id)
            if asset is None:
                continue

            meta = asset.metadata_ or {}
            img_w = meta.get("width", 1)
            img_h = meta.get("height", 1)

            x, y, w, h = data.get("x", 0), data.get("y", 0), data.get("width", 0), data.get("height", 0)
            cx = (x + w / 2) / img_w if img_w else 0
            cy = (y + h / 2) / img_h if img_h else 0
            nw = w / img_w if img_w else 0
            nh = h / img_h if img_h else 0

            label = data.get("label", "unknown")
            class_id = label_to_id.get(label, 0)

            fname = asset.filename.rsplit(".", 1)[0] + ".txt"
            line = f"{class_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}"
            if fname in files:
                files[fname] += "\n" + line
            else:
                files[fname] = line

        return {
            "format": "yolo",
            "classes": sorted(label_to_id.keys()),
            "files": files,
        }

    @staticmethod
    def _export_voc(
        annotations: list[Annotation],
        assets: dict[uuid.UUID, Asset],
    ) -> dict[str, Any]:
        """Convert bbox annotations to Pascal VOC XML format."""
        files: dict[str, str] = {}

        # Group annotations by asset
        by_asset: dict[uuid.UUID, list[Annotation]] = {}
        for ann in annotations:
            by_asset.setdefault(ann.asset_id, []).append(ann)

        for asset_id, anns in by_asset.items():
            asset = assets.get(asset_id)
            if asset is None:
                continue

            meta = asset.metadata_ or {}
            root = ET.Element("annotation")
            ET.SubElement(root, "filename").text = asset.filename
            size_el = ET.SubElement(root, "size")
            ET.SubElement(size_el, "width").text = str(meta.get("width", 0))
            ET.SubElement(size_el, "height").text = str(meta.get("height", 0))
            ET.SubElement(size_el, "depth").text = str(meta.get("depth", 3))

            for ann in anns:
                if ann.annotation_type != "bbox":
                    continue
                data = ann.data or {}
                obj_el = ET.SubElement(root, "object")
                ET.SubElement(obj_el, "name").text = data.get("label", "unknown")
                bndbox = ET.SubElement(obj_el, "bndbox")
                x, y = data.get("x", 0), data.get("y", 0)
                w, h = data.get("width", 0), data.get("height", 0)
                ET.SubElement(bndbox, "xmin").text = str(int(x))
                ET.SubElement(bndbox, "ymin").text = str(int(y))
                ET.SubElement(bndbox, "xmax").text = str(int(x + w))
                ET.SubElement(bndbox, "ymax").text = str(int(y + h))

            fname = asset.filename.rsplit(".", 1)[0] + ".xml"
            files[fname] = ET.tostring(root, encoding="unicode")

        return {"format": "voc", "files": files}

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    @staticmethod
    async def import_annotations(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        data: dict[str, Any],
        format: str = "coco",
    ) -> dict[str, int]:
        """Import annotations from COCO (or other) format."""
        if format != "coco":
            raise ValueError(f"Import format '{format}' not yet supported. Use 'coco'.")

        images = data.get("images", [])
        coco_annotations = data.get("annotations", [])
        categories = data.get("categories", [])

        cat_map = {c["id"]: c["name"] for c in categories}

        # Map image IDs to asset filenames -> look up asset by filename
        img_map: dict[int, dict] = {img["id"]: img for img in images}

        imported = 0
        for coco_ann in coco_annotations:
            img_info = img_map.get(coco_ann.get("image_id"))
            if img_info is None:
                continue

            # Try to find asset by filename
            result = await db.execute(
                select(Asset).where(Asset.filename == img_info.get("file_name")).limit(1)
            )
            asset = result.scalar_one_or_none()
            if asset is None:
                continue

            label = cat_map.get(coco_ann.get("category_id"), "unknown")

            # Determine annotation type from COCO data
            if "bbox" in coco_ann and coco_ann["bbox"]:
                bbox = coco_ann["bbox"]
                ann_data = {
                    "x": bbox[0],
                    "y": bbox[1],
                    "width": bbox[2],
                    "height": bbox[3],
                    "label": label,
                }
                ann_type = "bbox"
            elif "segmentation" in coco_ann and coco_ann["segmentation"]:
                seg = coco_ann["segmentation"]
                points_flat = seg[0] if isinstance(seg, list) and len(seg) > 0 else []
                points = [[points_flat[i], points_flat[i + 1]] for i in range(0, len(points_flat), 2)]
                ann_data = {"points": points, "label": label}
                ann_type = "polygon"
            elif "keypoints" in coco_ann and coco_ann["keypoints"]:
                kps = coco_ann["keypoints"]
                points = []
                for i in range(0, len(kps), 3):
                    points.append({"name": f"kp_{i // 3}", "x": kps[i], "y": kps[i + 1]})
                ann_data = {"points": points, "label": label}
                ann_type = "keypoint"
            else:
                ann_data = {"label": label, "confidence": 1.0}
                ann_type = "label"

            annotation = Annotation(
                asset_id=asset.id,
                dataset_id=dataset_id,
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                annotation_type=ann_type,
                data=ann_data,
            )
            db.add(annotation)
            imported += 1

        await db.commit()
        return {"imported": imported}

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @staticmethod
    async def annotation_stats(
        db: AsyncSession,
        dataset_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Compute annotation statistics for a dataset."""
        result = await db.execute(
            select(Annotation).where(Annotation.dataset_id == dataset_id)
        )
        annotations = list(result.scalars().all())

        total = len(annotations)
        by_type: dict[str, int] = dict(Counter(a.annotation_type for a in annotations))
        by_label: dict[str, int] = dict(
            Counter(
                a.data.get("label", "unknown")
                for a in annotations
                if isinstance(a.data, dict) and "label" in a.data
            )
        )

        # Calculate annotated percentage (unique assets with annotations / total assets in dataset)
        annotated_asset_ids = {a.asset_id for a in annotations}

        # Count total assets linked via dataset — simple approach: use asset count
        total_assets_result = await db.execute(
            select(func.count()).select_from(Asset)
        )
        total_assets = total_assets_result.scalar() or 0
        annotated_pct = (len(annotated_asset_ids) / total_assets * 100) if total_assets else 0.0

        return {
            "total": total,
            "by_type": by_type,
            "by_label": by_label,
            "annotated_pct": round(annotated_pct, 2),
        }
