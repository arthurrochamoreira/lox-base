import builtins
from dataclasses import dataclass
from operator import neg
from typing import TYPE_CHECKING
from types import BuiltinFunctionType, FunctionType

from .ctx import Ctx

if TYPE_CHECKING:
    from .ast import Stmt, Value

__all__ = [
    "add",
    "eq",
    "ge",
    "gt",
    "le",
    "lt",
    "mul",
    "ne",
    "neg",
    "not_",
    "print",
    "show",
    "sub",
    "truthy",
    "truediv",
    "LoxClass",
    "LoxInstance",
]


class LoxClass:
    """Representa uma classe Lox."""

    name: str

    def __init__(self, name: str):
        self.name = name

    def __call__(self, *args):
        return LoxInstance(self)

    def __str__(self) -> str:
        return self.name


class LoxInstance:
    """Instância de uma :class:`LoxClass`."""

    def __init__(self, cls: LoxClass):
        self.cls = cls

    def __str__(self) -> str:
        return f"{self.cls.name} instance"


@dataclass
class LoxFunction:
    """Representa uma função do Lox."""

    name: str
    params: list[str]
    body: list["Stmt"]
    ctx: Ctx

    def call(self, args: list["Value"]):
        env = dict(zip(self.params, args, strict=True))
        ctx = self.ctx.push(env)
        try:
            for stmt in self.body:
                stmt.eval(ctx)
        except LoxReturn as e:
            return e.value
        finally:
            ctx.pop()

    def __call__(self, *args):
        return self.call(list(args))
    
    def __str__(self) -> str:
        return f"<fn {self.name}>"
class LoxReturn(Exception):
    """
    Exceção para retornar de uma função Lox.
    """

    def __init__(self, value):
        self.value = value
        super().__init__()


class LoxError(Exception):
    """
    Exceção para erros de execução Lox.
    """


nan = float("nan")
inf = float("inf")


def print(value: "Value"):
    """
    Imprime um valor lox.
    """
    builtins.print(show(value))


def show(value: "Value") -> str:
    """
    Converte valor lox para string.
    """
    if isinstance(value, LoxClass):
        return str(value)
    if isinstance(value, LoxInstance):
        return str(value)
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        text = str(value)
        return text.removesuffix(".0")
    if isinstance(value, LoxFunction):
        return str(value)
    if isinstance(value, type):
        return value.__name__
    if isinstance(value, LoxInstance):
        return f"{type(value).__name__} instance"
    if isinstance(value, (FunctionType, BuiltinFunctionType)):
        return "<native fn>"
    return str(value)


def show_repr(value: "Value") -> str:
    """
    Mostra um valor lox, mas coloca aspas em strings.
    """
    if isinstance(value, str):
        return f'"{value}"'
    return show(value)


def truthy(value: "Value") -> bool:
    """
    Converte valor lox para booleano segundo a semântica do lox.
    """
    return not (value is False or value is None)


def not_(value: "Value") -> bool:
    return not truthy(value)


def _ensure_number(x: "Value") -> float:
    if not isinstance(x, float):
        raise LoxError("Operação requer números")
    return x


def add(a: "Value", b: "Value") -> "Value":
    if isinstance(a, float) and isinstance(b, float):
        return a + b
    if isinstance(a, str) and isinstance(b, str):
        return a + b
    raise LoxError("Operands must be two numbers or two strings")


def sub(a: "Value", b: "Value") -> float:
    return _ensure_number(a) - _ensure_number(b)


def mul(a: "Value", b: "Value") -> float:
    return _ensure_number(a) * _ensure_number(b)


def truediv(a: "Value", b: "Value") -> float:
    return _ensure_number(a) / _ensure_number(b)


def gt(a: "Value", b: "Value") -> bool:
    return _ensure_number(a) > _ensure_number(b)


def ge(a: "Value", b: "Value") -> bool:
    return _ensure_number(a) >= _ensure_number(b)


def lt(a: "Value", b: "Value") -> bool:
    return _ensure_number(a) < _ensure_number(b)


def le(a: "Value", b: "Value") -> bool:
    return _ensure_number(a) <= _ensure_number(b)


def eq(a: "Value", b: "Value") -> bool:
    if type(a) is not type(b):
        return False
    return a == b


def ne(a: "Value", b: "Value") -> bool:
    return not eq(a, b)
