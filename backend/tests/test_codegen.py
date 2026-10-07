import pytest
from app.codegen.validator import validate_code

def test_validator_safe():
    code = """
import pandas as pd
result = df.groupby('product')['sales'].sum()
    """
    # Should not raise
    validate_code(code)

def test_validator_dangerous_imports():
    code = """
import os
import pandas as pd
result = 1
    """
    with pytest.raises(ValueError, match="Forbidden import: os"):
        validate_code(code)

def test_validator_eval():
    code = """
import pandas as pd
result = eval("1+1")
    """
    with pytest.raises(ValueError, match="Forbidden function call: eval"):
        validate_code(code)

def test_validator_no_result():
    code = """
import pandas as pd
x = 1
    """
    with pytest.raises(ValueError, match="Code must assign the final output to a variable named 'result'"):
        validate_code(code)

def test_validator_syntax_error():
    code = """
import pandas as pd
result = df.groupby(
    """
    with pytest.raises(ValueError, match="Syntax Error"):
        validate_code(code)
