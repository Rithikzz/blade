import pytest
import os
import tempfile
import pandas as pd
from app.execution.executor import execute_analysis
from app.execution.sandbox import execute_in_sandbox

@pytest.fixture
def temp_dataset():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        df = pd.DataFrame({"product": ["A", "B", "C"], "sales": [10, 20, 30]})
        df.to_csv(f.name, index=False)
        path = f.name
    yield path
    os.remove(path)

def test_execute_analysis_success(temp_dataset, monkeypatch):
    monkeypatch.setattr("app.execution.executor.get_dataset_path", lambda x: temp_dataset)
    
    code = """
import pandas as pd
result = df['sales'].sum()
"""
    result = execute_analysis("test_id", code)
    assert result["success"] is True
    assert result["result"]["type"] == "scalar"
    assert result["result"]["value"] == 60
    assert "code_hash" in result

def test_execute_analysis_dangerous_code(temp_dataset, monkeypatch):
    monkeypatch.setattr("app.execution.executor.get_dataset_path", lambda x: temp_dataset)
    
    code = """
import os
result = 1
"""
    result = execute_analysis("test_id", code)
    assert result["success"] is False
    assert "Forbidden import" in result["error"]

def test_execute_analysis_no_result(temp_dataset, monkeypatch):
    monkeypatch.setattr("app.execution.executor.get_dataset_path", lambda x: temp_dataset)
    
    code = """
import pandas as pd
x = 1
"""
    result = execute_analysis("test_id", code)
    assert result["success"] is False
    assert "Code must assign the final output to a variable named 'result'" in result["error"]

def test_execute_analysis_execution_error(temp_dataset, monkeypatch):
    monkeypatch.setattr("app.execution.executor.get_dataset_path", lambda x: temp_dataset)
    
    # Valid syntax, but throws error at runtime (e.g. division by zero, or invalid column)
    code = """
import pandas as pd
result = df['missing_column'].sum()
"""
    result = execute_analysis("test_id", code)
    assert result["success"] is False
    assert "error" in result

def test_execute_analysis_dataframe_truncation(temp_dataset, monkeypatch):
    monkeypatch.setattr("app.execution.executor.get_dataset_path", lambda x: temp_dataset)
    
    # 101 rows to test truncation
    code = """
import pandas as pd
result = pd.DataFrame({'a': range(105)})
"""
    result = execute_analysis("test_id", code)
    assert result["success"] is True
    assert result["truncated"] is True
    assert result["result"]["type"] == "dataframe"
    assert result["result"]["returned_rows"] == 100
    assert result["result"]["total_rows"] == 105

