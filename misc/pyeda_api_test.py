#!/usr/bin/env python3

from pyeda.inter import expr, expr2bdd, bddvar

# type
#   expr.Variable
#   expr.OrOp
#
#   bdd.BDDVariable
#   bdd.BinaryDecisionDiagram
#
#   expr()     => expr.*
#   expr2bdd() => from expr to bdd
#   bddvar()   => bdd.BDDVariable
#
#   both expr and bdd can use ~|&^ operator

# f = expr('a & b | b & c | c & a')
f = expr('a1_1 & a2_1 | a2_1 & a2_2 | a2_2 & a1_1')
g = f | expr('d')
# type(f) => expr
# type(g) => expr

f2 = expr2bdd(f)
# type(f2) = bdd
print(f2.satisfy_one())
print(f2.satisfy_all()) # generator
print(list(f2.satisfy_all()))
print(f2.satisfy_count())
print(f2.to_dot())

