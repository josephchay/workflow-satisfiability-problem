from ortools.sat.python import cp_model
from typing import Dict
import time
from itertools import combinations

from solvers import BaseWSPSolver
from typings import NotEquals, AtMost, Solution


class ORToolsCSWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        model = cp_model.CpModel()

        y = []
        for s in range(self.instance.k):
            users = [u for u in range(self.instance.n) if self.instance.authorisations[u].authorisation_list[s]]
            v = model.NewIntVarFromDomain(cp_model.Domain.FromValues(users), f'y{s}')
            y.append(v)

        for c in self.instance.constraints:
            if isinstance(c, NotEquals):
                model.Add(y[c.s1] != y[c.s2])

            elif isinstance(c, AtMost):
                import itertools
                for T1 in itertools.combinations(c.scope, c.limit + 1):
                    a_list = []
                    for (s1, s2) in itertools.combinations(T1, 2):
                        a = model.NewBoolVar('a')
                        model.Add(y[s1] == y[s2]).OnlyEnforceIf(a)
                        a_list.append(a)
                    model.AddBoolOr(a_list)

            else:
                print('Unknown constraint ' + type(c))
                exit(1)

        solver = cp_model.CpSolver()

        start = time.time()
        status = solver.Solve(model)
        end = time.time()

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return Solution([solver.Value(y[s]) for s in range(self.instance.k)], end - start)
        else:
            return Solution(False, end - start)


class ORToolsPBPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        model = cp_model.CpModel()

        x = []
        for s in range(self.instance.k):
            row = []
            for u in range(self.instance.n):
                if self.instance.authorisations[u].authorisation_list[s]:
                    v = model.NewBoolVar('')
                    row.append(v)
                else:
                    row.append(None)
            model.Add(sum([v for v in row if v is not None]) == 1)
            x.append(row)

        M = [[None for s1 in range(self.instance.k)] for s2 in range(self.instance.k)]
        for s1 in range(self.instance.k):
            for s2 in range(s1 + 1, self.instance.k):
                M[s1][s2] = M[s2][s1] = model.NewBoolVar('')

        for (s1, s2) in combinations(range(self.instance.k), 2):
            for s3 in range(self.instance.k):
                if s1 == s3 or s2 == s3:
                    continue

                model.Add(M[s1][s2] == 1).OnlyEnforceIf([M[s1][s3], M[s2][s3]])
                model.Add(M[s1][s2] == 0).OnlyEnforceIf([M[s2][s3].Not(), M[s1][s3]])
                model.Add(M[s1][s2] == 0).OnlyEnforceIf([M[s2][s3], M[s1][s3].Not()])

        for (s1, s2) in combinations(range(self.instance.k), 2):
            for u in range(self.instance.n):
                if x[s1][u] is not None and x[s2][u] is not None:
                    model.Add(x[s1][u] == x[s2][u]).OnlyEnforceIf(M[s1][s2])
                    model.AddBoolOr([x[s1][u].Not(), x[s2][u].Not()]).OnlyEnforceIf(M[s1][s2].Not())
                if x[s2][u] is None and x[s1][u] is not None:
                    model.AddImplication(M[s1][s2], x[s1][u].Not())
                if x[s1][u] is None and x[s2][u] is not None:
                    model.AddImplication(M[s1][s2], x[s2][u].Not())

        for c in self.instance.constraints:
            if isinstance(c, NotEquals):
                model.Add(M[c.s1][c.s2] == 0)
                # model.Add(M[c.s1][c.s2] == 0)
            elif isinstance(c, AtMost):
                for T1 in combinations(c.scope, c.limit + 1):
                    model.AddBoolOr([M[s1][s2] for (s1, s2) in combinations(T1, 2)])

            else:
                print('Unknown constraint ' + type(c))
                exit(1)

        solver = cp_model.CpSolver()
        solver.parameters

        start = time.time()
        status = solver.Solve(model)
        end = time.time()

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            def get_user(s):
                result = [u for u in range(self.instance.n) if x[s][u] is not None and solver.Value(x[s][u]) > 0.5]
                assert len(result) == 1
                return result[0]

            return Solution([get_user(s) for s in range(self.instance.k)], end - start)
        else:
            return Solution(False, end - start)


class ORToolsUDPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        model = cp_model.CpModel()

        x = []
        for s in range(self.instance.k):
            row = []
            for u in range(self.instance.n):
                if self.instance.authorisations[u].authorisation_list[s]:
                    v = model.NewBoolVar('')
                    row.append(v)
                else:
                    row.append(None)
            model.Add(sum([v for v in row if v is not None]) == 1)
            x.append(row)

        for c in self.instance.constraints:
            if isinstance(c, NotEquals):
                for u in range(self.instance.n):
                    if x[c.s1][u] is not None and x[c.s2][u] is not None:
                        model.AddBoolOr([x[c.s1][u].Not(), x[c.s2][u].Not()])

            elif isinstance(c, AtMost):
                z = [model.NewBoolVar('') for u in range(self.instance.n)]
                for u in range(self.instance.n):
                    for s in c.scope:
                        if x[s][u] is not None:
                            model.AddImplication(x[s][u], z[u])

                model.Add(sum(z) <= c.limit)

            else:
                print('Unknown constraint ' + type(c))
                exit(1)

        solver = cp_model.CpSolver()
        solver.parameters

        start = time.time()
        status = solver.Solve(model)
        end = time.time()

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            def get_user(s):
                for u in range(self.instance.n):
                    if x[s][u] is not None and solver.Value(x[s][u]) > 0.5:
                        return u
                raise Exception()

            return Solution([get_user(s) for s in range(self.instance.k)], end - start)
        else:
            return Solution(False, end - start)
