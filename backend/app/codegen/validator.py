import ast

class CodeValidator(ast.NodeVisitor):
    def __init__(self):
        self.allowed_modules = {"pandas", "numpy", "duckdb", "math", "statistics", "pd", "np"}
        self.forbidden_functions = {"eval", "exec", "open", "__import__", "globals", "locals"}
        self.has_result_assignment = False
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module not in self.allowed_modules:
                self.errors.append(f"Forbidden import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module not in self.allowed_modules:
                self.errors.append(f"Forbidden import from: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.forbidden_functions:
                self.errors.append(f"Forbidden function call: {node.func.id}")
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "result":
                self.has_result_assignment = True
        self.generic_visit(node)

def validate_code(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax Error: {str(e)}")

    validator = CodeValidator()
    validator.visit(tree)

    if not validator.has_result_assignment:
        validator.errors.append("Code must assign the final output to a variable named 'result'")

    if validator.errors:
        raise ValueError("Code validation failed: " + "; ".join(validator.errors))
