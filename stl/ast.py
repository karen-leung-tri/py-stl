# -*- coding: utf-8 -*-
from collections import deque, namedtuple
from functools import lru_cache

import funcy as fn
from lenses import lens, bind

import stl


def flatten_binary(phi, op, dropT, shortT):
    def f(x):
        return x.args if isinstance(x, op) else [x]

    args = [arg for arg in phi.args if arg is not dropT]

    if any(arg is shortT for arg in args):
        return shortT
    elif not args:
        return dropT
    elif len(args) == 1:
        return args[0]
    else:
        return op(tuple(fn.mapcat(f, phi.args)))


class AST(object):
    __slots__ = ()

    def __or__(self, other):
        return flatten_binary(Or((self, other)), Or, BOT, TOP)

    def __and__(self, other):
        return flatten_binary(And((self, other)), And, TOP, BOT)

    def __invert__(self):
        if isinstance(self, Neg):
            return self.arg
        return Neg(self)

    def __rshift__(self, t):
        if self in (BOT, TOP):
            return self

        phi = self
        for _ in range(t):
            phi = Next(phi)

        return phi

    def __call__(self, trace, time=0):
        return stl.pointwise_sat(self)(trace, time)

    @property
    def children(self):
        return tuple()

    def walk(self):
        """Walk of the AST."""
        pop = deque.pop
        children = deque([self])
        while len(children) > 0:
            node = pop(children)
            yield node
            children.extend(node.children)

    @property
    def params(self):
        def get_params(leaf):
            if isinstance(leaf, ModalOp):
                if isinstance(leaf.interval[0], Param):
                    yield leaf.interval[0]
                if isinstance(leaf.interval[1], Param):
                    yield leaf.interval[1]
            elif isinstance(leaf, LinEq):
                if isinstance(leaf.const, Param):
                    yield leaf.const

        return set(fn.mapcat(get_params, self.walk()))

    def set_params(self, val):
        phi = param_lens(self)
        return phi.modify(lambda x: float(val.get(x, val.get(str(x), x))))

    @property
    def lineqs(self):
        return set(lineq_lens.collect()(self))

    @property
    def atomic_predicates(self):
        return set(AP_lens.collect()(self))

    @property
    def var_names(self):
        symbols = set(bind(self.lineqs).Each().terms.Each().collect())
        symbols |= self.atomic_predicates
        return set(bind(symbols).Each().id.collect())

    def inline_context(self, context):
        phi, phi2 = self, None

        def update(ap):
            return context.get(ap, ap)

        while phi2 != phi:
            phi2, phi = phi, AP_lens.modify(update)(phi)

        return phi

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


class _Top(AST):
    __slots__ = ()

    def __repr__(self):
        return "⊤"

    def __invert__(self):
        return BOT


class _Bot(AST):
    __slots__ = ()

    def __repr__(self):
        return "⊥"

    def __invert__(self):
        return TOP


TOP = _Top()
BOT = _Bot()


class AtomicPred(namedtuple("AP", ["id"]), AST):
    __slots__ = ()

    def __repr__(self):
        return f"{self.id}"

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))

    @property
    def children(self):
        return tuple()


class LinEq(namedtuple("LinEquality", ["terms", "op", "const"]), AST):
    __slots__ = ()

    def __repr__(self):
        return " + ".join(map(str, self.terms)) + f" {self.op} {self.const}"

    @property
    def children(self):
        return tuple()

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


class Var(namedtuple("Var", ["coeff", "id"])):
    __slots__ = ()

    def __repr__(self):
        if self.coeff == -1:
            coeff_str = "-"
        elif self.coeff == +1:
            coeff_str = ""
        else:
            coeff_str = f"{self.coeff}"
        return f"{coeff_str}{self.id}"


class Interval(namedtuple('I', ['lower', 'upper'])):
    __slots__ = ()

    def __repr__(self):
        return f"[{self.lower},{self.upper}]"


class NaryOpSTL(namedtuple('NaryOp', ['args']), AST):
    __slots__ = ()

    OP = "?"

    def __repr__(self):
        return f" {self.OP} ".join(f"({x})" for x in self.args)

    @property
    def children(self):
        return tuple(self.args)


class Or(NaryOpSTL):
    __slots__ = ()

    OP = "∨"

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


class And(NaryOpSTL):
    __slots__ = ()

    OP = "∧"

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


class ModalOp(namedtuple('ModalOp', ['interval', 'arg']), AST):
    __slots__ = ()
    OP = '?'

    def __repr__(self):
        return f"{self.OP}{self.interval}({self.arg})"

    @property
    def children(self):
        return (self.arg,)


class F(ModalOp):
    __slots__ = ()
    OP = "◇"

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


class G(ModalOp):
    __slots__ = ()
    OP = "□"

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


class Until(namedtuple('ModalOp', ['arg1', 'arg2']), AST):
    __slots__ = ()

    def __repr__(self):
        return f"({self.arg1}) U ({self.arg2})"

    @property
    def children(self):
        return (self.arg1, self.arg2)

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


class Neg(namedtuple('Neg', ['arg']), AST):
    __slots__ = ()

    def __repr__(self):
        return f"¬({self.arg})"

    @property
    def children(self):
        return (self.arg,)

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


class Next(namedtuple('Next', ['arg']), AST):
    __slots__ = ()

    def __repr__(self):
        return f"◯({self.arg})"

    @property
    def children(self):
        return (self.arg,)

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


class Param(namedtuple('Param', ['name']), AST):
    __slots__ = ()

    def __repr__(self):
        return self.name

    def __hash__(self):
        # TODO: compute hash based on contents
        return hash(repr(self))


@lru_cache()
def param_lens(phi, *, getter=False):
    return bind(phi).Recur(Param)


def type_pred(*args):
    ast_types = set(args)
    return lambda x: type(x) in ast_types


lineq_lens = lens.Recur(LinEq)
AP_lens = lens.Recur(AtomicPred)
