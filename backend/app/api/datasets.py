from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services import dataset_service, profiling_service

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    return await dataset_service.process_upload(file)

@router.get("/{dataset_id}/preview")
def get_dataset_preview(dataset_id: str):
    return dataset_service.get_dataset_preview(dataset_id)

@router.get("")
def list_datasets():
    return dataset_service.list_datasets()

@router.post("/{dataset_id}/profile")
def generate_dataset_profile(dataset_id: str):
    return profiling_service.generate_profile(dataset_id)

@router.get("/{dataset_id}/profile")
def get_dataset_profile(dataset_id: str):
    profile = profiling_service.get_profile(dataset_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please generate it first.")
    return profile

from pydantic import BaseModel
from typing import List
from app.multidataset.registry import get_available_datasets
from app.multidataset.relationship_detector import detect_relationships
from app.multidataset.join_analyzer import preview_join
from app.multidataset.schemas import JoinPreviewRequest

@router.get("/available/all") # modified path to avoid collision with list_datasets which was mapped to "" and might conflict with "/available". But actually we can just map to "/available" and put it above "/{dataset_id}/preview" if needed. Let's use "/available" and fix route orders later if needed.
def get_all_available_datasets():
    return {"datasets": get_available_datasets()}

class RelationshipRequest(BaseModel):
    dataset_ids: List[str]

@router.post("/relationships")
def discover_relationships(request: RelationshipRequest):
    return {"relationships": detect_relationships(request.dataset_ids)}

@router.post("/join-preview")
def get_join_preview(request: JoinPreviewRequest):
    return preview_join(request)

