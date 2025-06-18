"""
Define a gramática da Linguagem e funções para realizar a análise sintática,
análise léxica, etc.
"""

from pathlib import Path
import operator
from typing import Callable, Iterator

from lark import Lark, Transformer, Token, v_args

from .ast import BinOp, Var, Literal, Expr, Stmt

DIR = Path(__file__).parent
GRAMMAR_PATH = DIR / "grammar.lark"
grammar = GRAMMAR_PATH.read_text()


def op_handler(op: Callable):
    """
    Fábrica de métodos que lidam com operações binárias na árvore sintática.

    Recebe a função que implementa a operação em tempo de execução.
    """

    def method(self, left, right):
        return BinOp(left, right, op)

    return method


@v_args(inline=True)
class LoxTransformer(Transformer):
    # Operações matemáticas básicas
    mul = op_handler(operator.mul)
    div = op_handler(operator.truediv)
    sub = op_handler(operator.sub)
    add = op_handler(operator.add)

    # Comparações
    gt = op_handler(operator.gt)
    lt = op_handler(operator.lt)
    ge = op_handler(operator.ge)
    le = op_handler(operator.le)
    eq = op_handler(operator.eq)
    ne = op_handler(operator.ne)

    def VAR(self, token):
        name = str(token)
        return Var(name)

    def NUMBER(self, token):
        num = float(token)
        return Literal(num)


ast_parser = Lark(
    grammar,
    transformer=LoxTransformer(),
    parser="lalr",
    start=["start", "expr"],
)
cst_parser = Lark(
    grammar,
    parser="lalr",
    start=["start", "expr"],
)


def parse(src: str, expr: bool = False) -> Expr | Stmt:
    """
    Função que recebe um código fonte e retorna a árvore sintática.

    A função usa o Lark para fazer a análise léxica e sintática do código
    fonte. O resultado é uma árvore sintática que representa a estrutura
    do código usando os nós definidos na classe `Node`.

    Args:
        src (str):
            Código fonte a ser analisado.
        expr (bool):
            Se True, analisa o código como se fosse apenas uma expressão.
    """
    start = "expr" if expr else "start"
    return ast_parser.parse(src, start=start)


def parse_cst(src: str, expr: bool = False) -> Expr | Stmt:
    """
    Similar a função `parse`, mas retorna a árvore sintática produzida pelo
    Lark.

    Não é exatamente a árvore concreta, pois o Lark produz algumas
    simplificações, mas é próxima o suficiente.

    Args:
        src (str):
            Código fonte a ser analisado.
        expr (bool):
            Se True, analisa o código como se fosse apenas uma expressão.
    """
    start = "expr" if expr else "start"
    return cst_parser.parse(src, start=start)


def lex(src: str) -> Iterator[Token]:
    """
    Retorna um iterador sobre os tokens do código fonte.
    """
    return ast_parser.lex(src)
