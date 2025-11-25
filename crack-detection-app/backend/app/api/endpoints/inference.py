"""
Inference API endpoints
Handles image upload, inference requests, and result retrieval
"""
import asyncio
import uuid
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from ...core.config import settings
from ...schemas.inference import (
    InferenceConfig,
    InferenceRequest,
    InferenceResponse,
    TaskStatusResponse,
    ImageResultSchema,
)
from ...services.inference_service import InferenceService
from ...services.report_service import ReportService

router = APIRouter(prefix="/inference", tags=["inference"])

# In-memory task storage (use Redis/DB in production)
tasks: Dict[str, Dict[str, Any]] = {}


@router.post("/upload", response_model=Dict[str, Any])
async def upload_images(
    building_name: str,
    files: List[UploadFile] = File(...),
):
    """
    Upload multiple images for a building

    Args:
        building_name: Name of the building/project
        files: List of image files

    Returns:
        Upload confirmation with file paths
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Create building directory
    building_dir = settings.upload_dir / building_name
    building_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = []
    for file in files:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}"
            )

        # Save file
        file_path = building_dir / file.filename
        content = await file.read()

        # Check file size
        if len(content) > settings.max_upload_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file.filename}"
            )

        with open(file_path, "wb") as f:
            f.write(content)

        uploaded_files.append({
            "filename": file.filename,
            "path": str(file_path),
            "size": len(content),
        })

    return {
        "building_name": building_name,
        "uploaded_count": len(uploaded_files),
        "files": uploaded_files,
    }


async def run_inference_task(
    task_id: str,
    building_name: str,
    config: InferenceConfig,
):
    """Background task for running inference"""
    try:
        # Update task status
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = 0.0

        # Get image paths
        building_dir = settings.upload_dir / building_name
        if not building_dir.exists():
            raise FileNotFoundError(f"Building directory not found: {building_name}")

        img_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        img_paths = [
            p for p in building_dir.rglob("*")
            if p.suffix.lower() in img_exts
        ]

        if not img_paths:
            raise ValueError(f"No images found in {building_name}")

        # Initialize inference service
        crack_model = config.crack_model_path or settings.default_crack_model
        det_model = config.det_model_path or settings.default_det_model

        service = InferenceService(config, crack_model, det_model)

        # Progress callback
        async def progress_callback(current: int, total: int):
            progress = (current / total) * 100.0
            tasks[task_id]["progress"] = progress
            tasks[task_id]["message"] = f"Processing {current}/{total} images"

        # Run inference
        results = await service.infer_batch(img_paths, progress_callback)

        # Generate reports
        output_dir = settings.output_dir / building_name
        output_dir.mkdir(parents=True, exist_ok=True)

        report_service = ReportService(config)
        report_data = await report_service.generate_reports(
            building_name=building_name,
            results=results,
            output_dir=output_dir,
        )

        # Update task with results
        tasks[task_id].update({
            "status": "completed",
            "progress": 100.0,
            "message": "Inference completed successfully",
            "results": results,
            "stats": report_data["stats"],
            "severe_findings": report_data["severe_findings"],
            "report_pdf_url": f"/api/v1/inference/download/{building_name}/report.pdf",
            "report_html_url": f"/api/v1/inference/download/{building_name}/report.html",
            "detected_images_dir": str(output_dir / "detected"),
            "severe_images_dir": str(output_dir / "severe"),
        })

    except Exception as e:
        tasks[task_id].update({
            "status": "failed",
            "message": f"Error: {str(e)}",
        })


@router.post("/start", response_model=InferenceResponse)
async def start_inference(
    request: InferenceRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start inference on uploaded images

    Args:
        request: Inference request with building name and config

    Returns:
        Task ID and initial status
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())

    # Use default config if not provided
    config = request.config or InferenceConfig()

    # Create task entry
    tasks[task_id] = {
        "task_id": task_id,
        "building_name": request.building_name,
        "status": "pending",
        "progress": 0.0,
        "message": "Task queued",
        "config": config.model_dump(),
    }

    # Start background task
    background_tasks.add_task(
        run_inference_task,
        task_id,
        request.building_name,
        config,
    )

    return InferenceResponse(
        task_id=task_id,
        building_name=request.building_name,
        status="pending",
        progress=0.0,
        message="Inference started",
    )


@router.get("/status/{task_id}", response_model=InferenceResponse)
async def get_task_status(task_id: str):
    """
    Get status of an inference task

    Args:
        task_id: Task identifier

    Returns:
        Current task status and results (if completed)
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    return InferenceResponse(
        task_id=task_id,
        building_name=task["building_name"],
        status=task["status"],
        progress=task["progress"],
        message=task.get("message"),
        results=task.get("results"),
        stats=task.get("stats"),
        severe_findings=task.get("severe_findings"),
        report_pdf_url=task.get("report_pdf_url"),
        report_html_url=task.get("report_html_url"),
        detected_images_dir=task.get("detected_images_dir"),
        severe_images_dir=task.get("severe_images_dir"),
    )


@router.get("/download/{building_name}/{filename}")
async def download_file(building_name: str, filename: str):
    """
    Download generated reports or images

    Args:
        building_name: Building name
        filename: File to download (e.g., report.pdf, report.html)

    Returns:
        File download response
    """
    file_path = settings.output_dir / building_name / "report" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )


@router.get("/tasks", response_model=List[Dict[str, Any]])
async def list_tasks():
    """
    List all inference tasks

    Returns:
        List of tasks with status
    """
    return [
        {
            "task_id": task_id,
            "building_name": task["building_name"],
            "status": task["status"],
            "progress": task["progress"],
        }
        for task_id, task in tasks.items()
    ]


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task from memory"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    del tasks[task_id]
    return {"message": "Task deleted"}
