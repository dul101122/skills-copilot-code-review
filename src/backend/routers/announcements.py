"""
Endpoints for managing announcements in the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime
from bson.objectid import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements(include_inactive: bool = Query(False)) -> List[Dict[str, Any]]:
    """
    Get all active announcements (or all if include_inactive is True).
    Active announcements are those where:
    - start_date is None or today >= start_date
    - today <= expiration_date
    """
    today = datetime.now().strftime("%Y-%m-%d")
    announcements = []

    for announcement in announcements_collection.find():
        announcement_id = str(announcement["_id"])
        announcement["id"] = announcement_id
        del announcement["_id"]

        if not include_inactive:
            # Check if announcement is active
            start_date = announcement.get("start_date")
            expiration_date = announcement.get("expiration_date")

            # Check start date
            if start_date and today < start_date:
                continue

            # Check expiration date
            if expiration_date and today > expiration_date:
                continue

        announcements.append(announcement)

    return announcements


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements() -> List[Dict[str, Any]]:
    """Get all announcements including inactive ones (admin only)"""
    announcements = []

    for announcement in announcements_collection.find():
        announcement_id = str(announcement["_id"])
        announcement["id"] = announcement_id
        del announcement["_id"]
        announcements.append(announcement)

    return announcements


@router.post("", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new announcement (teacher only)"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required to create announcements")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    # Validate dates
    today = datetime.now().strftime("%Y-%m-%d")
    if expiration_date < today:
        raise HTTPException(
            status_code=400, detail="Expiration date must be in the future")

    if start_date and start_date > expiration_date:
        raise HTTPException(
            status_code=400, detail="Start date must be before expiration date")

    # Create announcement
    announcement = {
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_at": today,
        "updated_at": today
    }

    result = announcements_collection.insert_one(announcement)

    announcement["id"] = str(result.inserted_id)

    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: Optional[str] = None,
    start_date: Optional[str] = None,
    expiration_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update an existing announcement (teacher only)"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required to update announcements")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    # Get the announcement
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    announcement = announcements_collection.find_one({"_id": obj_id})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Prepare update data
    update_data = {}
    if message is not None:
        update_data["message"] = message
    if start_date is not None:
        update_data["start_date"] = start_date
    if expiration_date is not None:
        update_data["expiration_date"] = expiration_date

    if update_data:
        today = datetime.now().strftime("%Y-%m-%d")
        update_data["updated_at"] = today

        # Validate dates if they were provided
        final_start_date = start_date if start_date is not None else announcement.get(
            "start_date")
        final_expiration_date = expiration_date if expiration_date is not None else announcement.get(
            "expiration_date")

        if final_expiration_date < today:
            raise HTTPException(
                status_code=400, detail="Expiration date must be in the future")

        if final_start_date and final_expiration_date and final_start_date > final_expiration_date:
            raise HTTPException(
                status_code=400, detail="Start date must be before expiration date")

        announcements_collection.update_one({"_id": obj_id}, {"$set": update_data})

    # Return updated announcement
    updated = announcements_collection.find_one({"_id": obj_id})
    updated["id"] = str(updated["_id"])
    del updated["_id"]

    return updated


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """Delete an announcement (teacher only)"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required to delete announcements")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    # Delete the announcement
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    result = announcements_collection.delete_one({"_id": obj_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted successfully"}
