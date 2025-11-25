"""
Crack detection inference service
Refactored from dual_infer_severity_v4_plus3.py with async support
"""
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import cv2
import numpy as np
from ultralytics import YOLO

from ..schemas.inference import (
    CrackRegionSchema,
    DetectionResultSchema,
    ImageResultSchema,
    InferenceConfig,
)


class CrackMeasurement:
    """Crack measurement using skeleton-based approach"""

    @staticmethod
    def _morphological_skeleton(mask_uint8: np.ndarray) -> np.ndarray:
        """Extract skeleton using OpenCV morphological operations"""
        img = (mask_uint8 > 0).astype(np.uint8) * 255
        skel = np.zeros_like(img)
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

        while True:
            eroded = cv2.erode(img, kernel)
            opened = cv2.morphologyEx(eroded, cv2.MORPH_OPEN, kernel)
            temp = cv2.subtract(eroded, opened)
            skel = cv2.bitwise_or(skel, temp)
            img = eroded.copy()
            if cv2.countNonZero(img) == 0:
                break

        return (skel > 0).astype(np.uint8)

    @staticmethod
    def measure_crack(
        mask: np.ndarray, mm_per_pixel: float
    ) -> Optional[CrackRegionSchema]:
        """
        Measure crack using distance transform + skeleton

        Filters:
        1) Minimum length 20mm, width 1mm, area 50mm²
        2) Remove straight horizontal/vertical lines (ribs, edges)
        """
        mask_uint8 = (mask > 0).astype(np.uint8)
        if mask_uint8.sum() == 0:
            return None

        # Area
        area_px = float(cv2.countNonZero(mask_uint8))
        area_mm2 = area_px * (mm_per_pixel ** 2)

        # Distance Transform
        dist = cv2.distanceTransform(mask_uint8, cv2.DIST_L2, 5)

        # Skeleton
        skeleton = CrackMeasurement._morphological_skeleton(mask_uint8)
        ys, xs = np.where(skeleton > 0)
        if len(xs) == 0:
            return None

        local_widths_px = 2.0 * dist[ys, xs]
        local_widths_mm = local_widths_px * mm_per_pixel
        max_width_mm = float(local_widths_mm.max())
        mean_width_mm = float(local_widths_mm.mean())

        length_px = len(xs)
        length_mm = float(length_px * mm_per_pixel)

        # Filter 1: Basic mm thresholds
        if length_mm < 20.0 or max_width_mm < 1.0 or area_mm2 < 50.0:
            return None

        # Get contour polygon
        contours, _ = cv2.findContours(
            mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None
        main_contour = max(contours, key=cv2.contourArea)
        poly = main_contour.reshape(-1, 2).tolist()
        flat = [int(x) for xy in poly for x in xy]

        # Filter 2: Straightness & axis alignment (remove ribs/edges)
        dx = float(xs.max() - xs.min())
        dy = float(ys.max() - ys.min())
        straight_dist = float(np.hypot(dx, dy))
        straight_ratio = straight_dist / max(float(length_px), 1.0)

        rect = cv2.minAreaRect(main_contour)
        (cx, cy), (w_rect, h_rect), theta = rect
        long_side = max(w_rect, h_rect)
        short_side = max(min(w_rect, h_rect), 1e-3)
        aspect = long_side / short_side

        angle = theta if w_rect >= h_rect else theta + 90.0
        angle = abs(angle)
        axis_aligned = (angle < 10.0) or (90.0 - angle < 10.0)

        # Very straight + axis-aligned + elongated = likely false positive
        if straight_ratio > 0.9 and aspect > 10.0 and axis_aligned:
            return None

        severity = length_mm * max_width_mm

        return CrackRegionSchema(
            polygon=flat,
            length_mm=length_mm,
            width_mm=max_width_mm,
            mean_width_mm=mean_width_mm,
            area_mm2=area_mm2,
            severity=severity,
        )


class InferenceService:
    """Main inference service for crack detection"""

    def __init__(self, config: InferenceConfig, crack_model_path: str, det_model_path: str):
        self.config = config
        self.crack_model = YOLO(crack_model_path)
        self.det_model = YOLO(det_model_path)

    async def infer_image(self, img_path: Path) -> ImageResultSchema:
        """
        Run inference on a single image (async wrapper)

        Returns:
            ImageResultSchema with cracks and detections
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._infer_image_sync, img_path)

    def _infer_image_sync(self, img_path: Path) -> ImageResultSchema:
        """Synchronous inference (runs in thread pool)"""
        img = cv2.imread(str(img_path))
        if img is None:
            raise RuntimeError(f"Cannot read image: {img_path}")
        h, w = img.shape[:2]

        # 1) Crack segmentation
        crack_pred = self.crack_model.predict(
            source=str(img_path),
            imgsz=self.config.imgsz,
            conf=self.config.crack_conf,
            verbose=False,
        )[0]

        crack_regions: List[CrackRegionSchema] = []
        if crack_pred.masks is not None:
            for m in crack_pred.masks.data:
                mask = m.cpu().numpy()
                mask = cv2.resize(mask, (w, h))
                mask_bin = (mask > 0.5).astype(np.uint8)

                # Filter small masks
                if np.sum(mask_bin) < self.config.min_mask_area_px:
                    continue

                region = CrackMeasurement.measure_crack(mask_bin, self.config.mm_per_pixel)
                if region:
                    crack_regions.append(region)

        # 2) Multi-defect detection
        det_pred = self.det_model.predict(
            source=str(img_path),
            imgsz=self.config.imgsz,
            conf=self.config.det_conf,
            verbose=False,
        )[0]
        class_names = det_pred.names

        detections: List[DetectionResultSchema] = []
        if det_pred.boxes is not None and len(det_pred.boxes) > 0:
            for box, cls_id, conf in zip(
                det_pred.boxes.xyxy,
                det_pred.boxes.cls,
                det_pred.boxes.conf,
            ):
                cid = int(cls_id)
                cname = class_names.get(cid, str(cid))

                # Skip crack (handled by segmentation)
                if cname == "crack":
                    continue

                if conf < self.config.det_conf:
                    continue

                x1, y1, x2, y2 = map(float, box.tolist())
                width_px = x2 - x1
                height_px = y2 - y1

                # Filter small boxes
                if width_px < self.config.min_box_px or height_px < self.config.min_box_px:
                    continue

                area_px = max(width_px, 0.0) * max(height_px, 0.0)
                width_mm = width_px * self.config.mm_per_pixel
                height_mm = height_px * self.config.mm_per_pixel
                area_mm2 = area_px * (self.config.mm_per_pixel ** 2)

                detections.append(
                    DetectionResultSchema(
                        bbox_xyxy=[x1, y1, x2, y2],
                        class_id=cid,
                        class_name=cname,
                        confidence=float(conf),
                        width_mm=width_mm,
                        height_mm=height_mm,
                        area_mm2=area_mm2,
                        severity=area_mm2,
                    )
                )

        return ImageResultSchema(
            image=img_path.name,
            full_path=str(img_path),
            width=w,
            height=h,
            cracks=crack_regions,
            detections=detections,
        )

    async def infer_batch(
        self, img_paths: List[Path], progress_callback=None
    ) -> List[ImageResultSchema]:
        """
        Run inference on multiple images with progress tracking

        Args:
            img_paths: List of image paths
            progress_callback: Optional callback(current, total) for progress

        Returns:
            List of ImageResultSchema
        """
        results = []
        total = len(img_paths)

        for idx, img_path in enumerate(img_paths, 1):
            try:
                result = await self.infer_image(img_path)
                results.append(result)

                if progress_callback:
                    await progress_callback(idx, total)

            except Exception as e:
                print(f"Error processing {img_path}: {e}")
                # Continue with other images

        return results
