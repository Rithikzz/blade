import json
import pandas as pd
import numpy as np
from pathlib import Path
from fastapi import HTTPException
from app.core.config import UPLOAD_DIR
from app.services.dataset_service import get_file_extension

def load_dataframe(dataset_id: str) -> tuple[pd.DataFrame, dict]:
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
            df = pd.read_csv(file_path)
        elif ext == ".xlsx":
            df = pd.read_excel(file_path)
        elif ext == ".json":
            df = pd.read_json(file_path)
        else:
            raise ValueError("Unsupported file type")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Unable to read dataset")

    return df, meta

def generate_profile(dataset_id: str):
    df, meta = load_dataframe(dataset_id)
    
    row_count = len(df)
    column_count = len(df.columns)
    
    if row_count == 0 or column_count == 0:
        raise HTTPException(status_code=400, detail="Cannot profile an empty dataset")

    # 1. Standardize missing values globally
    common_na = ['N/A', 'n/a', 'NA', 'NULL', 'null', 'NaN', 'None', '', 'INVALID']
    for col in df.columns:
        if df[col].dtype == 'object' or pd.api.types.is_string_dtype(df[col]):
            # replace exact matches
            df[col] = df[col].replace(common_na, np.nan)
            # replace whitespace-only strings
            df[col] = df[col].replace(r'^\s*$', np.nan, regex=True)

    # 2. Recompute global stats
    memory_usage = int(df.memory_usage(deep=True).sum())
    duplicate_rows = int(df.duplicated().sum())
    empty_rows = int(df.isnull().all(axis=1).sum())
    empty_columns = int(df.isnull().all(axis=0).sum())

    columns_profile = []
    findings = []
    
    score = 100
    components = {}

    if empty_rows > 0:
        penalty = 10
        score -= penalty
        components["empty_rows"] = penalty
        findings.append({
            "severity": "critical",
            "category": "empty_rows",
            "column": None,
            "message": f"{empty_rows} completely empty rows detected.",
            "evidence": {"empty_rows": empty_rows}
        })

    if empty_columns > 0:
        penalty = 10
        score -= penalty
        components["empty_columns"] = penalty

    # 3. Column Profiling
    total_missing_after_coercion = 0

    for col in df.columns:
        col_series = df[col]
        non_null_count = int(col_series.count())
        null_count = row_count - non_null_count
        null_percentage = (null_count / row_count) if row_count > 0 else 0
        
        if non_null_count > 0:
            unique_count = int(col_series.nunique(dropna=True))
        else:
            unique_count = 0
            
        unique_percentage = (unique_count / non_null_count) if non_null_count > 0 else 0

        if null_count == row_count:
            findings.append({
                "severity": "critical",
                "category": "empty_column",
                "column": str(col),
                "message": "Column is completely empty.",
                "evidence": {"null_count": null_count}
            })

        if unique_count == 1 and non_null_count > 0:
            findings.append({
                "severity": "info",
                "category": "constant_column",
                "column": str(col),
                "message": "Column has a constant value.",
                "evidence": {"value": str(col_series.dropna().iloc[0])}
            })

        pandas_dtype = str(col_series.dtype)
        
        # Logical Type Detection
        logical_type = "unknown"
        type_reason = "Default fallback"
        numeric_stats = None
        categorical_stats = None
        datetime_stats = None

        if non_null_count == 0:
            logical_type = "unknown"
            type_reason = "All values missing"
        else:
            # Check boolean
            if pd.api.types.is_bool_dtype(col_series) or set(col_series.dropna().astype(str).str.lower().unique()).issubset({'0', '1', 'true', 'false', 'y', 'n', 'yes', 'no'}):
                logical_type = "boolean"
                type_reason = "Contains boolean-like values"
            else:
                # Check numeric via coercion
                coerced_numeric = pd.to_numeric(col_series, errors='coerce')
                numeric_ratio = coerced_numeric.notna().sum() / non_null_count
                
                if pd.api.types.is_numeric_dtype(col_series) or numeric_ratio > 0.5:
                    if unique_percentage > 0.9 and ('id' in str(col).lower() or 'uuid' in str(col).lower()):
                        logical_type = "identifier"
                        type_reason = "High uniqueness and name suggests ID"
                    else:
                        logical_type = "numeric"
                        type_reason = "Majority of values are numeric"
                        
                    # Use coerced_numeric for stats and true null count
                    col_series = coerced_numeric
                    
                    new_nulls = int(col_series.isna().sum()) - null_count
                    if new_nulls > 0:
                        null_count += new_nulls
                        non_null_count -= new_nulls
                        null_percentage = (null_count / row_count) if row_count > 0 else 0
                        findings.append({
                            "severity": "warning",
                            "category": "invalid_numeric",
                            "column": str(col),
                            "message": f"{new_nulls} values could not be parsed as numbers.",
                            "evidence": {"invalid_numeric_count": new_nulls}
                        })
                        
                    unique_count = int(col_series.nunique(dropna=True))
                    unique_percentage = (unique_count / non_null_count) if non_null_count > 0 else 0
                    
                    if logical_type == "numeric":
                        numeric_stats = {
                            "min": float(col_series.min()) if pd.notnull(col_series.min()) else None,
                            "max": float(col_series.max()) if pd.notnull(col_series.max()) else None,
                            "mean": float(col_series.mean()) if pd.notnull(col_series.mean()) else None,
                            "median": float(col_series.median()) if pd.notnull(col_series.median()) else None,
                            "std": float(col_series.std()) if pd.notnull(col_series.std()) else None,
                            "p25": float(col_series.quantile(0.25)) if pd.notnull(col_series.quantile(0.25)) else None,
                            "p50": float(col_series.quantile(0.50)) if pd.notnull(col_series.quantile(0.50)) else None,
                            "p75": float(col_series.quantile(0.75)) if pd.notnull(col_series.quantile(0.75)) else None,
                        }
                        
                        if numeric_stats["p25"] is not None and numeric_stats["p75"] is not None:
                            iqr = numeric_stats["p75"] - numeric_stats["p25"]
                            if iqr > 0:
                                lower_bound = numeric_stats["p25"] - 1.5 * iqr
                                upper_bound = numeric_stats["p75"] + 1.5 * iqr
                                outliers = col_series[(col_series < lower_bound) | (col_series > upper_bound)]
                                outlier_count = int(outliers.count())
                                if outlier_count > 0:
                                    findings.append({
                                        "severity": "info",
                                        "category": "potential_outliers",
                                        "column": str(col),
                                        "message": f"{outlier_count} potential outliers detected.",
                                        "evidence": {"outlier_count": outlier_count}
                                    })
                                    
                elif pd.api.types.is_datetime64_any_dtype(col_series):
                    logical_type = "datetime"
                    type_reason = "Pandas recognized as datetime"
                else:
                    # String heuristics for Datetime
                    try:
                        sample = col_series.dropna().head(100)
                        parsed_dates = pd.to_datetime(sample, errors='coerce', format='mixed')
                        if parsed_dates.notna().sum() > 0.5 * len(sample):
                            logical_type = "datetime"
                            type_reason = "Values successfully parsed as dates"
                            full_parsed = pd.to_datetime(col_series, errors='coerce', format='mixed')
                            invalid_count = int(full_parsed.isna().sum()) - null_count
                            
                            datetime_stats = {
                                "min_date": str(full_parsed.min()) if pd.notnull(full_parsed.min()) else None,
                                "max_date": str(full_parsed.max()) if pd.notnull(full_parsed.max()) else None,
                                "invalid_date_count": max(0, invalid_count)
                            }
                            
                            if invalid_count > 0:
                                findings.append({
                                    "severity": "warning",
                                    "category": "invalid_dates",
                                    "column": str(col),
                                    "message": f"{invalid_count} values could not be parsed as dates.",
                                    "evidence": {"invalid_date_count": invalid_count}
                                })
                                penalty = min(10, int((invalid_count / row_count) * 100))
                                score -= penalty
                                components["invalid_dates"] = components.get("invalid_dates", 0) + penalty
                                
                        elif unique_percentage > 0.9 and ('id' in str(col).lower() or 'uuid' in str(col).lower()):
                            logical_type = "identifier"
                            type_reason = "High uniqueness and name suggests ID"
                        elif unique_percentage < 0.5 and unique_count < 100:
                            logical_type = "categorical"
                            type_reason = "Low uniqueness ratio, likely categorical"
                        else:
                            logical_type = "text"
                            type_reason = "High uniqueness, not recognized as ID or Date"
                    except Exception:
                        logical_type = "text"
                        type_reason = "Fallback text type"

        if null_percentage > 0.5:
            findings.append({
                "severity": "warning",
                "category": "missing_values",
                "column": str(col),
                "message": f"High missingness: {round(null_percentage*100,1)}% missing.",
                "evidence": {"null_percentage": null_percentage}
            })

        # Categorical Stats Calculation
        if logical_type in ["categorical", "boolean", "text"] and non_null_count > 0:
            val_counts = col_series.value_counts().head(10)
            top_vals = []
            for val, count in val_counts.items():
                top_vals.append({
                    "value": str(val),
                    "count": int(count),
                    "percentage": round((int(count) / non_null_count) * 100, 2)
                })
            categorical_stats = {
                "unique_count": unique_count,
                "top_values": top_vals
            }
            
            # Email validation check
            if 'email' in str(col).lower():
                # A very simple regex for email validation
                import re
                email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
                valid_emails = col_series.dropna().astype(str).str.match(email_regex)
                invalid_email_count = int((~valid_emails).sum())
                if invalid_email_count > 0:
                    findings.append({
                        "severity": "warning",
                        "category": "malformed_emails",
                        "column": str(col),
                        "message": f"{invalid_email_count} malformed email addresses detected.",
                        "evidence": {"invalid_email_count": invalid_email_count}
                    })

        total_missing_after_coercion += null_count

        columns_profile.append({
            "column_name": str(col),
            "inferred_type": logical_type,
            "pandas_dtype": pandas_dtype,
            "logical_type": logical_type,
            "type_reason": type_reason,
            "non_null_count": non_null_count,
            "null_count": null_count,
            "null_percentage": round(null_percentage, 4),
            "unique_count": unique_count,
            "unique_percentage": round(unique_percentage, 4),
            "numeric_stats": numeric_stats,
            "categorical_stats": categorical_stats,
            "datetime_stats": datetime_stats
        })

    # 4. Global missing values computation
    missing_values = total_missing_after_coercion
    total_cells = row_count * column_count
    missing_percentage = (missing_values / total_cells) if total_cells > 0 else 0.0

    if missing_percentage > 0:
        penalty = min(30, int(missing_percentage * 100))
        score -= penalty
        components["missing_values"] = penalty

    # 5. Advanced Duplicate Detection (Ignoring Identifiers)
    identifiers = [c["column_name"] for c in columns_profile if c["logical_type"] == "identifier"]
    if identifiers:
        df_no_id = df.drop(columns=identifiers, errors='ignore')
        dup_no_id = int(df_no_id.duplicated().sum())
        if dup_no_id > duplicate_rows:
            duplicate_rows = dup_no_id
            findings.append({
                "severity": "warning",
                "category": "duplicates_ignoring_id",
                "column": None,
                "message": f"{dup_no_id} duplicate rows detected when ignoring identifier columns.",
                "evidence": {"duplicate_count": dup_no_id}
            })

    if duplicate_rows > 0:
        dup_pct = duplicate_rows / row_count
        penalty = min(20, int(dup_pct * 100))
        score -= penalty
        components["duplicates"] = penalty
        if not any(f["category"] == "duplicates_ignoring_id" for f in findings):
            findings.append({
                "severity": "warning",
                "category": "duplicates",
                "column": None,
                "message": f"{duplicate_rows} duplicate rows detected.",
                "evidence": {"duplicate_count": duplicate_rows, "duplicate_percentage": round(dup_pct * 100, 2)}
            })

    # Ensure score is at least 0
    score = max(0, score)

    profile_data = {
        "dataset_id": dataset_id,
        "filename": meta["filename"],
        "row_count": row_count,
        "column_count": column_count,
        "memory_usage": memory_usage,
        "duplicate_rows": duplicate_rows,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "missing_values": missing_values,
        "missing_percentage": round(missing_percentage, 4),
        "columns": columns_profile,
        "quality_findings": findings,
        "quality_score": {
            "score": score,
            "components": components
        }
    }
    
    profile_path = UPLOAD_DIR / f"{dataset_id}.profile.json"
    
    def clean_nan(obj):
        if isinstance(obj, float) and np.isnan(obj):
            return None
        if isinstance(obj, dict):
            return {k: clean_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean_nan(i) for i in obj]
        return obj

    clean_profile_data = clean_nan(profile_data)

    with open(profile_path, "w") as f:
        json.dump(clean_profile_data, f)
        
    return clean_profile_data

def get_profile(dataset_id: str):
    profile_path = UPLOAD_DIR / f"{dataset_id}.profile.json"
    if not profile_path.exists():
        return None
    with open(profile_path, "r") as f:
        return json.load(f)
