"""Python-only extract of BFCL's ast_parse, lifted verbatim from
model_handler/utils.py at gorilla commit 30124c4399 (BFCL V2 Live release).
Only the Java/JavaScript branches are dropped, so they cannot pull in tree-sitter.
Python parsing semantics are unchanged."""
import ast


def ast_parse(input_str, language="Python"):
    assert language == "Python", "this extract supports Python only"
    cleaned_input = input_str.strip("[]'")
    parsed = ast.parse(cleaned_input, mode="eval")
    extracted = []
    if isinstance(parsed.body, ast.Call):
        extracted.append(resolve_ast_call(parsed.body))
    else:
        for elem in parsed.body.elts:
            assert isinstance(elem, ast.Call)
            extracted.append(resolve_ast_call(elem))
    return extracted


def resolve_ast_call(elem):
    # Handle nested attributes for deeply nested module paths
    func_parts = []
    func_part = elem.func
    while isinstance(func_part, ast.Attribute):
        func_parts.append(func_part.attr)
        func_part = func_part.value
    if isinstance(func_part, ast.Name):
        func_parts.append(func_part.id)
    func_name = ".".join(reversed(func_parts))
    args_dict = {}
    for arg in elem.keywords:
        output = resolve_ast_by_type(arg.value)
        args_dict[arg.arg] = output
    return {func_name: args_dict}


def resolve_ast_by_type(value):
    if isinstance(value, ast.Constant):
        if value.value is Ellipsis:
            output = "..."
        else:
            output = value.value
    elif isinstance(value, ast.UnaryOp):
        output = -value.operand.value
    elif isinstance(value, ast.List):
        output = [resolve_ast_by_type(v) for v in value.elts]
    elif isinstance(value, ast.Dict):
        output = {
            resolve_ast_by_type(k): resolve_ast_by_type(v)
            for k, v in zip(value.keys, value.values)
        }
    elif isinstance(
        value, ast.NameConstant
    ):  # Added this condition to handle boolean values
        output = value.value
    elif isinstance(
        value, ast.BinOp
    ):  # Added this condition to handle function calls as arguments
        output = eval(ast.unparse(value))
    elif isinstance(value, ast.Name):
        output = value.id
    elif isinstance(value, ast.Call):
        if len(value.keywords)==0:
            output = ast.unparse(value)
        else:
            output = resolve_ast_call(value)
    elif isinstance(value, ast.Tuple):
        output = tuple(resolve_ast_by_type(v) for v in value.elts)
    elif isinstance(value, ast.Lambda):
        output = eval(ast.unparse(value.body[0].value))
    elif isinstance(value, ast.Ellipsis):
        output = "..."
    elif isinstance(value, ast.Subscript):
        try:
            output = ast.unparse(value.body[0].value)
        except:
            output = ast.unparse(value.value) + "[" + ast.unparse(value.slice) + "]"
    else:
        raise Exception(f"Unsupported AST type: {type(value)}")
    return output
