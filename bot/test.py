import os
import ast
import requests

class Parentage(ast.NodeTransformer):
    parent = None

    def visit(self, node):
        node.parent = self.parent
        self.parent = node
        node = super().visit(node)
        if isinstance(node, ast.AST):
            self.parent = node.parent
        return node

path = "dpy/discord/"
for root, _, files in os.walk(path):
    for file in files:
        filepath = os.path.join(root, file)
        without_root = filepath[len(path):]
        first_directory = without_root.split("/")[0]
        if first_directory == "types":
            continue
        
        if not file.endswith(".py"):
            continue
        
        if file.startswith("_"):
            continue

        with open(filepath) as f:
            code = f.read()
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("_"):
                    continue
                
                print(f'{node.name} | {node.lineno}-{node.end_lineno}')
                continue
                for child in node.body:
                    if not isinstance(child, ast.AsyncFunctionDef) and not isinstance(child, ast.FunctionDef):
                        continue
                    
                    if child.name.startswith("_"):
                        continue
                    
                    function_name = child.name
                    start_line = child.lineno
                    end_line = child.end_lineno
                    print(f'{node.name}.{function_name} | {start_line}-{end_line}')