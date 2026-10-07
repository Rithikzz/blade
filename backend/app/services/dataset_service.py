import os
import uuid
import pandas as pd
import json
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.core.config import UPLOAD_DIR

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".json"}
MAX_PREVIEW_ROWS = 20

def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()

def is_allowed_file(filename: str) -> bool:
    return get_file_extension(filename) in ALLOWED_EXTENSIONS

async def save_upload_file(upload_file: UploadFile, dataset_id: str) -> Path:
    ext = get_file_extension(upload_file.filename)
    safe_filename = f"{dataset_id}{ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    content = await upload_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty dataset")
        
    with open(file_path, "wb") as f:
        f.write(content)
        
    return file_path

def parse_dataset_info(file_path: Path, filename: str) -> dict:
    ext = get_file_extension(filename)
    
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext == ".xlsx":
            df = pd.read_excel(file_path)
        elif ext == ".json":
            df = pd.read_json(file_path)
        else:
            raise ValueError("Unsupported file type")
    except ValueError as e:
        if "No objects to concatenate" in str(e) or "empty" in str(e).lower():
            raise HTTPException(status_code=400, detail="Empty dataset")
        raise HTTPException(status_code=400, detail=f"Unable to parse dataset: {str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Unable to parse dataset or corrupted file")

    if df.empty:
        raise HTTPException(status_code=400, detail="Empty dataset")

    # Handle NaN values to make JSON compliant
    df = df.fillna(0) # or replace with None depending on needs. Let's use string 'NaN' or just drop? 
    # Actually just replacing nan with None for JSON serialization.
    df = df.replace({pd.NA: None})
    
    rows, cols = df.shape
    column_names = df.columns.tolist()

    return {
        "rows": rows,
        "columns": cols,
        "column_names": [str(c) for c in column_names]
    }

def list_datasets():
    datasets = []
    # Simple list based on files in upload_dir, ideally we'd store metadata in a db/json.
    # We will look for a companion .meta.json file for each uploaded dataset.
    for meta_file in UPLOAD_DIR.glob("*.meta.json"):
        with open(meta_file, "r") as f:
            meta = json.load(f)
            datasets.append(meta)
    return datasets

def get_dataset_preview(dataset_id: str):
    # Find metadata
    meta_path = UPLOAD_DIR / f"{dataset_id}.meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    with open(meta_path, "r") as f:
        meta = json.load(f)
        
    ext = get_file_extension(meta["filename"])
    file_path = UPLOAD_DIR / f"{dataset_id}{ext}"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file not found")
        
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path, nrows=MAX_PREVIEW_ROWS)
        elif ext == ".xlsx":
            df = pd.read_excel(file_path, nrows=MAX_PREVIEW_ROWS)
        elif ext == ".json":
            df = pd.read_json(file_path)
            if len(df) > MAX_PREVIEW_ROWS:
                df = df.head(MAX_PREVIEW_ROWS)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Unable to read dataset for preview")

    # Replace NaNs with None for JSON response
    df = df.where(pd.notnull(df), None)

    preview_data = df.to_dict(orient="records")
    
    return {
        "dataset_id": dataset_id,
        "filename": meta["filename"],
        "rows": meta["rows"],
        "columns": meta["columns"],
        "column_names": meta["column_names"],
        "preview": preview_data
    }

async def process_upload(file: UploadFile):
    if not is_allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type")
        
    dataset_id = str(uuid.uuid4())
    
    # Save the file
    file_path = await save_upload_file(file, dataset_id)
    
    # Parse and validate
    try:
        info = parse_dataset_info(file_path, file.filename)
    except Exception as e:
        # cleanup invalid file
        if file_path.exists():
            os.remove(file_path)
        raise e
        
    ext = get_file_extension(file.filename)
    
    metadata = {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "file_type": ext.lstrip("."),
        "rows": info["rows"],
        "columns": info["columns"],
        "column_names": info["column_names"]
    }
    
    # Save metadata
    meta_path = UPLOAD_DIR / f"{dataset_id}.meta.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f)
        
    return {
        "success": True,
        **metadata
    }

def get_dataset_path(dataset_id: str) -> str:
    meta_path = UPLOAD_DIR / f"{dataset_id}.meta.json"
    if not meta_path.exists():
        return None
    import json
    with open(meta_path, "r") as f:
        meta = json.load(f)
    ext = get_file_extension(meta["filename"])
    file_path = UPLOAD_DIR / f"{dataset_id}{ext}"
    if not file_path.exists():
        return None
    return str(file_path.resolve())
