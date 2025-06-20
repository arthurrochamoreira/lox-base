from abc import ABC
from dataclasses import dataclass
from typing import Callable
from .ctx import Ctx
from .runtime import LoxFunction, LoxReturn, LoxClass, LoxError, truthy, show, LoxInstance
from .node import Node, Cursor
from .errors import SemanticError

KEYWORDS = {
    "and",
    "class",
    "else",
    "false",
    "for",
    "fun",
    "if",
    "nil",
    "or",
    "print",
    "return",
    "super",
    "this",
    "true",
    "var",
    "while",
}

""" Tipos de valores que podem aparecer durante a execução do programa"""
Value = bool | str | float | None

class Expr(Node, ABC):
    """
    Classe base para expressões.

    Expressões são nós que podem ser avaliados para produzir um valor.
    Também podem ser atribuídos a variáveis, passados como argumentos para
    funções, etc.
    """


class Stmt(Node, ABC):
    """
    Classe base para comandos.

    Comandos são associdos a construtos sintáticos que alteram o fluxo de
    execução do código ou declaram elementos como classes, funções, etc.
    """


@dataclass
class Program(Node):
    """
    Representa um programa.

    Um programa é uma lista de comandos.
    """

    stmts: list[Stmt]

    def eval(self, ctx: Ctx):
        for stmt in self.stmts:
            stmt.eval(ctx)


#
# EXPRESSÕES
#
@dataclass
class BinOp(Expr):
    """
    Uma operação infixa com dois operandos.

    Ex.: x + y, 2 * x, 3.14 > 3 and 3.14 < 4
    """

    left: Expr
    right: Expr
    op: Callable[[Value, Value], Value]

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        right_value = self.right.eval(ctx)
        return self.op(left_value, right_value)


@dataclass
class Var(Expr):
    """
    Uma variável no código

    Ex.: x, y, z
    """

    name: str

    def eval(self, ctx: Ctx):
        try:
            return ctx[self.name]
        except KeyError:
            raise NameError(f"variável {self.name} não existe!")

    def validate_self(self, cursor: Cursor):
        if self.name in KEYWORDS:
            raise SemanticError("nome inválido", token=self.name)

@dataclass
class Literal(Expr):
    """
    Representa valores literais no código, ex.: strings, booleanos,
    números, etc.

    Ex.: "Hello, world!", 42, 3.14, true, nil
    """

    value: Value

    def eval(self, ctx: Ctx):
        return self.value


@dataclass
class And(Expr):
    """Operador lógico 'and' com curto-circuito."""

    left: Expr
    right: Expr

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        if not truthy(left_value):
            return left_value
        return self.right.eval(ctx)

@dataclass
class Or(Expr):
    """Operador lógico 'or' com curto-circuito."""

    left: Expr
    right: Expr

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        if truthy(left_value):
            return left_value
        return self.right.eval(ctx)

@dataclass
class Call(Expr):
    """
    Uma chamada de função.

    Ex.: fat(42)
    """

    callee: Expr
    params: list[Expr]

    def eval(self, ctx: Ctx):
        func = self.callee.eval(ctx)
        args = [p.eval(ctx) for p in self.params]
        if callable(func):
            return func(*args)
        raise TypeError(f"{func!r} não é chamável")


@dataclass
class This(Expr):
    """
    Acesso ao `this`.

    Ex.: this
    """

    name: str = "this"

    def eval(self, ctx: Ctx):
        try:
            return ctx[self.name]
        except KeyError:
            raise NameError("variável this não existe!")

    def validate_self(self, cursor: Cursor):
        if not cursor.is_scoped_to(Class):
            raise SemanticError("uso inválido de 'this'", token="this")

@dataclass
class Super(Expr):
    """
    Acesso a method ou atributo da superclasse.

    Ex.: super.x
    """

    name: str

    def eval(self, ctx: Ctx):
        method_name = self.name
        superclass = ctx["super"]
        this = ctx["this"]
        method = superclass.get_method(method_name)
        return method.bind(this)

    def validate_self(self, cursor: Cursor):
        if not cursor.is_scoped_to(Class):
            raise SemanticError("uso inválido de 'super'", token="super")

        cls = cursor.class_scope().node
        if cls.base is None:
            raise SemanticError("classe sem superclasse", token="super")
        
@dataclass
class Assign(Expr):
    """
    Atribuição de variável.

    Ex.: x = 42
    """
    name: str
    value: Expr

    def eval(self, ctx: Ctx):
        result = self.value.eval(ctx)
        ctx.assign(self.name, result)
        return result

@dataclass
class Getattr(Expr):
    """
    Acesso a atributo de um objeto.

    Ex.: x.y
    """

    obj: Expr
    attr: str

    def eval(self, ctx: Ctx):
        value = self.obj.eval(ctx)
        if (
            value is None
            or type(value) in (bool, float, str)
            or isinstance(value, (LoxClass, LoxFunction))
        ):
            raise LoxError("Somente instâncias têm propriedades.")
        return getattr(value, self.attr)

@dataclass
class Setattr(Expr):
    obj: Expr
    attr: str
    value: Expr

    def eval(self, ctx: Ctx):
        obj_value = self.obj.eval(ctx)
        if (
            obj_value is None
            or type(obj_value) in (bool, float, str)
            or isinstance(obj_value, (LoxClass, LoxFunction))
        ):
            raise LoxError("Somente instâncias tem campos")
        result = self.value.eval(ctx)
        setattr(obj_value, self.attr, result)
        return result

@dataclass
class Print(Stmt):
    """
    Representa uma instrução de impressão.

    Ex.: print "Hello, world!";
    """
    expr: Expr
    
    def eval(self, ctx: Ctx):
        value = self.expr.eval(ctx)
        print(show(value))

@dataclass
class Return(Stmt):
    value: Expr | None = None

    def eval(self, ctx: Ctx):
        result = None if self.value is None else self.value.eval(ctx)
        raise LoxReturn(result)

    def validate_self(self, cursor: Cursor):
        if not cursor.is_scoped_to(Function):
            raise SemanticError("return fora de função", token="return")
        func_cursor = cursor.function_scope()
        if (
            self.value is not None
            and func_cursor.node.name == "init"
            and isinstance(func_cursor.parent().node, Class)
        ):
            raise SemanticError(
                "não pode retornar valor de inicializador",
                token="return",
            )

@dataclass
class VarDef(Stmt):
    name: str
    value: Expr

    def eval(self, ctx: Ctx):
        ctx.var_def(self.name, self.value.eval(ctx))

    def validate_self(self, cursor: Cursor):
        if self.name in KEYWORDS:
            raise SemanticError("nome inválido", token=self.name)
        if isinstance(cursor.parent().node, Program):
            return
        for desc in self.value.cursor().descendants():
            node = desc.node
            if isinstance(node, Var) and node.name == self.name:
                raise SemanticError(
                    "variável usada em seu próprio inicializador",
                    token=self.name,
                )

@dataclass
class If(Stmt):
    cond: Expr
    then_branch: Stmt
    else_branch: Stmt | None = None

    def eval(self, ctx: Ctx):
        if truthy(self.cond.eval(ctx)):
            self.then_branch.eval(ctx)
        elif self.else_branch is not None:
            self.else_branch.eval(ctx)
@dataclass
class While(Stmt):
    cond: Expr
    body: Stmt

    def eval(self, ctx: Ctx):
        while truthy(self.cond.eval(ctx)):
            self.body.eval(ctx)

@dataclass
class Block(Node):
    stmts: list[Stmt]

    def eval(self, ctx: Ctx):
        ctx = ctx.push({})
        try:
            for stmt in self.stmts:
                stmt.eval(ctx)
        finally:
            ctx.pop()

    def validate_self(self, cursor: Cursor):
        names: list[str] = [s.name for s in self.stmts if isinstance(s, VarDef)]
        seen: set[str] = set()
        for name in names:
            if name in seen:
                raise SemanticError("variável duplicada", token=name)
            seen.add(name)

@dataclass
class Function(Stmt):
    name: str
    params: list[str]
    body: Block

    def eval(self, ctx: Ctx):
        func = LoxFunction(
            name=self.name,
            params=self.params,
            body=self.body.stmts,
            ctx=ctx,
        )
        ctx.var_def(self.name, func)
        return func

    def validate_self(self, cursor: Cursor):
        for p in self.params:
            if p in KEYWORDS:
                raise SemanticError("nome inválido", token=p)

        if len(set(self.params)) != len(self.params):
            seen: set[str] = set()
            for p in self.params:
                if p in seen:
                    raise SemanticError("parâmetro duplicado", token=p)
                seen.add(p)

        body_vars = [s.name for s in self.body.stmts if isinstance(s, VarDef)]
        for name in body_vars:
            if name in self.params:
                raise SemanticError("nome inválido", token=name)
            
@dataclass
class Class(Stmt):
    """
    Representa uma classe.

    Ex.: class B < A { ... }
    """
    name: str
    methods: list["Function"]
    base: str | None = None

    def validate_self(self, cursor: Cursor):
        if self.base == self.name:
            raise SemanticError(
                "classe nao pode herdar de si mesma",
                token=self.name,
            )

    def eval(self, ctx: Ctx):
        superclass = None
        if self.base is not None:
            try:
                value = ctx[self.base]
            except KeyError as e:
                raise NameError(f"classe {self.base} não existe") from e
            if not isinstance(value, LoxClass):
                raise LoxError("Superclasse inválida")
            superclass = value

        if superclass is None:
            method_ctx = ctx
        else:
            method_ctx = ctx.push({"super": superclass})

        methods: dict[str, LoxFunction] = {}
        for method in self.methods:
            method_impl = LoxFunction(
                name=method.name,
                params=method.params,
                body=method.body.stmts,
                ctx=method_ctx,
            )
            methods[method.name] = method_impl

        lox_class = LoxClass(self.name, methods, superclass)
        ctx.var_def(self.name, lox_class)
        return lox_class

@dataclass
class UnaryOp(Expr):
    op: Callable[[Value], Value]
    operand: Expr

    def eval(self, ctx: Ctx):
        return self.op(self.operand.eval(ctx))
