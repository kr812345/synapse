import ast
import os
import sys

TARGET_DIRS = [
    "/root/synapse/models",
    "/root/synapse/departments",
    "/root/synapse/kernel",
    "/root/synapse/events",
    "/root/synapse/memory",
    "/root/synapse/registry",
    "/root/synapse/scheduler",
    "/root/synapse/shared",
]

SUSPICIOUS_KEYWORDS = [
    "mock", "fake", "stub", "dummy", "placeholder", "todo", "notimplemented"
]

class ASTInspector(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.findings = []

    def visit_FunctionDef(self, node):
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node):
        # Check for facade / empty function body
        body_non_doc = [
            n for n in node.body 
            if not (isinstance(n, ast.Expr) and isinstance(n.value, (ast.Str, ast.Constant)))
        ]

        if not body_non_doc:
            self.findings.append({
                "file": self.filename,
                "line": node.lineno,
                "func": node.name,
                "type": "EMPTY_FUNCTION_BODY",
                "details": "Function body contains no operational code"
            })
            return

        if len(body_non_doc) == 1:
            stmt = body_non_doc[0]
            if isinstance(stmt, ast.Pass):
                self.findings.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "func": node.name,
                    "type": "FACADE_PASS",
                    "details": "Function contains only 'pass'"
                })
            elif isinstance(stmt, ast.Return):
                # Check if returning constant string or int
                if isinstance(stmt.value, ast.Constant):
                    val_str = str(stmt.value.value).lower()
                    for kw in SUSPICIOUS_KEYWORDS:
                        if kw in val_str:
                            self.findings.append({
                                "file": self.filename,
                                "line": node.lineno,
                                "func": node.name,
                                "type": "HARDCODED_SUSPICIOUS_RETURN",
                                "details": f"Returns suspicious constant: {stmt.value.value}"
                            })

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            val_lower = node.value.lower()
            for kw in SUSPICIOUS_KEYWORDS:
                if kw in val_lower:
                    # Ignore docstrings or harmless strings if needed, but flag for audit review
                    self.findings.append({
                        "file": self.filename,
                        "line": node.lineno,
                        "type": "SUSPICIOUS_STRING_CONSTANT",
                        "details": f"String constant contains '{kw}': {node.value[:50]}"
                    })
        self.generic_visit(node)

def run_ast_audit():
    all_findings = []
    files_scanned = 0

    for target_dir in TARGET_DIRS:
        if not os.path.exists(target_dir):
            continue
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    files_scanned += 1
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            tree = ast.parse(f.read(), filename=filepath)
                        inspector = ASTInspector(filepath)
                        inspector.visit(tree)
                        all_findings.extend(inspector.findings)
                    except Exception as e:
                        all_findings.append({
                            "file": filepath,
                            "line": 0,
                            "type": "PARSE_ERROR",
                            "details": str(e)
                        })

    print(f"Scanned {files_scanned} files across production modules.")
    print(f"Total findings: {len(all_findings)}")
    for f in all_findings:
        print(f"[{f['type']}] {f['file']}:{f['line']} ({f.get('func', 'N/A')}) — {f['details']}")

if __name__ == "__main__":
    run_ast_audit()
