#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
dual_infer_severity_v4_plus3.py

Crack segmentation + multi-defect detection + severity ranking +
CSV / JSON / HTML / PDF 리포트 생성 (skeleton 기반 crack 계측, v4_plus3)

주요 기능
- Crack: YOLOv8-seg + skeleton 기반 계측
- Multi-defect: YOLOv8-det (spall, rust 등)
- 멀리 있는 작은 결함 자동 필터링 (픽셀·mm 기준)
- 직선형 / 세로 리브 / 배경 산 능선 등 오검출 제거용 필터 추가
- severe 이미지: 사진당 가장 심각한 결함 1개 + ZOOM 인셋 자동 생성
- CRACK 라벨: 흰 바탕 + 짙은 빨강 굵은 글씨
- 기타 결함 라벨: 흰 바탕 + 파랑/주황/보라 글씨
- HTML: 썸네일 클릭 후 마우스 휠 확대 / 드래그 이동
- PDF: 목감 스타일 표지 + 심각 결함 페이지
"""

import argparse
import html
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import cv2
import numpy as np
from tqdm import tqdm
from ultralytics import YOLO

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# =========================
# Constants
# =========================

# Visualization constants
ZOOM_PADDING_PX = 80
ZOOM_SIZE_RATIO = 0.25
RANK_BADGE_FONT_SCALE = 1.0
RANK_BADGE_FONT_THICKNESS = 2

# Crack measurement thresholds
MIN_CRACK_LENGTH_MM = 20.0
MIN_CRACK_WIDTH_MM = 1.0
MIN_CRACK_AREA_MM2 = 50.0

# False positive filtering
STRAIGHTNESS_THRESHOLD = 0.9
ASPECT_RATIO_THRESHOLD = 10.0
ANGLE_ALIGNMENT_THRESHOLD = 10.0

# Label styling
CRACK_LABEL_FONT_SCALE = 1.3
CRACK_LABEL_FONT_THICKNESS = 3
DETECTION_LABEL_FONT_SCALE = 1.2
DETECTION_LABEL_FONT_THICKNESS = 3
SEVERE_LABEL_FONT_SCALE = 1.6
SEVERE_LABEL_FONT_THICKNESS = 3

# =========================
# 한글 폰트 등록 (가능하면 나눔고딕 사용)
# =========================
FONT_AVAILABLE = False
try:
    pdfmetrics.registerFont(
        TTFont("NanumGothic", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
    )
    pdfmetrics.registerFont(
        TTFont("NanumGothic-Bold", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
    )
    FONT_AVAILABLE = True
except Exception as e:
    print("[WARN] NanumGothic font register failed:", e)

# =========================
# 기본 모델 경로 (환경 변수 우선, 없으면 기본값)
# =========================
DEFAULT_CRACK_MODEL = os.getenv(
    "CRACK_MODEL_PATH",
    "./models/crack_seg/best.pt"
)
DEFAULT_DET_MODEL = os.getenv(
    "DET_MODEL_PATH",
    "./models/detection/best.pt"
)

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".JPG", ".JPEG", ".PNG", ".BMP", ".WEBP"}

# =========================
# 시각화 색상 설정
# =========================

# detected 폴더: 바운딩 박스는 기본 노랑
BOUNDING_BOX_COLOR = (0, 255, 255)  # BGR

# 클래스별 stroke 색상 (detected / severe 공통 기본 팔레트)
CLASS_STROKE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "crack": (0, 0, 255),             # 빨강
    "spall": (255, 0, 0),             # 파랑
    "spalling": (255, 0, 0),
    "rust": (0, 140, 255),            # 주황 (녹)
    "corrosion": (0, 140, 255),
    "rebar_exposed": (211, 0, 148),   # 보라
    "rebar_exposure": (211, 0, 148),
}

# severe 전용: non-crack bounding box 짙은 파랑
SEVERE_BOX_COLOR = (255, 0, 0)  # deep blue (BGR)
SEVERE_LABEL_TEXT_RED = (0, 0, 200)     # 짙은 빨강
SEVERE_LABEL_TEXT_BLUE = (255, 0, 0)    # 파랑

# =========================
# Dataclasses
# =========================
@dataclass
class CrackRegion:
    polygon: List[int]           # [x1,y1,x2,y2,...] - contour polyline
    length_mm: float             # skeleton 기반 길이
    width_mm: float              # 최대 폭
    mean_width_mm: float         # 평균 폭
    area_mm2: float
    severity: float              # length_mm * width_mm


@dataclass
class DetectionResult:
    bbox_xyxy: List[float]
    class_id: int
    class_name: str
    confidence: float
    width_mm: float
    height_mm: float
    area_mm2: float
    severity: float              # area_mm2


@dataclass
class ImageResult:
    image: str
    full_path: str
    width: int
    height: int
    cracks: List[CrackRegion]
    detections: List[DetectionResult]


@dataclass
class DefectFinding:
    building: str
    image: str
    image_path: str          # 원본 이미지 경로
    type: str                # "crack" or class_name
    severity: float
    length_mm: Optional[float]
    width_mm: Optional[float]
    area_mm2: Optional[float]
    extra: Dict[str, Any]
    bbox_xyxy: Optional[List[float]] = None  # detection 용
    polygon: Optional[List[int]] = None      # crack 용


# =========================
# 유틸 함수
# =========================
def collect_images(root: Path) -> List[Path]:
    """
    Recursively collect all image files from a directory.

    Args:
        root: Root directory to search for images

    Returns:
        Sorted list of image file paths
    """
    imgs: List[Path] = []
    for p in root.rglob("*"):
        if p.suffix in IMG_EXTS:
            imgs.append(p)
    return sorted(imgs)


# ---------------- skeleton 기반 crack 계측 ----------------
def _morphological_skeleton(mask_uint8: np.ndarray) -> np.ndarray:
    """
    Extract morphological skeleton using OpenCV operations.

    Uses iterative erosion and morphological opening to extract
    the skeleton centerline of a binary mask.

    Args:
        mask_uint8: Binary mask (0/1 or 0/255)

    Returns:
        Binary skeleton image (0/1)
    """
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


def _calculate_skeleton_length(skeleton_points: np.ndarray) -> float:
    """
    Calculate accurate skeleton length by summing distances between adjacent pixels.

    This is more accurate than simply counting pixels, as it accounts for
    diagonal connections (sqrt(2) vs 1.0 pixel distance).

    Args:
        skeleton_points: Array of shape (N, 2) containing (x, y) coordinates

    Returns:
        Total skeleton length in pixels
    """
    if len(skeleton_points) <= 1:
        return float(len(skeleton_points))

    # Calculate distances between consecutive points
    # Note: This is an approximation. For perfect accuracy, we'd need
    # to trace the actual connected skeleton path, but this provides
    # a good estimate.
    diffs = np.diff(skeleton_points, axis=0)
    distances = np.sqrt((diffs ** 2).sum(axis=1))
    total_length = np.sum(distances)

    return float(total_length)


def measure_crack_skeleton(mask: np.ndarray, mm_per_pixel: float) -> Optional[CrackRegion]:
    """
    Measure crack dimensions using Distance Transform and skeleton analysis.

    Implements multi-stage false positive filtering to remove:
    1. Small defects (minimum size thresholds)
    2. Linear patterns (ribs, building edges, background lines)

    Filtering criteria:
    - Minimum length: 20mm, width: 1mm, area: 50mm²
    - Rejects very straight (>0.9) + axis-aligned patterns with high aspect ratio (>10)

    Args:
        mask: Binary mask of crack region
        mm_per_pixel: Ground Sample Distance (GSD) for mm conversion

    Returns:
        CrackRegion object with measurements, or None if filtered out
    """
    mask_uint8 = (mask > 0).astype(np.uint8)
    if mask_uint8.sum() == 0:
        return None

    # Calculate area
    area_px = float(cv2.countNonZero(mask_uint8))
    area_mm2 = area_px * (mm_per_pixel ** 2)

    # Distance Transform for width measurement
    dist = cv2.distanceTransform(mask_uint8, cv2.DIST_L2, 5)

    # Extract skeleton
    skeleton = _morphological_skeleton(mask_uint8)
    ys, xs = np.where(skeleton > 0)
    if len(xs) == 0:
        return None

    # Measure width using distance transform
    local_widths_px = 2.0 * dist[ys, xs]
    local_widths_mm = local_widths_px * mm_per_pixel
    max_width_mm = float(local_widths_mm.max())
    mean_width_mm = float(local_widths_mm.mean())

    # Calculate accurate skeleton length
    skeleton_points = np.column_stack((xs, ys))
    length_px = _calculate_skeleton_length(skeleton_points)
    length_mm = length_px * mm_per_pixel

    # ---------- Stage 1: Basic size filters ----------
    if length_mm < MIN_CRACK_LENGTH_MM:
        return None
    if max_width_mm < MIN_CRACK_WIDTH_MM:
        return None
    if area_mm2 < MIN_CRACK_AREA_MM2:
        return None

    # Get contour polygon for visualization and linearity analysis
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    main_contour = max(contours, key=cv2.contourArea)
    poly = main_contour.reshape(-1, 2).tolist()
    flat = [int(x) for xy in poly for x in xy]

    # ---------- Stage 2: Linearity and orientation filters ----------
    # Calculate straightness ratio: diagonal distance / skeleton length
    dx = float(xs.max() - xs.min())
    dy = float(ys.max() - ys.min())
    straight_dist = np.hypot(dx, dy)
    straight_ratio = straight_dist / max(length_px, 1.0)  # 0~1

    # Analyze contour orientation using minAreaRect
    rect = cv2.minAreaRect(main_contour)
    (cx, cy), (w_rect, h_rect), theta = rect
    long_side = max(w_rect, h_rect)
    short_side = max(min(w_rect, h_rect), 1e-3)
    aspect = long_side / short_side

    # Normalize angle to 0-90 range
    angle = abs(theta if w_rect >= h_rect else theta + 90.0)

    # Check if aligned with axes (horizontal or vertical)
    axis_aligned = (angle < ANGLE_ALIGNMENT_THRESHOLD) or \
                   (90.0 - angle < ANGLE_ALIGNMENT_THRESHOLD)

    # Filter out straight, axis-aligned patterns with high aspect ratio
    # (likely ribs, building edges, or background lines)
    if (straight_ratio > STRAIGHTNESS_THRESHOLD and
        aspect > ASPECT_RATIO_THRESHOLD and
        axis_aligned):
        return None

    # Calculate severity index (length × max_width)
    severity = length_mm * max_width_mm

    return CrackRegion(
        polygon=flat,
        length_mm=length_mm,
        width_mm=max_width_mm,
        mean_width_mm=mean_width_mm,
        area_mm2=area_mm2,
        severity=severity,
    )


# =========================
# Dual Model Inferencer
# =========================
class DualModelInferencer:
    """
    Dual-model inference engine for crack segmentation and multi-defect detection.

    Combines YOLOv8 segmentation (for cracks) and detection (for other defects)
    with automatic false positive filtering and metric calculation.
    """

    def __init__(
        self,
        crack_model_path: str,
        det_model_path: str,
        imgsz: int = 1024,
        crack_conf: float = 0.25,
        det_conf: float = 0.35,
        mm_per_pixel: float = 1.0,
        crack_measure_mode: str = "skeleton",
        min_box_px: int = 40,
        min_mask_area_px: int = 250,
    ):
        """
        Initialize dual-model inferencer.

        Args:
            crack_model_path: Path to YOLOv8 segmentation model for cracks
            det_model_path: Path to YOLOv8 detection model for other defects
            imgsz: Input image size for models
            crack_conf: Confidence threshold for crack segmentation
            det_conf: Confidence threshold for detection
            mm_per_pixel: Ground Sample Distance (GSD)
            crack_measure_mode: Measurement mode (currently only "skeleton")
            min_box_px: Minimum bounding box size (filters distant small defects)
            min_mask_area_px: Minimum mask area (filters distant small cracks)
        """
        self.crack_model = YOLO(crack_model_path)
        self.det_model = YOLO(det_model_path)
        self.imgsz = imgsz
        self.crack_conf = crack_conf
        self.det_conf = det_conf
        self.mm_per_pixel = mm_per_pixel
        self.crack_measure_mode = crack_measure_mode
        self.min_box_px = min_box_px
        self.min_mask_area_px = min_mask_area_px

    def _measure_crack(self, mask_bin: np.ndarray) -> Optional[CrackRegion]:
        """Measure crack dimensions from binary mask."""
        return measure_crack_skeleton(mask_bin, self.mm_per_pixel)

    def infer_one(self, img_path: Path) -> ImageResult:
        """
        Run inference on a single image.

        Args:
            img_path: Path to input image

        Returns:
            ImageResult containing detected cracks and defects

        Raises:
            RuntimeError: If image cannot be read
        """
        # Load image once
        img = cv2.imread(str(img_path))
        if img is None:
            raise RuntimeError(f"Cannot read image: {img_path}")
        h, w = img.shape[:2]

        # 1) Crack segmentation - pass image array directly
        crack_pred = self.crack_model.predict(
            source=img,  # Pass image array instead of path
            imgsz=self.imgsz,
            conf=self.crack_conf,
            verbose=False,
        )[0]

        crack_regions: List[CrackRegion] = []
        if crack_pred.masks is not None:
            for m in crack_pred.masks.data:
                mask = m.cpu().numpy()
                mask = cv2.resize(mask, (w, h))
                mask_bin = (mask > 0.5).astype(np.uint8)

                # Filter out small masks (distant noise)
                if np.sum(mask_bin) < self.min_mask_area_px:
                    continue

                region = self._measure_crack(mask_bin)
                if region:
                    crack_regions.append(region)

        # 2) Multi-defect detection - pass image array directly
        det_pred = self.det_model.predict(
            source=img,  # Pass image array instead of path
            imgsz=self.imgsz,
            conf=self.det_conf,
            verbose=False,
        )[0]
        class_names = det_pred.names

        detections: List[DetectionResult] = []
        if det_pred.boxes is not None and len(det_pred.boxes) > 0:
            for box, cls_id, conf in zip(
                det_pred.boxes.xyxy,
                det_pred.boxes.cls,
                det_pred.boxes.conf,
            ):
                cid = int(cls_id)
                cname = class_names.get(cid, str(cid))

                # Skip cracks (handled by segmentation model)
                if cname == "crack":
                    continue

                if conf < self.det_conf:
                    continue

                x1, y1, x2, y2 = map(float, box.tolist())
                width_px = x2 - x1
                height_px = y2 - y1

                # Filter out small boxes (distant defects)
                if width_px < self.min_box_px or height_px < self.min_box_px:
                    continue

                area_px = max(width_px, 0.0) * max(height_px, 0.0)

                width_mm = width_px * self.mm_per_pixel
                height_mm = height_px * self.mm_per_pixel
                area_mm2 = area_px * (self.mm_per_pixel ** 2)

                severity = area_mm2

                detections.append(
                    DetectionResult(
                        bbox_xyxy=[x1, y1, x2, y2],
                        class_id=cid,
                        class_name=cname,
                        confidence=float(conf),
                        width_mm=width_mm,
                        height_mm=height_mm,
                        area_mm2=area_mm2,
                        severity=severity,
                    )
                )

        return ImageResult(
            image=img_path.name,
            full_path=str(img_path),
            width=w,
            height=h,
            cracks=crack_regions,
            detections=detections,
        )

    @staticmethod
    def visualize(img: np.ndarray, res: ImageResult) -> np.ndarray:
        """
        Visualize all detected defects on image (for 'detected' folder).

        - Cracks: Red polygon + white background label with dark red text
        - Other defects: Yellow bounding box + class-specific stroke color +
          white background label with colored text

        Args:
            img: Input image (BGR)
            res: ImageResult containing detected defects

        Returns:
            Annotated image
        """
        vis = img.copy()

        # Draw crack polygons
        for c in res.cracks:
            pts = np.array(c.polygon, dtype=np.int32).reshape(-1, 2)

            # Draw skeleton contour
            color = CLASS_STROKE_COLORS.get("crack", (0, 0, 255))
            cv2.polylines(vis, [pts], True, color, 4)

            # Calculate label position from bounding rect
            x, y, w_rect, h_rect = cv2.boundingRect(pts)
            label_x = int(x)
            label_y = max(0, int(y) - 8)

            label = "CRACK"
            (tw, th), _ = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                CRACK_LABEL_FONT_SCALE,
                CRACK_LABEL_FONT_THICKNESS
            )

            # Draw white background + red text label
            bg_x1 = label_x
            bg_y1 = max(0, label_y - th - 10)
            bg_x2 = label_x + tw + 14
            bg_y2 = label_y

            cv2.rectangle(vis, (bg_x1, bg_y1), (bg_x2, bg_y2), (255, 255, 255), -1)
            cv2.rectangle(vis, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 255), 2)
            cv2.putText(
                vis,
                label,
                (bg_x1 + 6, bg_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                CRACK_LABEL_FONT_SCALE,
                SEVERE_LABEL_TEXT_RED,
                CRACK_LABEL_FONT_THICKNESS,
            )

        # Draw detection boxes (spall, rust, rebar_exposed, etc.)
        for d in res.detections:
            x1, y1, x2, y2 = map(int, d.bbox_xyxy)

            # Yellow outer box + class-specific stroke
            cv2.rectangle(vis, (x1, y1), (x2, y2), BOUNDING_BOX_COLOR, 4)

            stroke_color = CLASS_STROKE_COLORS.get(d.class_name, (0, 255, 0))
            cv2.rectangle(vis, (x1 + 3, y1 + 3), (x2 - 3, y2 - 3), stroke_color, 3)

            # Draw label
            label = d.class_name.upper()
            (tw, th), _ = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                DETECTION_LABEL_FONT_SCALE,
                DETECTION_LABEL_FONT_THICKNESS
            )
            y_text = max(0, y1 - th - 10)

            bg_x1 = x1
            bg_y1 = max(0, y_text)
            bg_x2 = x1 + tw + 16
            bg_y2 = bg_y1 + th + 10

            cv2.rectangle(vis, (bg_x1, bg_y1), (bg_x2, bg_y2), (255, 255, 255), -1)
            cv2.rectangle(vis, (bg_x1, bg_y1), (bg_x2, bg_y2), stroke_color, 2)
            cv2.putText(
                vis,
                label,
                (bg_x1 + 6, bg_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                DETECTION_LABEL_FONT_SCALE,
                stroke_color,
                DETECTION_LABEL_FONT_THICKNESS,
            )

        return vis


# =========================
# severe 이미지 시각화 (1장당 1결함 + ZOOM 인셋)
# =========================
def draw_rank_badge(img: np.ndarray, rank: int) -> None:
    """
    Draw yellow rank badge in top-left corner.

    Modifies image in-place.

    Args:
        img: Image to annotate (BGR)
        rank: Rank number to display
    """
    label = str(rank)
    (tw, th), _ = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        RANK_BADGE_FONT_SCALE,
        RANK_BADGE_FONT_THICKNESS
    )
    x1, y1 = 0, 0
    x2, y2 = x1 + tw + 18, y1 + th + 14

    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
    cv2.putText(
        img,
        label,
        (x1 + 6, y1 + th + 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        RANK_BADGE_FONT_SCALE,
        (0, 255, 255),
        RANK_BADGE_FONT_THICKNESS,
    )


def draw_main_finding_on_image(base: np.ndarray, finding: DefectFinding) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """
    Annotate image with main defect finding (for severe images).

    - Crack: Red skeleton contour + white background label with dark red text
    - Other: Deep blue bounding box + white background label with blue text

    Args:
        base: Input image (BGR)
        finding: Defect finding to visualize

    Returns:
        Tuple of (annotated_image, defect_bbox_xyxy)
    """
    vis = base.copy()
    h, w = vis.shape[:2]

    if finding.type == "crack" and finding.polygon:
        pts = np.array(finding.polygon, dtype=np.int32).reshape(-1, 2)
        color = CLASS_STROKE_COLORS.get("crack", (0, 0, 255))
        cv2.polylines(vis, [pts], True, color, 5)

        # Get bounding box from contour
        x, y, width, height = cv2.boundingRect(pts)
        x1, y1, x2, y2 = x, y, x + width, y + height
        bbox = (x1, y1, x2, y2)

        label = finding.type.upper()
        (tw, th), _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            SEVERE_LABEL_FONT_SCALE,
            SEVERE_LABEL_FONT_THICKNESS
        )
        y_text = max(0, y1 - th - 16)

        cv2.rectangle(
            vis,
            (x1, y_text),
            (x1 + tw + 22, y_text + th + 20),
            (255, 255, 255),
            -1,
        )
        cv2.rectangle(
            vis,
            (x1, y_text),
            (x1 + tw + 22, y_text + th + 20),
            SEVERE_BOX_COLOR,
            2,
        )
        cv2.putText(
            vis,
            label,
            (x1 + 8, y_text + th + 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            SEVERE_LABEL_FONT_SCALE,
            SEVERE_LABEL_TEXT_RED,
            SEVERE_LABEL_FONT_THICKNESS,
        )
    elif finding.bbox_xyxy:
        x1, y1, x2, y2 = map(int, finding.bbox_xyxy)
        bbox = (x1, y1, x2, y2)

        # Draw deep blue bounding box
        cv2.rectangle(vis, (x1, y1), (x2, y2), SEVERE_BOX_COLOR, 6)

        label = finding.type.upper()
        (tw, th), _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            SEVERE_LABEL_FONT_SCALE,
            SEVERE_LABEL_FONT_THICKNESS
        )
        y_text = max(0, y1 - th - 16)

        cv2.rectangle(
            vis,
            (x1, y_text),
            (x1 + tw + 22, y_text + th + 20),
            (255, 255, 255),
            -1,
        )
        cv2.rectangle(
            vis,
            (x1, y_text),
            (x1 + tw + 22, y_text + th + 20),
            SEVERE_BOX_COLOR,
            2,
        )
        cv2.putText(
            vis,
            label,
            (x1 + 8, y_text + th + 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            SEVERE_LABEL_FONT_SCALE,
            SEVERE_LABEL_TEXT_BLUE,
            SEVERE_LABEL_FONT_THICKNESS,
        )
    else:
        bbox = (0, 0, w, h)

    return vis, bbox


def add_zoom_inset(img: np.ndarray, bbox: Tuple[int, int, int, int], finding_type: str) -> np.ndarray:
    """
    Add zoomed inset of defect region to bottom-left corner.

    Crops defect area with padding, resizes to ~25% of image width,
    and overlays in bottom-left corner with border and label.

    Args:
        img: Input image (BGR)
        bbox: Defect bounding box (x1, y1, x2, y2)
        finding_type: Type of defect (for label)

    Returns:
        Image with zoom inset overlay
    """
    h, w = img.shape[:2]
    x1, y1, x2, y2 = bbox

    # Add padding around defect
    x1p = max(0, x1 - ZOOM_PADDING_PX)
    y1p = max(0, y1 - ZOOM_PADDING_PX)
    x2p = min(w, x2 + ZOOM_PADDING_PX)
    y2p = min(h, y2 + ZOOM_PADDING_PX)

    if x2p <= x1p or y2p <= y1p:
        return img

    crop = img[y1p:y2p, x1p:x2p].copy()

    # Resize to target width (25% of image width)
    target_w = int(w * ZOOM_SIZE_RATIO)
    scale = target_w / max(crop.shape[1], 1)
    target_h = int(crop.shape[0] * scale)
    crop_resized = cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

    # Place in bottom-left corner
    x0 = 10
    y0 = h - target_h - 10
    overlay = img.copy()
    overlay[y0:y0 + target_h, x0:x0 + target_w] = crop_resized

    # Draw border
    cv2.rectangle(
        overlay,
        (x0, y0),
        (x0 + target_w, y0 + target_h),
        SEVERE_BOX_COLOR,
        3,
    )

    # Draw label
    label = f"ZOOM - {finding_type.upper()}"
    font_scale = 0.9
    font_th = 2
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_th)
    lx1, ly1 = x0, y0 - th - 8
    lx2, ly2 = x0 + tw + 14, y0 - 2

    cv2.rectangle(overlay, (lx1, ly1), (lx2, ly2), (255, 255, 255), -1)
    cv2.rectangle(overlay, (lx1, ly1), (lx2, ly2), SEVERE_BOX_COLOR, 2)
    cv2.putText(
        overlay,
        label,
        (lx1 + 6, ly2 - 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        SEVERE_LABEL_TEXT_RED,
        font_th,
    )

    return overlay


def make_severe_image(base_img: np.ndarray, finding: DefectFinding, rank: int) -> np.ndarray:
    """
    Create final severe defect visualization image.

    Combines:
    - Top-left yellow rank badge
    - Main defect annotation
    - Bottom-left zoom inset

    Args:
        base_img: Input image (BGR)
        finding: Defect finding to visualize
        rank: Rank number (for badge)

    Returns:
        Fully annotated severe defect image
    """
    vis, bbox = draw_main_finding_on_image(base_img, finding)
    vis = add_zoom_inset(vis, bbox, finding.type)
    draw_rank_badge(vis, rank)
    return vis


# =========================
# PDF Report
# =========================
def build_pdf(
    pdf_path: Path,
    building_name: str,
    stats: Dict[str, Any],
    severe_items: List[DefectFinding],
    severe_img_paths: List[Path],
):
    """
    Generate PDF report with cover page and severe defect images.

    Layout:
    - Page 1: Title, summary statistics, and class-wise breakdown table
    - Following pages: One severe defect image per page with measurements

    Args:
        pdf_path: Output PDF file path
        building_name: Name of the building
        stats: Statistics dictionary containing counts and severity metrics
        severe_items: List of severe defect findings
        severe_img_paths: List of severe image file paths (must match severe_items)
    """
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    normal = styles["Normal"]
    heading = styles["Heading2"]

    if FONT_AVAILABLE:
        title_style.fontName = "NanumGothic-Bold"
        heading.fontName = "NanumGothic-Bold"
        normal.fontName = "NanumGothic"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    story = []

    # --------- 1페이지: 표지 / 요약 ---------
    story.append(Paragraph(
        "드론 기반 외벽 결함 자동 분석 보고서<br/>"
        "Automatic Drone-based Facade Defect Analysis Report",
        title_style,
    ))
    story.append(Spacer(1, 10 * mm))

    story.append(Paragraph(f"대상 건물 / Building: {building_name}", heading))
    story.append(Spacer(1, 5 * mm))

    summary_text = (
        f"총 이미지 수 (Total images): {stats['num_images']}<br/>"
        f"총 결함 수 (Total defects): {stats['total_defects']}<br/>"
        f"평균 심각도 지수 (Mean severity index): {stats['mean_severity']:.2f}<br/>"
    )
    story.append(Paragraph(summary_text, normal))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("결함 종류별 통계 / Statistics by class", heading))
    story.append(Spacer(1, 3 * mm))

    table_data = [["Class", "Count", "Mean Severity"]]
    for cls_name, info in stats["by_class"].items():
        table_data.append([
            cls_name,
            str(info["count"]),
            f"{info['mean_severity']:.2f}",
        ])

    t = Table(table_data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.gray),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t)

    story.append(PageBreak())

    # --------- 이후 페이지: severe 이미지 1장당 1페이지 ---------
    for f, img_path in zip(severe_items, severe_img_paths):
        story.append(Paragraph(
            f"[{f.type.upper()}] {f.image}",
            heading,
        ))
        story.append(Spacer(1, 4 * mm))

        # 크기 맞춰서 삽입
        try:
            img_obj = RLImage(str(img_path))
            iw, ih = img_obj.wrap(0, 0)
            max_w = A4[0] - 30 * mm
            max_h = A4[1] - 70 * mm
            scale = min(max_w / iw, max_h / ih)
            img_obj.drawWidth = iw * scale
            img_obj.drawHeight = ih * scale
            story.append(img_obj)
        except Exception:
            story.append(Paragraph("이미지를 불러올 수 없습니다.", normal))

        story.append(Spacer(1, 4 * mm))

        # 수치 요약
        if f.type == "crack":
            length_txt = f"{f.length_mm:.1f} mm" if f.length_mm is not None else "-"
            width_txt = f"{f.width_mm:.1f} mm" if f.width_mm is not None else "-"
        else:
            length_txt = "-"
            width_txt = "-"
        area_txt = f"{f.area_mm2:.1f} mm²" if f.area_mm2 is not None else "-"

        info_text = (
            f"Severity index: {f.severity:.2f}<br/>"
            f"Length: {length_txt} / Width: {width_txt} / Area: {area_txt}"
        )
        story.append(Paragraph(info_text, normal))

        story.append(PageBreak())

    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc.build(story)


# =========================
# HTML Report
# =========================
def build_html(
    html_path: Path,
    building_name: str,
    stats: Dict[str, Any],
    severe_items: List[DefectFinding],
    severe_img_paths: List[Path],
):
    """
    Generate bilingual HTML report with interactive lightbox image viewer.

    Features:
    - Thumbnail click → fullscreen popup
    - Mouse wheel zoom in/out
    - Drag to pan
    - Synchronized rank badges between table and images

    Args:
        html_path: Output HTML file path
        building_name: Name of the building
        stats: Statistics dictionary
        severe_items: List of severe defect findings
        severe_img_paths: List of severe image file paths
    """
    html_path.parent.mkdir(parents=True, exist_ok=True)

    # Escape building name for HTML
    safe_building_name = html.escape(building_name)

    rows = []
    for idx, f in enumerate(severe_items, start=1):
        # Escape all user-controllable strings
        safe_image = html.escape(f.image)
        safe_type = html.escape(f.type)

        if f.type == "crack":
            length_txt = f"{f.length_mm:.1f}" if f.length_mm is not None else "-"
            width_txt = f"{f.width_mm:.1f}" if f.width_mm is not None else "-"
        else:
            length_txt = "-"
            width_txt = "-"
        area_txt = f"{f.area_mm2:.1f}" if f.area_mm2 is not None else "-"

        rows.append(f"""
        <tr>
          <td>{idx}</td>
          <td>{safe_image}</td>
          <td>{safe_type}</td>
          <td>{f.severity:.2f}</td>
          <td>{length_txt}</td>
          <td>{width_txt}</td>
          <td>{area_txt}</td>
        </tr>
        """)

    thumb_blocks = []
    for idx, p in enumerate(severe_img_paths, start=1):
        rel = Path("../severe") / p.name
        # Escape filename for HTML attributes and text
        safe_name = html.escape(p.name)
        safe_path = html.escape(rel.as_posix())

        thumb_blocks.append(f"""
        <div class="thumb" data-fullsrc="{safe_path}">
          <img src="{safe_path}" alt="{safe_name}" />
          <div class="caption">#{idx} - {safe_name}</div>
        </div>
        """)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
      <meta charset="utf-8" />
      <title>Facade Defect Report - {safe_building_name}</title>
      <style>
        body {{
          font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans","Malgun Gothic",sans-serif;
          margin: 24px;
          background-color: #111;
          color: #eee;
        }}
        h1, h2 {{
          color: #ffcc66;
        }}
        table {{
          border-collapse: collapse;
          width: 100%;
          margin-top: 16px;
        }}
        th, td {{
          border: 1px solid #444;
          padding: 6px 8px;
          text-align: center;
        }}
        th {{
          background-color: #222;
        }}
        tr:nth-child(even) {{
          background-color: #1a1a1a;
        }}
        .thumb-container {{
          display: flex;
          flex-wrap: wrap;
          gap: 16px;
          margin-top: 16px;
        }}
        .thumb {{
          flex: 0 0 280px;
          cursor: zoom-in;
        }}
        .thumb img {{
          max-width: 100%;
          border: 1px solid #444;
          display: block;
        }}
        .caption {{
          margin-top: 4px;
          font-size: 12px;
          color: #ccc;
        }}

        #viewer {{
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.8);
          display: none;
          align-items: center;
          justify-content: center;
          z-index: 9999;
        }}
        #viewer img {{
          max-width: 90%;
          max-height: 90%;
          transform-origin: center center;
          cursor: grab;
        }}
        #viewer .hint {{
          position: fixed;
          bottom: 20px;
          left: 50%;
          transform: translateX(-50%);
          color: #eee;
          font-size: 13px;
          background: rgba(0,0,0,0.6);
          padding: 6px 10px;
          border-radius: 4px;
        }}
      </style>
    </head>
    <body>
      <h1>외벽 결함 자동 분석 리포트 / Automatic Facade Defect Analysis Report</h1>
      <h2>Building / 건물: {safe_building_name}</h2>

      <h2>1. Summary / 요약</h2>
      <ul>
        <li>Total images (총 이미지 수): {stats['num_images']}</li>
        <li>Total defects (총 결함 수): {stats['total_defects']}</li>
        <li>Mean severity (평균 심각도 지수): {stats['mean_severity']:.2f}</li>
      </ul>

      <h2>2. Top severe defects / 상위 심각 결함</h2>
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Image</th>
            <th>Type</th>
            <th>Severity</th>
            <th>Length (mm)</th>
            <th>Width (mm)</th>
            <th>Area (mm²)</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>

      <h2>3. Visualization (click to zoom) / 시각화 (클릭 후 휠로 확대)</h2>
      <div class="thumb-container">
        {"".join(thumb_blocks)}
      </div>

      <div id="viewer">
        <img id="viewer-img" src="" alt="" />
        <div class="hint">마우스 휠로 확대/축소, 드래그로 이동, ESC 또는 빈 곳 클릭으로 닫기</div>
      </div>

      <script>
        const viewer = document.getElementById('viewer');
        const viewerImg = document.getElementById('viewer-img');
        let scale = 1.0;
        let originX = 0, originY = 0;
        let isDragging = false;
        let lastX = 0, lastY = 0;

        function updateTransform() {{
          viewerImg.style.transform = `translate(${{originX}}px, ${{originY}}px) scale(${{scale}})`;
        }}

        document.querySelectorAll('.thumb').forEach(el => {{
          el.addEventListener('click', () => {{
            const src = el.getAttribute('data-fullsrc');
            viewerImg.src = src;
            scale = 1.0;
            originX = 0;
            originY = 0;
            updateTransform();
            viewer.style.display = 'flex';
          }});
        }});

        viewer.addEventListener('click', (e) => {{
          if (e.target === viewer) {{
            viewer.style.display = 'none';
          }}
        }});

        document.addEventListener('keydown', (e) => {{
          if (e.key === 'Escape') {{
            viewer.style.display = 'none';
          }}
        }});

        viewer.addEventListener('wheel', (e) => {{
          e.preventDefault();
          const delta = e.deltaY < 0 ? 1.1 : 0.9;
          scale *= delta;
          if (scale < 0.3) scale = 0.3;
          if (scale > 8.0) scale = 8.0;
          updateTransform();
        }}, {{ passive: false }});

        viewerImg.addEventListener('mousedown', (e) => {{
          isDragging = true;
          lastX = e.clientX;
          lastY = e.clientY;
          viewerImg.style.cursor = 'grabbing';
        }});

        window.addEventListener('mouseup', () => {{
          isDragging = false;
          viewerImg.style.cursor = 'grab';
        }});

        window.addEventListener('mousemove', (e) => {{
          if (!isDragging) return;
          const dx = e.clientX - lastX;
          const dy = e.clientY - lastY;
          lastX = e.clientX;
          lastY = e.clientY;
          originX += dx;
          originY += dy;
          updateTransform();
        }});
      </script>
    </body>
    </html>
    """

    html_path.write_text(html_content, encoding="utf-8")


# =========================
# Building 단위 처리
# =========================
def process_building(
    building_dir: Path,
    out_root: Path,
    inferencer: DualModelInferencer,
    topk_base: int = 5,
    topk_max: int = 7,
    high_severity_threshold: float = 5000.0,
):
    """
    Process all images in a building directory.

    Runs inference, generates visualizations, computes statistics,
    and creates PDF/HTML reports.

    Args:
        building_dir: Directory containing building images
        out_root: Output root directory
        inferencer: DualModelInferencer instance
        topk_base: Base number of top severe defects to include
        topk_max: Maximum number of top severe defects (if high severity)
        high_severity_threshold: Threshold for expanding topk to topk_max
    """
    building_name = building_dir.name
    img_paths = collect_images(building_dir)
    if not img_paths:
        print(f"⚠ No images in {building_dir}")
        return

    print(f"\n=== Building: {building_name} ({len(img_paths)} images) ===")

    b_out = out_root / building_name
    det_dir = b_out / "detected"
    severe_dir = b_out / "severe"
    report_dir = b_out / "report"

    det_dir.mkdir(parents=True, exist_ok=True)
    severe_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    findings: List[DefectFinding] = []
    num_images = 0
    errors: List[str] = []

    for img_path in tqdm(img_paths, desc=f"{building_name}", unit="img"):
        try:
            img = cv2.imread(str(img_path))
            if img is None:
                error_msg = f"Failed to read image: {img_path}"
                print(f"⚠ {error_msg}")
                errors.append(error_msg)
                continue

            num_images += 1

            # Run inference
            try:
                res = inferencer.infer_one(img_path)
            except Exception as e:
                error_msg = f"Inference failed for {img_path}: {e}"
                print(f"⚠ {error_msg}")
                errors.append(error_msg)
                continue

            # Visualize and save
            vis = DualModelInferencer.visualize(img, res)
            out_img_path = det_dir / f"{img_path.stem}_vis.jpg"

            if not cv2.imwrite(str(out_img_path), vis):
                error_msg = f"Failed to write visualization: {out_img_path}"
                print(f"⚠ {error_msg}")
                errors.append(error_msg)

            # Collect crack findings
            for c in res.cracks:
                findings.append(
                    DefectFinding(
                        building=building_name,
                        image=res.image,
                        image_path=str(img_path),
                        type="crack",
                        severity=c.severity,
                        length_mm=c.length_mm,
                        width_mm=c.width_mm,
                        area_mm2=c.area_mm2,
                        extra={"mean_width_mm": c.mean_width_mm},
                        bbox_xyxy=None,
                        polygon=c.polygon,
                    )
                )

            # Collect detection findings
            for d in res.detections:
                findings.append(
                    DefectFinding(
                        building=building_name,
                        image=res.image,
                        image_path=str(img_path),
                        type=d.class_name,
                        severity=d.severity,
                        length_mm=None,
                        width_mm=None,
                        area_mm2=d.area_mm2,
                        extra={"conf": d.confidence},
                        bbox_xyxy=d.bbox_xyxy,
                        polygon=None,
                    )
                )

        except Exception as e:
            error_msg = f"Unexpected error processing {img_path}: {e}"
            print(f"⚠ {error_msg}")
            errors.append(error_msg)

    # 통계/리포트
    if not findings:
        print(f"⚠ No defects found in {building_name}")
        pdf_path = report_dir / "report.pdf"
        html_path = report_dir / "report.html"
        empty_stats = {
            "num_images": num_images,
            "total_defects": 0,
            "mean_severity": 0.0,
            "by_class": {},
        }
        build_pdf(pdf_path, building_name, empty_stats, [], [])
        build_html(html_path, building_name, empty_stats, [], [])
        with (b_out / "findings.csv").open("w", encoding="utf-8") as f:
            f.write("building,image,image_path,type,severity,length_mm,width_mm,area_mm2,extra\n")
        print(f"✅ {building_name} 완료(결함 없음): {pdf_path}")
        return

    # 통계 계산
    total_severity = sum(f.severity for f in findings)
    mean_severity = total_severity / len(findings)

    by_class: Dict[str, Dict[str, float]] = {}
    for f in findings:
        cls = f.type
        info = by_class.setdefault(cls, {"count": 0, "severity_sum": 0.0})
        info["count"] += 1
        info["severity_sum"] += f.severity
    for cls, info in by_class.items():
        info["mean_severity"] = info["severity_sum"] / max(info["count"], 1)

    stats = {
        "num_images": num_images,
        "total_defects": len(findings),
        "mean_severity": mean_severity,
        "by_class": by_class,
    }

    # 이미지당 가장 심각한 결함 1개만 뽑기
    findings_by_image: Dict[str, DefectFinding] = {}
    for f in findings:
        key = f.image_path  # 원본 경로 기준
        cur = findings_by_image.get(key)
        if cur is None or f.severity > cur.severity:
            findings_by_image[key] = f

    per_image_tops = list(findings_by_image.values())
    per_image_tops_sorted = sorted(per_image_tops, key=lambda x: x.severity, reverse=True)

    # mean severity 에 따라 topk 크기 결정
    if mean_severity >= high_severity_threshold and len(per_image_tops_sorted) >= topk_max:
        topk = topk_max
    else:
        topk = min(topk_base, len(per_image_tops_sorted))

    severe_items = per_image_tops_sorted[:topk]

    # Generate severe defect images
    severe_img_paths: List[Path] = []
    for rank, f in enumerate(severe_items, start=1):
        try:
            base_img = cv2.imread(f.image_path)
            if base_img is None:
                error_msg = f"Cannot read image for severe visualization: {f.image_path}"
                print(f"⚠ {error_msg}")
                errors.append(error_msg)
                continue

            severe_vis = make_severe_image(base_img, f, rank)
            out_path = severe_dir / f"{Path(f.image_path).stem}_severe.jpg"

            if not cv2.imwrite(str(out_path), severe_vis):
                error_msg = f"Failed to write severe image: {out_path}"
                print(f"⚠ {error_msg}")
                errors.append(error_msg)
                continue

            severe_img_paths.append(out_path)

        except Exception as e:
            error_msg = f"Error generating severe image for {f.image_path}: {e}"
            print(f"⚠ {error_msg}")
            errors.append(error_msg)

    # PDF / HTML 생성
    pdf_path = report_dir / "report.pdf"
    html_path = report_dir / "report.html"
    build_pdf(pdf_path, building_name, stats, severe_items, severe_img_paths)
    build_html(html_path, building_name, stats, severe_items, severe_img_paths)

    # 전체 findings JSON / CSV / stats 저장
    with (b_out / "findings.json").open("w", encoding="utf-8") as f:
        json.dump([asdict(x) for x in findings], f, ensure_ascii=False, indent=2)

    csv_path = b_out / "findings.csv"
    with csv_path.open("w", encoding="utf-8-sig") as f:
        f.write("building,image,image_path,type,severity,length_mm,width_mm,area_mm2,extra\n")
        for x in findings:
            f.write(
                f"{x.building},{x.image},{x.image_path},"
                f"{x.type},{x.severity:.4f},"
                f"{'' if x.length_mm is None else f'{x.length_mm:.3f}'},"
                f"{'' if x.width_mm is None else f'{x.width_mm:.3f}'},"
                f"{'' if x.area_mm2 is None else f'{x.area_mm2:.3f}'},"
                f"{json.dumps(x.extra, ensure_ascii=False)}\n"
            )

    with (b_out / "stats.json").open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    stats_csv_path = b_out / "stats.csv"
    with stats_csv_path.open("w", encoding="utf-8-sig") as f:
        f.write("class,count,mean_severity\n")
        for cls, info in by_class.items():
            f.write(f"{cls},{info['count']},{info['mean_severity']:.4f}\n")

    # Print summary
    print(f"✅ {building_name} 완료: {pdf_path}, {html_path}")

    if errors:
        print(f"\n⚠ Encountered {len(errors)} errors during processing:")
        for err in errors[:10]:  # Show first 10 errors
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

        # Save error log
        error_log_path = b_out / "errors.log"
        with error_log_path.open("w", encoding="utf-8") as f:
            for err in errors:
                f.write(f"{err}\n")
        print(f"  Full error log saved to: {error_log_path}")


# =========================
# main
# =========================
def main():
    parser = argparse.ArgumentParser(
        description="Crack segmentation + multi-defect detection + severity ranking + CSV/HTML/PDF report (skeleton-based crack measurement, v4_plus3)"
    )
    parser.add_argument(
        "--input-root",
        type=str,
        required=True,
        help="이미지 루트 폴더 (건물 폴더들이 들어있거나, 단일 폴더)",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="dual_reports",
        help="결과 저장 루트 폴더",
    )
    parser.add_argument(
        "--crack-model",
        type=str,
        default=DEFAULT_CRACK_MODEL,
        help="YOLOv8-seg crack 모델(best.pt)",
    )
    parser.add_argument(
        "--det-model",
        type=str,
        default=DEFAULT_DET_MODEL,
        help="multi-class detection 모델(best.pt)",
    )
    parser.add_argument("--imgsz", type=int, default=1024)
    parser.add_argument("--crack-conf", type=float, default=0.25)
    parser.add_argument("--det-conf", type=float, default=0.35)
    parser.add_argument(
        "--mm-per-pixel",
        type=float,
        default=1.0,
        help="픽셀당 mm (GSD). 모를 경우 1.0으로 두고 상대적인 지표로 사용.",
    )
    parser.add_argument("--topk-base", type=int, default=5)
    parser.add_argument("--topk-max", type=int, default=7)
    parser.add_argument(
        "--high-severity-th",
        type=float,
        default=5000.0,
        help="평균 severity가 이 값 이상이면 topk_max까지 확장",
    )
    parser.add_argument(
        "--crack-measure-mode",
        type=str,
        default="skeleton",
        choices=["skeleton"],
        help="현재는 skeleton만 사용",
    )
    parser.add_argument(
        "--min-box-px",
        type=int,
        default=40,
        help="멀리 있는 detection 제거용 최소 박스 크기(px)",
    )
    parser.add_argument(
        "--min-mask-area-px",
        type=int,
        default=250,
        help="멀리 있는 crack mask 제거용 최소 area(px)",
    )

    args = parser.parse_args()

    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    if not input_root.exists():
        raise SystemExit(f"Input root not found: {input_root}")

    output_root.mkdir(parents=True, exist_ok=True)

    inferencer = DualModelInferencer(
        crack_model_path=args.crack_model,
        det_model_path=args.det_model,
        imgsz=args.imgsz,
        crack_conf=args.crack_conf,
        det_conf=args.det_conf,
        mm_per_pixel=args.mm_per_pixel,
        crack_measure_mode=args.crack_measure_mode,
        min_box_px=args.min_box_px,
        min_mask_area_px=args.min_mask_area_px,
    )

    direct_imgs = collect_images(input_root)
    subdirs = [d for d in input_root.iterdir() if d.is_dir()]

    if direct_imgs and not subdirs:
        process_building(
            input_root,
            output_root,
            inferencer,
            topk_base=args.topk_base,
            topk_max=args.topk_max,
            high_severity_threshold=args.high_severity_th,
        )
    else:
        for d in sorted(subdirs):
            process_building(
                d,
                output_root,
                inferencer,
                topk_base=args.topk_base,
                topk_max=args.topk_max,
                high_severity_threshold=args.high_severity_th,
            )


if __name__ == "__main__":
    main()
