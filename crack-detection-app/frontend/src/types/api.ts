/**
 * TypeScript types matching backend Pydantic schemas
 */

export interface InferenceConfig {
  imgsz?: number;
  crack_conf?: number;
  det_conf?: number;
  mm_per_pixel?: number;
  min_box_px?: number;
  min_mask_area_px?: number;
  topk_base?: number;
  topk_max?: number;
  high_severity_th?: number;
  crack_model_path?: string;
  det_model_path?: string;
}

export interface CrackRegion {
  polygon: number[];
  length_mm: number;
  width_mm: number;
  mean_width_mm: number;
  area_mm2: number;
  severity: number;
}

export interface DetectionResult {
  bbox_xyxy: number[];
  class_id: number;
  class_name: string;
  confidence: number;
  width_mm: number;
  height_mm: number;
  area_mm2: number;
  severity: number;
}

export interface ImageResult {
  image: string;
  full_path: string;
  width: number;
  height: number;
  cracks: CrackRegion[];
  detections: DetectionResult[];
}

export interface DefectFinding {
  building: string;
  image: string;
  image_path: string;
  type: string;
  severity: number;
  length_mm?: number;
  width_mm?: number;
  area_mm2?: number;
  extra: Record<string, any>;
  bbox_xyxy?: number[];
  polygon?: number[];
}

export interface BuildingStats {
  num_images: number;
  total_defects: number;
  mean_severity: number;
  by_class: Record<string, { count: number; mean_severity: number; severity_sum: number }>;
}

export interface InferenceRequest {
  building_name: string;
  config?: InferenceConfig;
}

export interface InferenceResponse {
  task_id: string;
  building_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  results?: ImageResult[];
  stats?: BuildingStats;
  severe_findings?: DefectFinding[];
  report_pdf_url?: string;
  report_html_url?: string;
  detected_images_dir?: string;
  severe_images_dir?: string;
}

export interface UserPreferences {
  user_id?: string;
  default_config: InferenceConfig;
  theme: 'light' | 'dark';
  language: string;
  recent_buildings: string[];
}

export interface UploadResponse {
  building_name: string;
  uploaded_count: number;
  files: Array<{
    filename: string;
    path: string;
    size: number;
  }>;
}
