"""
Report generation service
Creates PDF, HTML, and visualization images
"""
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import cv2
import numpy as np

from ..schemas.inference import (
    InferenceConfig,
    ImageResultSchema,
    DefectFindingSchema,
    BuildingStatsSchema,
)


class ReportService:
    """Generate reports and visualizations"""

    def __init__(self, config: InferenceConfig):
        self.config = config

    async def generate_reports(
        self,
        building_name: str,
        results: List[ImageResultSchema],
        output_dir: Path,
    ) -> Dict[str, Any]:
        """
        Generate all reports (PDF, HTML, visualizations)

        Args:
            building_name: Building name
            results: List of inference results
            output_dir: Output directory

        Returns:
            Dictionary with stats and severe findings
        """
        # Create output directories
        detected_dir = output_dir / "detected"
        severe_dir = output_dir / "severe"
        report_dir = output_dir / "report"

        detected_dir.mkdir(parents=True, exist_ok=True)
        severe_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        # Collect all findings
        findings: List[DefectFindingSchema] = []
        for res in results:
            # Crack findings
            for crack in res.cracks:
                findings.append(
                    DefectFindingSchema(
                        building=building_name,
                        image=res.image,
                        image_path=res.full_path,
                        type="crack",
                        severity=crack.severity,
                        length_mm=crack.length_mm,
                        width_mm=crack.width_mm,
                        area_mm2=crack.area_mm2,
                        extra={"mean_width_mm": crack.mean_width_mm},
                        polygon=crack.polygon,
                    )
                )

            # Detection findings
            for det in res.detections:
                findings.append(
                    DefectFindingSchema(
                        building=building_name,
                        image=res.image,
                        image_path=res.full_path,
                        type=det.class_name,
                        severity=det.severity,
                        area_mm2=det.area_mm2,
                        extra={"confidence": det.confidence},
                        bbox_xyxy=det.bbox_xyxy,
                    )
                )

        # Calculate statistics
        stats = self._calculate_statistics(building_name, findings, len(results))

        # Get top severe findings (one per image)
        severe_findings = self._get_severe_findings(findings)

        # Generate visualizations (run in executor)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._generate_visualizations,
            results,
            severe_findings,
            detected_dir,
            severe_dir,
        )

        # TODO: Generate PDF and HTML reports
        # (Reuse existing code from dual_infer_severity_v4_plus3.py)

        return {
            "stats": stats,
            "severe_findings": severe_findings,
        }

    def _calculate_statistics(
        self,
        building_name: str,
        findings: List[DefectFindingSchema],
        num_images: int,
    ) -> BuildingStatsSchema:
        """Calculate statistics from findings"""
        if not findings:
            return BuildingStatsSchema(
                num_images=num_images,
                total_defects=0,
                mean_severity=0.0,
                by_class={},
            )

        total_severity = sum(f.severity for f in findings)
        mean_severity = total_severity / len(findings)

        # Group by class
        by_class: Dict[str, Dict[str, float]] = {}
        for f in findings:
            cls = f.type
            if cls not in by_class:
                by_class[cls] = {"count": 0, "severity_sum": 0.0}

            by_class[cls]["count"] += 1
            by_class[cls]["severity_sum"] += f.severity

        # Calculate mean severity per class
        for cls, info in by_class.items():
            info["mean_severity"] = info["severity_sum"] / max(info["count"], 1)

        return BuildingStatsSchema(
            num_images=num_images,
            total_defects=len(findings),
            mean_severity=mean_severity,
            by_class=by_class,
        )

    def _get_severe_findings(
        self, findings: List[DefectFindingSchema]
    ) -> List[DefectFindingSchema]:
        """Get most severe finding per image"""
        # Group by image path
        by_image: Dict[str, DefectFindingSchema] = {}
        for f in findings:
            key = f.image_path
            if key not in by_image or f.severity > by_image[key].severity:
                by_image[key] = f

        # Sort by severity and get top K
        sorted_findings = sorted(
            by_image.values(),
            key=lambda x: x.severity,
            reverse=True
        )

        # Determine topk
        mean_severity = sum(f.severity for f in findings) / max(len(findings), 1)
        if mean_severity >= self.config.high_severity_th:
            topk = min(self.config.topk_max, len(sorted_findings))
        else:
            topk = min(self.config.topk_base, len(sorted_findings))

        return sorted_findings[:topk]

    def _generate_visualizations(
        self,
        results: List[ImageResultSchema],
        severe_findings: List[DefectFindingSchema],
        detected_dir: Path,
        severe_dir: Path,
    ):
        """Generate visualization images (synchronous)"""
        # Generate detected images (all defects)
        for res in results:
            img = cv2.imread(res.full_path)
            if img is None:
                continue

            vis = self._visualize_all(img, res)
            out_path = detected_dir / f"{Path(res.image).stem}_detected.jpg"
            cv2.imwrite(str(out_path), vis)

        # Generate severe images (top defects with zoom)
        for rank, finding in enumerate(severe_findings, start=1):
            img = cv2.imread(finding.image_path)
            if img is None:
                continue

            vis = self._visualize_severe(img, finding, rank)
            out_path = severe_dir / f"{Path(finding.image).stem}_severe.jpg"
            cv2.imwrite(str(out_path), vis)

    def _visualize_all(
        self, img: np.ndarray, res: ImageResultSchema
    ) -> np.ndarray:
        """Visualize all defects on image"""
        vis = img.copy()

        # Draw cracks
        for crack in res.cracks:
            pts = np.array(crack.polygon, dtype=np.int32).reshape(-1, 2)
            cv2.polylines(vis, [pts], True, (0, 0, 255), 4)

            # Label
            x, y, w, h = cv2.boundingRect(pts)
            cv2.putText(
                vis,
                "CRACK",
                (x, max(0, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3,
            )

        # Draw detections
        for det in res.detections:
            x1, y1, x2, y2 = map(int, det.bbox_xyxy)
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 255), 4)
            cv2.putText(
                vis,
                det.class_name.upper(),
                (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (255, 0, 0),
                3,
            )

        return vis

    def _visualize_severe(
        self, img: np.ndarray, finding: DefectFindingSchema, rank: int
    ) -> np.ndarray:
        """Visualize severe defect with zoom inset"""
        vis = img.copy()
        h, w = vis.shape[:2]

        # Draw main defect
        if finding.type == "crack" and finding.polygon:
            pts = np.array(finding.polygon, dtype=np.int32).reshape(-1, 2)
            cv2.polylines(vis, [pts], True, (0, 0, 255), 5)
            x, y, w_rect, h_rect = cv2.boundingRect(pts)
            bbox = (x, y, x + w_rect, y + h_rect)
        elif finding.bbox_xyxy:
            x1, y1, x2, y2 = map(int, finding.bbox_xyxy)
            cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 0, 0), 6)
            bbox = (x1, y1, x2, y2)
        else:
            bbox = (0, 0, w, h)

        # Add zoom inset
        vis = self._add_zoom_inset(vis, bbox)

        # Add rank badge
        self._draw_rank_badge(vis, rank)

        return vis

    def _add_zoom_inset(
        self, img: np.ndarray, bbox: tuple
    ) -> np.ndarray:
        """Add zoom inset to bottom-left corner"""
        h, w = img.shape[:2]
        x1, y1, x2, y2 = bbox

        # Crop with padding
        pad = 80
        x1p = max(0, x1 - pad)
        y1p = max(0, y1 - pad)
        x2p = min(w, x2 + pad)
        y2p = min(h, y2 + pad)

        if x2p <= x1p or y2p <= y1p:
            return img

        crop = img[y1p:y2p, x1p:x2p].copy()

        # Resize to 25% of image width
        target_w = int(w * 0.25)
        scale = target_w / max(crop.shape[1], 1)
        target_h = int(crop.shape[0] * scale)
        crop_resized = cv2.resize(crop, (target_w, target_h))

        # Place in bottom-left
        x0, y0 = 10, h - target_h - 10
        overlay = img.copy()
        overlay[y0:y0 + target_h, x0:x0 + target_w] = crop_resized

        # Border
        cv2.rectangle(
            overlay,
            (x0, y0),
            (x0 + target_w, y0 + target_h),
            (255, 0, 0),
            3,
        )

        return overlay

    def _draw_rank_badge(self, img: np.ndarray, rank: int):
        """Draw rank badge in top-left corner"""
        label = str(rank)
        cv2.rectangle(img, (0, 0), (60, 50), (0, 0, 0), -1)
        cv2.rectangle(img, (0, 0), (60, 50), (0, 255, 255), 2)
        cv2.putText(
            img,
            label,
            (10, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 255),
            3,
        )
