import pandas as pd
from typing import List, Dict
import re
from app.services.profiling_service import get_profile, load_dataframe
from app.multidataset.schemas import DatasetRelationship

def normalize_name(name: str) -> str:
    name = str(name).lower()
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def detect_relationships(dataset_ids: List[str]) -> List[DatasetRelationship]:
    relationships = []
    
    # Load all profiles
    profiles = {ds_id: get_profile(ds_id) for ds_id in dataset_ids}
    
    # Load dataframes (we'll only load them when needed for overlap checks to save time, or load all at once if small enough)
    dfs = {}
    
    for i in range(len(dataset_ids)):
        for j in range(i + 1, len(dataset_ids)):
            left_id = dataset_ids[i]
            right_id = dataset_ids[j]
            
            p_left = profiles.get(left_id)
            p_right = profiles.get(right_id)
            
            if not p_left or not p_right:
                continue
                
            left_cols = p_left.get("columns", [])
            right_cols = p_right.get("columns", [])
            
            for l_col in left_cols:
                for r_col in right_cols:
                    rel = evaluate_column_pair(left_id, p_left, l_col, right_id, p_right, r_col, dfs)
                    if rel and rel.compatibility_score >= 0.4:
                        relationships.append(rel)
                        
    return relationships

def evaluate_column_pair(left_id: str, p_left: dict, l_col: dict, right_id: str, p_right: dict, r_col: dict, dfs: dict) -> DatasetRelationship:
    evidence = []
    warnings = []
    
    score = 0.0
    
    l_name = l_col["column_name"]
    r_name = r_col["column_name"]
    
    l_norm = normalize_name(l_name)
    r_norm = normalize_name(r_name)
    
    # 1. Exact / Normalized Name Match (20%)
    if l_name == r_name:
        score += 0.20
        evidence.append("Exact column-name match")
    elif l_norm == r_norm and len(l_norm) > 2:
        score += 0.15
        evidence.append("Normalized column-name match")
    elif l_norm in r_norm or r_norm in l_norm:
        if len(l_norm) > 3 and len(r_norm) > 3:
            score += 0.05
            evidence.append("Partial column-name match")
            
    # 2. Type Compatibility (15%)
    l_type = l_col.get("logical_type")
    r_type = r_col.get("logical_type")
    if l_type == r_type and l_type not in ["unknown"]:
        score += 0.15
        evidence.append(f"Compatible data types ({l_type})")
    elif l_type in ["identifier", "text"] and r_type in ["identifier", "text"]:
        score += 0.10
        evidence.append(f"Compatible data types ({l_type} / {r_type})")
    elif l_type in ["numeric", "identifier"] and r_type in ["numeric", "identifier"]:
        score += 0.10
        evidence.append(f"Compatible data types ({l_type} / {r_type})")
    else:
        warnings.append(f"Type mismatch: {l_type} vs {r_type}")
        
    # 3. Uniqueness and Identifier Semantics (15% + 10%)
    l_unique_pct = l_col.get("unique_percentage", 0)
    r_unique_pct = r_col.get("unique_percentage", 0)
    
    l_is_id = (l_unique_pct > 0.9 or l_type == "identifier")
    r_is_id = (r_unique_pct > 0.9 or r_type == "identifier")
    
    if l_is_id and r_is_id:
        score += 0.25
        evidence.append(f"Both columns have high uniqueness (Primary Key to Primary Key / 1-to-1)")
        rel_type = "one_to_one"
    elif l_is_id:
        score += 0.20
        evidence.append(f"Left column {l_name} is highly unique (Primary Key)")
        rel_type = "one_to_many"
    elif r_is_id:
        score += 0.20
        evidence.append(f"Right column {r_name} is highly unique (Primary Key)")
        rel_type = "many_to_one"
    else:
        rel_type = "many_to_many"
        warnings.append("Many-to-many relationship detected (neither side is highly unique)")
        
    # 4. Null Quality (10%)
    l_null_pct = l_col.get("null_percentage", 0)
    r_null_pct = r_col.get("null_percentage", 0)
    
    if l_null_pct < 0.05 and r_null_pct < 0.05:
        score += 0.10
        evidence.append("Low null rates in both columns")
    elif l_null_pct > 0.5 or r_null_pct > 0.5:
        warnings.append("High null rates in join keys")
        
    # Early exit for totally incompatible columns to avoid expensive overlap computation
    if score < 0.15:
        return None
        
    # 5. Value Overlap (30%)
    if left_id not in dfs:
        dfs[left_id], _ = load_dataframe(left_id)
    if right_id not in dfs:
        dfs[right_id], _ = load_dataframe(right_id)
        
    df_l = dfs[left_id]
    df_r = dfs[right_id]
    
    if l_name in df_l.columns and r_name in df_r.columns:
        l_set = set(df_l[l_name].dropna().astype(str).unique())
        r_set = set(df_r[r_name].dropna().astype(str).unique())
        
        if len(l_set) > 0 and len(r_set) > 0:
            intersection = l_set.intersection(r_set)
            overlap_l = len(intersection) / len(l_set)
            overlap_r = len(intersection) / len(r_set)
            max_overlap = max(overlap_l, overlap_r)
            
            if max_overlap > 0.9:
                score += 0.30
                evidence.append(f"Very high value overlap ({max_overlap:.1%} max)")
            elif max_overlap > 0.5:
                score += 0.20
                evidence.append(f"High value overlap ({max_overlap:.1%} max)")
            elif max_overlap > 0.1:
                score += 0.10
                evidence.append(f"Moderate value overlap ({max_overlap:.1%} max)")
            elif max_overlap > 0.0:
                warnings.append(f"Low overlap ({max_overlap:.1%} max)")
            else:
                warnings.append("Zero overlap. These columns do not intersect.")
                score = 0
    
    confidence = "unsafe"
    if score >= 0.8 and rel_type != "many_to_many" and len(warnings) == 0:
        confidence = "high"
    elif score >= 0.6:
        confidence = "medium"
    elif score >= 0.4:
        confidence = "low"
        
    if "Zero overlap. These columns do not intersect." in warnings:
        confidence = "unsafe"
        
    return DatasetRelationship(
        left_dataset_id=left_id,
        right_dataset_id=right_id,
        left_column=l_name,
        right_column=r_name,
        relationship_type=rel_type,
        compatibility_score=round(score, 2),
        confidence=confidence,
        evidence=evidence,
        warnings=warnings
    )
