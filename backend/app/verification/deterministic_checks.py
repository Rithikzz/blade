import pandas as pd
import math
from typing import Any, Dict, List

def safe_float(val: Any) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return float('nan')

def apply_filters(df: pd.DataFrame, filters: List[Dict]) -> pd.DataFrame:
    filtered_df = df.copy()
    for f in filters:
        col = f.get('column')
        op = f.get('operator')
        val = f.get('value')
        
        if col not in filtered_df.columns or col == 'string':
            continue
            
        if op == 'equals':
            if pd.api.types.is_numeric_dtype(filtered_df[col]):
                try:
                    num_val = float(val)
                    filtered_df = filtered_df[filtered_df[col] == num_val]
                except ValueError:
                    filtered_df = filtered_df[filtered_df[col].astype(str) == str(val)]
            else:
                filtered_df = filtered_df[filtered_df[col] == val]
        elif op == 'contains':
            filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(str(val), na=False)]
        elif op == 'greater_than':
            try:
                filtered_df = filtered_df[pd.to_numeric(filtered_df[col], errors='coerce') > float(val)]
            except ValueError:
                pass
        elif op == 'less_than':
            try:
                filtered_df = filtered_df[pd.to_numeric(filtered_df[col], errors='coerce') < float(val)]
            except ValueError:
                pass
    return filtered_df

def apply_time_range(df: pd.DataFrame, time_range: Dict) -> pd.DataFrame:
    col = time_range.get('column')
    start = time_range.get('start')
    end = time_range.get('end')
    
    if not col or col not in df.columns or col == 'string':
        return df
        
    filtered_df = df.copy()
    
    # Try converting to datetime
    date_col = pd.to_datetime(filtered_df[col], errors='coerce')
    
    if start:
        start_date = pd.to_datetime(start, errors='coerce')
        if not pd.isna(start_date):
            filtered_df = filtered_df[date_col >= start_date]
            date_col = date_col[date_col >= start_date]
            
    if end:
        end_date = pd.to_datetime(end, errors='coerce')
        if not pd.isna(end_date):
            filtered_df = filtered_df[date_col <= end_date]
            
    return filtered_df

def verify_aggregation(df: pd.DataFrame, plan: Dict) -> Any:
    target_metric = plan.get('target_metric')
    agg = plan.get('aggregation')
    
    if not target_metric or target_metric == 'string' or target_metric not in df.columns:
        if agg == 'count':
            return len(df)
        return None
        
    series = pd.to_numeric(df[target_metric], errors='coerce')
    
    if agg == 'sum':
        val = series.sum(); return float(val) if pd.notna(val) else None
    elif agg == 'mean' or agg == 'average':
        val = series.mean(); return float(val) if pd.notna(val) else None
    elif agg == 'min':
        val = series.min(); return float(val) if pd.notna(val) else None
    elif agg == 'max':
        val = series.max(); return float(val) if pd.notna(val) else None
    elif agg == 'median':
        val = series.median(); return float(val) if pd.notna(val) else None
    elif agg == 'count':
        val = series.count(); return int(val) if pd.notna(val) else None
    
    return None
    
def verify_groupby(df: pd.DataFrame, plan: Dict) -> pd.DataFrame:
    group_by = plan.get('group_by', [])
    target_metric = plan.get('target_metric')
    agg = plan.get('aggregation')
    
    # Remove 'string' artifacts
    group_by = [g for g in group_by if g != 'string']
    
    if not group_by or not all(g in df.columns for g in group_by):
        return None
        
    if not target_metric or target_metric == 'string' or target_metric not in df.columns:
        if agg == 'count':
            return df.groupby(group_by).size().reset_index(name='count')
        return None
        
    if agg == 'sum':
        return df.groupby(group_by, dropna=False)[target_metric].sum().reset_index()
    elif agg == 'mean' or agg == 'average':
        return df.groupby(group_by, dropna=False)[target_metric].mean().reset_index()
    elif agg == 'min':
        return df.groupby(group_by, dropna=False)[target_metric].min().reset_index()
    elif agg == 'max':
        return df.groupby(group_by, dropna=False)[target_metric].max().reset_index()
    elif agg == 'median':
        return df.groupby(group_by, dropna=False)[target_metric].median().reset_index()
    elif agg == 'count':
        return df.groupby(group_by, dropna=False)[target_metric].count().reset_index()
        
    return None

def apply_sort_limit(df: pd.DataFrame, plan: Dict) -> pd.DataFrame:
    sort = plan.get('sort')
    limit = plan.get('limit')
    
    if sort and isinstance(sort, dict):
        col = sort.get('column')
        direction = sort.get('direction', 'asc')
        if col and col != 'string' and col in df.columns:
            df = df.sort_values(by=col, ascending=(direction == 'asc'))
            
    if limit and isinstance(limit, int):
        df = df.head(limit)
        
    return df
