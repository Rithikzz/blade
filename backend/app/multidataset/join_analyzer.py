import pandas as pd
from app.services.profiling_service import load_dataframe
from app.multidataset.schemas import JoinPreviewRequest, JoinPreviewResponse

def preview_join(request: JoinPreviewRequest) -> JoinPreviewResponse:
    df_l, _ = load_dataframe(request.left_dataset_id)
    df_r, _ = load_dataframe(request.right_dataset_id)
    
    left_rows = len(df_l)
    right_rows = len(df_r)
    
    if request.left_column not in df_l.columns or request.right_column not in df_r.columns:
        raise ValueError("Join columns not found in datasets")
        
    df_l_key = df_l[request.left_column].dropna().astype(str)
    df_r_key = df_r[request.right_column].dropna().astype(str)
    
    null_left = left_rows - len(df_l_key)
    null_right = right_rows - len(df_r_key)
    
    # Calculate duplicates in join key
    l_counts = df_l_key.value_counts()
    r_counts = df_r_key.value_counts()
    
    l_dups = (l_counts > 1).sum()
    r_dups = (r_counts > 1).sum()
    
    # Estimated Output Rows (Inner Join)
    # We can actually just do a fast merge on the keys
    l_df_small = pd.DataFrame({request.left_column: df_l_key})
    r_df_small = pd.DataFrame({request.right_column: df_r_key})
    
    merged = l_df_small.merge(r_df_small, left_on=request.left_column, right_on=request.right_column, how='inner')
    
    matched_rows = len(merged)
    
    # Left and Right unmatched
    l_set = set(df_l_key.unique())
    r_set = set(df_r_key.unique())
    
    unmatched_left = len(l_set - r_set)
    unmatched_right = len(r_set - l_set)
    
    estimated_output_rows = matched_rows
    
    warnings = []
    if l_dups > 0 and r_dups > 0:
        warnings.append("Many-to-many join detected. This will multiply rows and may be unsafe.")
    if estimated_output_rows > (left_rows * 2) and estimated_output_rows > (right_rows * 2):
        warnings.append("Join explosion detected. Output rows significantly exceed input rows.")
    if matched_rows == 0:
        warnings.append("No matched rows found.")
        
    join_type = "inner"
        
    return JoinPreviewResponse(
        left_rows=left_rows,
        right_rows=right_rows,
        matched_rows=matched_rows,
        unmatched_left_rows=unmatched_left,
        unmatched_right_rows=unmatched_right,
        estimated_output_rows=estimated_output_rows,
        duplicate_key_counts={"left": int(l_dups), "right": int(r_dups)},
        null_key_counts={"left": int(null_left), "right": int(null_right)},
        join_type=join_type,
        warnings=warnings
    )
