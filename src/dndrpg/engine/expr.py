# Wrapper you can extend with custom funcs like ability_mod()
from py_expression_eval import Parser

_parser = Parser()
def eval_expr(expr: str, env: dict) -> int | float:
    return _parser.parse(expr).evaluate(env)
