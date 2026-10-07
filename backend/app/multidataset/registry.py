from app.core.config import UPLOAD_DIR
from app.services.profiling_service import get_profile

def get_available_datasets():
    datasets = []
    for profile_path in UPLOAD_DIR.glob("*.profile.json"):
        dataset_id = profile_path.name.replace(".profile.json", "")
        profile = get_profile(dataset_id)
        if profile:
            datasets.append({
                "dataset_id": dataset_id,
                "filename": profile.get("filename"),
                "rows": profile.get("row_count"),
                "columns": [col["column_name"] for col in profile.get("columns", [])]
            })
    return datasets
