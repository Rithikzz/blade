import sys
import json
import pandas as pd
import numpy as np
import math
import statistics
import duckdb
import time

MAX_ROWS = 100
MAX_COLS = 30

def clean_value(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (np.integer, np.floating)):
        val = val.item()
    if isinstance(val, float):
        if math.isinf(val) or math.isnan(val):
            return None
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    return val

def serialize_result(result):
    truncated = False
    
    if isinstance(result, pd.DataFrame):
        total_rows = len(result)
        
        if total_rows > MAX_ROWS:
            result = result.head(MAX_ROWS)
            truncated = True
            
        if len(result.columns) > MAX_COLS:
            result = result.iloc[:, :MAX_COLS]
            truncated = True
            
        columns = list(result.columns.astype(str))
        rows = []
        for row in result.itertuples(index=False):
            rows.append([clean_value(x) for x in row])
            
        return {
            "type": "dataframe",
            "columns": columns,
            "rows": rows,
            "total_rows": total_rows,
            "returned_rows": len(rows)
        }, truncated

    elif isinstance(result, pd.Series):
        total_rows = len(result)
        if total_rows > MAX_ROWS:
            result = result.head(MAX_ROWS)
            truncated = True
        
        values = [clean_value(x) for x in result.values]
        return {
            "type": "series",
            "values": values,
            "total_rows": total_rows,
            "returned_rows": len(values)
        }, truncated

    elif isinstance(result, dict):
        cleaned_dict = {str(k): clean_value(v) for k, v in result.items()}
        return {
            "type": "object",
            "value": cleaned_dict
        }, truncated

    else:
        # Scalar or string
        return {
            "type": "scalar",
            "value": clean_value(result)
        }, truncated

def main():
    if len(sys.argv) != 2:
        print("Usage: runner.py <config.json>")
        sys.exit(1)
        
    config_path = sys.argv[1]
    with open(config_path, 'r') as f:
        config = json.load(f)
        
    code_path = config['code_path']
    output_path = config['output_path']
    datasets_config = config.get('datasets', {})
    
    local_vars = {"pd": pd, "np": np, "math": math, "statistics": statistics, "duckdb": duckdb}
    
    for var_name, ds_path in datasets_config.items():
        try:
            if ds_path.endswith('.csv'):
                ds = pd.read_csv(ds_path)
            elif ds_path.endswith('.xlsx'):
                ds = pd.read_excel(ds_path)
            elif ds_path.endswith('.json'):
                ds = pd.read_json(ds_path)
            else:
                raise ValueError(f"Unsupported format for {ds_path}")
            local_vars[var_name] = ds
        except Exception as e:
            sys.exit(f"Failed to load dataset {var_name}: {str(e)}")
            
    # Load code
    with open(code_path, 'r') as f:
        code = f.read()
        
    # Execute code
    start_time = time.time()
    try:
        exec(code, {}, local_vars)
    except Exception as e:
        with open(output_path, 'w') as f:
            json.dump({"error": str(e), "success": False}, f)
        sys.exit(0)
        
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    if "result" not in local_vars:
        with open(output_path, 'w') as f:
            json.dump({"error": "Generated code did not produce a 'result' variable.", "success": False}, f)
        sys.exit(0)
        
    # Serialize result
    try:
        serialized, truncated = serialize_result(local_vars["result"])
        output_data = {
            "success": True,
            "execution_time_ms": execution_time_ms,
            "result": serialized,
            "truncated": truncated
        }
    except Exception as e:
        output_data = {
            "success": False,
            "error": f"Failed to serialize result: {str(e)}"
        }
        
    with open(output_path, 'w') as f:
        json.dump(output_data, f)

if __name__ == "__main__":
    main()
