import time
from itertools import combinations
from typing import Dict
from z3 import Bool, Not, And, Or, Implies, Solver, sat, Sum, If, BoolRef, BoolVector, IntVector

from .base import BaseWSPSolver
from typings import NotEquals, AtMost, Solution


class Z3UDPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        solver = Solver()

        x = []
        for s in range(self.instance.k):
            row = []
            for u in range(self.instance.n):
                if self.instance.authorisations[u].authorisation_list[s]:
                    row.append(Bool(f'x{s}_{u}'))
                else:
                    row.append(None)

            x.append(row)

            solver.add(1 == Sum([If(b, 1, 0) for b in row if b is not None]))

        constraint_index = 0

        for c in self.instance.constraints:
            constraint_index = constraint_index + 1
            if isinstance(c, NotEquals):
                for u in range(self.instance.n):
                    if x[c.s1][u] is not None and x[c.s2][u] is not None:
                        solver.add(Not(And(x[c.s1][u], x[c.s2][u])))

            elif isinstance(c, AtMost):
                z = BoolVector(f'z{constraint_index}', self.instance.n)
                for u in range(self.instance.n):
                    for s in c.scope:
                        if x[s][u] is not None:
                            solver.add(Implies(x[s][u], z[u]))

                solver.add(Sum([If(b, 1, 0) for b in z]) <= c.limit)

            else:
                print('Unknown constraint ' + type(c))
                exit(1)

        start = time.time()
        status = solver.check()
        end = time.time()

        if status == sat:
            def get_user(s):
                for u in range(self.instance.n):
                    if x[s][u] is not None and solver.model().eval(x[s][u]):
                        return u
                raise Exception()

            return Solution([get_user(s) for s in range(self.instance.k)], end - start)
        else:
            return Solution(False, end - start)


class Z3PBPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        solver = Solver()

        x = []
        for s in range(self.instance.k):
            row = []
            for u in range(self.instance.n):
                if self.instance.authorisations[u].authorisation_list[s]:
                    row.append(Bool(f'x{s}_{u}'))
                else:
                    row.append(None)

            x.append(row)

            solver.add(1 == Sum([If(b, 1, 0) for b in row if b is not None]))

        M = [[BoolRef(None) for _ in range(self.instance.k)] for _ in range(self.instance.k)]
        for s1 in range(self.instance.k):
            M[s1][s1] = None
            for s2 in range(s1 + 1, self.instance.k):
                M[s1][s2] = M[s2][s1] = Bool(f'M{s1}_{s2}')

        for (s1, s2) in combinations(range(self.instance.k), 2):
            for s3 in range(self.instance.k):
                if s1 == s3 or s2 == s3:
                    continue

                solver.add(Implies(And(M[s1][s3], M[s2][s3]), M[s1][s2]))
                solver.add(Implies(M[s1][s3] != M[s2][s3], Not(M[s1][s2])))

        for (s1, s2) in combinations(range(self.instance.k), 2):
            for u in range(self.instance.n):
                if x[s1][u] is not None and x[s2][u] is not None:
                    solver.add(M[s1][s2] == (x[s1][u] == x[s2][u]))
                if x[s2][u] is None and x[s1][u] is not None:
                    solver.add(Implies(M[s1][s2], Not(x[s1][u])))
                if x[s1][u] is None and x[s2][u] is not None:
                    solver.add(Implies(M[s1][s2], Not(x[s2][u])))

        constraint_index = 0
        for c in self.instance.constraints:
            constraint_index = constraint_index + 1
            if isinstance(c, NotEquals):
                solver.add(Not(M[c.s1][c.s2]))

            elif isinstance(c, AtMost):
                for T1 in combinations(c.scope, c.limit + 1):
                    solver.add(Or([M[s1][s2] for (s1, s2) in combinations(T1, 2)]))

            else:
                print('Unknown constraint ' + type(c))
                exit(1)

        start = time.time()
        status = solver.check()
        end = time.time()

        if status == sat:
            def get_user(s):
                for u in range(self.instance.n):
                    if solver.model().eval(x[s][u]):
                        return u
                raise Exception()

            return Solution([get_user(s) for s in range(self.instance.k)], end - start)
        else:
            return Solution(False, end - start)


class Z3CSWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        solver = Solver()

        y = IntVector('y', self.instance.k)
        for s in range(self.instance.k):
            solver.add(y[s] >= 0)
            solver.add(y[s] < self.instance.n)
            for u in range(self.instance.n):
                if not self.instance.authorisations[u].authorisation_list[s]:
                    solver.add(y[s] != u)

        constraint_index = 0
        for c in self.instance.constraints:
            constraint_index = constraint_index + 1
            if isinstance(c, NotEquals):
                solver.add(y[c.s1] != y[c.s2])

            elif isinstance(c, AtMost):
                import itertools
                for T1 in itertools.combinations(c.scope, c.limit + 1):
                    solver.add(Or([y[s1] == y[s2] for (s1, s2) in itertools.combinations(T1, 2)]))

            else:
                print('Unknown constraint ' + type(c))
                exit(1)

        start = time.time()
        status = solver.check()
        end = time.time()

        if status == sat:
            return Solution([solver.model().eval(y[s]).as_long() for s in range(self.instance.k)], end - start)
        else:
            return Solution(False, end - start)
