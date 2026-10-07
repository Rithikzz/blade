from app.multidataset.schemas import MultiDatasetAnalysisPlan, JoinSpecification
from app.multidataset.join_analyzer import preview_join
from app.multidataset.schemas import JoinPreviewRequest
from app.services.profiling_service import get_profile

class JoinValidationError(Exception):
    pass

def validate_join_plan(plan: MultiDatasetAnalysisPlan):
    # 1. Check if datasets exist
    for ds_ref in plan.datasets:
        if not get_profile(ds_ref.dataset_id):
            raise JoinValidationError(f"Dataset {ds_ref.dataset_id} not found.")

    for join in plan.joins:
        # Check datasets exist
        p_left = get_profile(join.left_dataset_id)
        p_right = get_profile(join.right_dataset_id)
        
        if not p_left:
            raise JoinValidationError(f"Left dataset {join.left_dataset_id} in join not found.")
        if not p_right:
            raise JoinValidationError(f"Right dataset {join.right_dataset_id} in join not found.")
            
        # Check columns exist
        l_cols = [c["column_name"] for c in p_left.get("columns", [])]
        r_cols = [c["column_name"] for c in p_right.get("columns", [])]
        
        if join.left_column not in l_cols:
            raise JoinValidationError(f"Column {join.left_column} not found in dataset {join.left_dataset_id}")
        if join.right_column not in r_cols:
            raise JoinValidationError(f"Column {join.right_column} not found in dataset {join.right_dataset_id}")
            
        # Preview join
        preview = preview_join(JoinPreviewRequest(
            left_dataset_id=join.left_dataset_id,
            right_dataset_id=join.right_dataset_id,
            left_column=join.left_column,
            right_column=join.right_column
        ))
        
        if preview.matched_rows == 0:
            raise JoinValidationError(f"Join on {join.left_column} and {join.right_column} produces 0 matched rows.")
            
        # Explosion check
        # Allow some multiplier, but not an extreme one
        # If output rows > max(left_rows, right_rows) * 10
        if preview.estimated_output_rows > max(preview.left_rows, preview.right_rows) * 5 and preview.estimated_output_rows > 1000:
             raise JoinValidationError("Join explosion detected. The selected join multiplied the dataset unexpectedly.")
             
        # Type compatibility - we assume relationship detector did this, but we can enforce it.
        # It's better to just rely on the overlap / preview results for safety.
        
    return True
