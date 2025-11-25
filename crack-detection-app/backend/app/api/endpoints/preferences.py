"""
User preferences API endpoints
Handles saving and loading user-specific settings
"""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from ...core.config import settings
from ...schemas.inference import UserPreferences, InferenceConfig

router = APIRouter(prefix="/preferences", tags=["preferences"])

# Simple file-based storage (use DB in production)
PREFS_DIR = Path("./user_preferences")
PREFS_DIR.mkdir(exist_ok=True)


@router.get("/", response_model=UserPreferences)
async def get_preferences(user_id: str = "default"):
    """
    Get user preferences

    Args:
        user_id: User identifier (default: "default")

    Returns:
        User preferences or defaults
    """
    prefs_file = PREFS_DIR / f"{user_id}.json"

    if prefs_file.exists():
        with open(prefs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return UserPreferences(**data)

    # Return defaults
    return UserPreferences(
        user_id=user_id,
        default_config=InferenceConfig(),
    )


@router.post("/", response_model=UserPreferences)
async def save_preferences(preferences: UserPreferences):
    """
    Save user preferences

    Args:
        preferences: User preferences to save

    Returns:
        Saved preferences
    """
    user_id = preferences.user_id or "default"
    prefs_file = PREFS_DIR / f"{user_id}.json"

    # Save to file
    with open(prefs_file, "w", encoding="utf-8") as f:
        json.dump(preferences.model_dump(), f, indent=2, ensure_ascii=False)

    return preferences


@router.delete("/")
async def reset_preferences(user_id: str = "default"):
    """
    Reset user preferences to defaults

    Args:
        user_id: User identifier

    Returns:
        Confirmation message
    """
    prefs_file = PREFS_DIR / f"{user_id}.json"

    if prefs_file.exists():
        prefs_file.unlink()

    return {"message": "Preferences reset to defaults"}


@router.post("/recent-building")
async def add_recent_building(building_name: str, user_id: str = "default"):
    """
    Add building to recent list

    Args:
        building_name: Building name
        user_id: User identifier

    Returns:
        Updated recent buildings list
    """
    prefs = await get_preferences(user_id)

    # Add to recent list (keep last 10)
    if building_name in prefs.recent_buildings:
        prefs.recent_buildings.remove(building_name)

    prefs.recent_buildings.insert(0, building_name)
    prefs.recent_buildings = prefs.recent_buildings[:10]

    # Save
    await save_preferences(prefs)

    return {"recent_buildings": prefs.recent_buildings}
