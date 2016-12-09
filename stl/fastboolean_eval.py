from functools import singledispatch
from bitarray import bitarray

import stl.ast
from stl.boolean_eval import eval_terms, op_lookup

@singledispatch
def pointwise_satf(stl):
    raise NotImplementedError


@pointwise_satf.register(stl.Or)
def _(stl):
    def sat_comp(x,t):
        sat = bitarray(len(t))
        for arg in stl.args:
            sat = pointwise_satf(arg)(x, t) | sat
        return sat
    return sat_comp


@pointwise_satf.register(stl.And)
def _(stl):
    def sat_comp(x,t):
        sat = ~bitarray(len(t))
        for arg in stl.args:
            sat = ~(~pointwise_satf(arg)(x, t) | ~sat)            
        return sat
    return sat_comp


@pointwise_satf.register(stl.F)
def _(stl):
    lo, hi = stl.interval
    def sat_comp(x,t):
        sat = bitarray()
        for tau in t:
            tau_t = [min(tau + t2, x.index[-1]) for t2 in x[lo:hi].index]
            sat.append((pointwise_satf(stl.arg)(x, tau_t)).count() > 0)
        return sat
    return sat_comp


@pointwise_satf.register(stl.G)
def _(stl):
    lo, hi = stl.interval
    def sat_comp(x,t):
        sat = bitarray()
        for tau in t:
            tau_t = [min(tau + t2, x.index[-1]) for t2 in x[lo:hi].index]
            sat.append((~(pointwise_satf(stl.arg)(x, tau_t))).count() == 0)
        return sat
    return sat_comp


@pointwise_satf.register(stl.Neg)
def _(stl):
    return lambda x,t: ~pointwise_satf(arg)(x, t) 


@pointwise_satf.register(stl.AtomicPred)
def _(stl):
    def sat_comp(x, t):
        sat = bitarray()
        [sat.append(x[stl.id][tau]) for tau in t]
        return sat
    return sat_comp


@pointwise_satf.register(stl.LinEq)
def _(stl):
    op = op_lookup[stl.op]
    def sat_comp(x, t):
        sat = bitarray()
        [sat.append(op(eval_terms(stl, x, tau), stl.const)) for tau in t]
        return sat
    return sat_comp 