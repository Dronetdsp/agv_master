"""
Pydantic schemas for inference requests and responses
Type-safe data validation
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class InferenceConfig(BaseModel):
    """User-customizable inference configuration"""

    model_config = ConfigDict(from_attributes=True)

    imgsz: int = Field(default=1024, ge=320, le=2048, description="Input image size")
    crack_conf: float = Field(default=0.25, ge=0.0, le=1.0, description="Crack confidence threshold")
    det_conf: float = Field(default=0.35, ge=0.0, le=1.0, description="Detection confidence threshold")
    mm_per_pixel: float = Field(default=1.0, gt=0, description="Millimeters per pixel (GSD)")
    min_box_px: int = Field(default=40, ge=1, description="Minimum box size in pixels")
    min_mask_area_px: int = Field(default=250, ge=1, description="Minimum mask area in pixels")
    topk_base: int = Field(default=5, ge=1, le=20, description="Base number of top defects")
    topk_max: int = Field(default=7, ge=1, le=30, description="Maximum number of top defects")
    high_severity_th: float = Field(default=5000.0, ge=0, description="High severity threshold")

    # Model selection (optional)
    crack_model_path: Optional[str] = None
    det_model_path: Optional[str] = None


class CrackRegionSchema(BaseModel):
    """Crack region measurement results"""

    polygon: List[int] = Field(description="Polygon coordinates [x1,y1,x2,y2,...]")
    length_mm: float = Field(description="Crack length in mm")
    width_mm: float = Field(description="Maximum crack width in mm")
    mean_width_mm: float = Field(description="Average crack width in mm")
    area_mm2: float = Field(description="Crack area in mm²")
    severity: float = Field(description="Severity index (length × width)")


class DetectionResultSchema(BaseModel):
    """Detection result for non-crack defects"""

    bbox_xyxy: List[float] = Field(description="Bounding box [x1,y1,x2,y2]")
    class_id: int
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    width_mm: float
    height_mm: float
    area_mm2: float
    severity: float = Field(description="Severity index (area)")


class ImageResultSchema(BaseModel):
    """Results for a single image"""

    image: str = Field(description="Image filename")
    full_path: str = Field(description="Full path to original image")
    width: int = Field(description="Image width in pixels")
    height: int = Field(description="Image height in pixels")
    cracks: List[CrackRegionSchema] = Field(default_factory=list)
    detections: List[DetectionResultSchema] = Field(default_factory=list)


class DefectFindingSchema(BaseModel):
    """Individual defect finding with ranking"""

    building: str
    image: str
    image_path: str
    type: str = Field(description="Defect type (crack, spall, rust, etc.)")
    severity: float
    length_mm: Optional[float] = None
    width_mm: Optional[float] = None
    area_mm2: Optional[float] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
    bbox_xyxy: Optional[List[float]] = None
    polygon: Optional[List[int]] = None


class BuildingStatsSchema(BaseModel):
    """Statistics for a building analysis"""

    num_images: int
    total_defects: int
    mean_severity: float
    by_class: Dict[str, Dict[str, float]] = Field(
        description="Statistics grouped by defect class"
    )


class InferenceRequest(BaseModel):
    """Request to start inference on uploaded images"""

    building_name: str = Field(description="Building/project name")
    config: Optional[InferenceConfig] = Field(
        default=None,
        description="Custom inference configuration (uses defaults if not provided)"
    )


class InferenceResponse(BaseModel):
    """Response after inference completion"""

    task_id: str = Field(description="Unique task identifier")
    building_name: str
    status: str = Field(description="Task status: pending, processing, completed, failed")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Progress percentage")
    message: Optional[str] = None

    # Results (populated when completed)
    results: Optional[List[ImageResultSchema]] = None
    stats: Optional[BuildingStatsSchema] = None
    severe_findings: Optional[List[DefectFindingSchema]] = None

    # Output paths
    report_pdf_url: Optional[str] = None
    report_html_url: Optional[str] = None
    detected_images_dir: Optional[str] = None
    severe_images_dir: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """Task status check response"""

    task_id: str
    status: str
    progress: float = Field(ge=0.0, le=100.0)
    message: Optional[str] = None
    created_at: str
    updated_at: str
    result: Optional[InferenceResponse] = None


class UserPreferences(BaseModel):
    """User-specific preferences (saved to DB)"""

    user_id: Optional[str] = None
    default_config: InferenceConfig = Field(default_factory=InferenceConfig)
    theme: str = Field(default="light", description="UI theme: light or dark")
    language: str = Field(default="ko", description="UI language")
    recent_buildings: List[str] = Field(default_factory=list, max_length=10)
