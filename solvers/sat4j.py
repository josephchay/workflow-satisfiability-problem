from typing import Dict
import time
from itertools import combinations

from initializers import init_jvm
from typings import NotEquals, AtMost, Solution
from solvers import BaseWSPSolver


class BinaryWeightedClause:
    def __init__(self, left, relation, right, right_const):
        self.left = left
        self.right = right
        self.right_const = right_const
        self.relation = relation

    def write(self, f):
        def list_to_str(variables, sign):
            return ''.join(f'{sign}1 x{v}' for v in variables)

        f.write(f'{list_to_str(self.left, "+")}{list_to_str(self.right, "-")} {self.relation} {self.right_const};\n')


class SAT4JUDPBWSPSolver(BaseWSPSolver):
    """User-Dependent Pseudo-Boolean encoding using SAT4J"""
    def __init__(self, instance, active_constraints):
        super().__init__(instance, active_constraints)

        # Initialize JVM for SAT4J
        init_jvm()
    
    def solve(self) -> Dict:
        var_count = 0
        constraints = []

        def var():
            nonlocal var_count
            var_count += 1
            return var_count

        x = []
        for s in range(self.instance.k):
            row = []
            for u in range(self.instance.n):
                if self.instance.auths[u].collection[s]:
                    v = var()
                    row.append(v)
                else:
                    row.append(None)
            constraints.append(BinaryWeightedClause([v for v in row if v is not None], '=', [], 1))
            x.append(row)

        for c in self.instance.cons:
            if isinstance(c, NotEquals):
                for u in range(self.instance.n):
                    if x[c.s1][u] is not None and x[c.s2][u] is not None:
                        constraints.append(BinaryWeightedClause([x[c.s1][u], x[c.s2][u]], '<=', [], 1))

            elif isinstance(c, AtMost):
                z = [var() for u in range(self.instance.n)]
                for u in range(self.instance.n):
                    for s in c.scope:
                        if x[s][u] is not None:
                            constraints.append(BinaryWeightedClause([z[u]], '>=', [x[s][u]], 0))

                constraints.append(BinaryWeightedClause(z, '<=', [], c.limit))

            else:
                print('Unknown constraint ' + type(c))
                exit(1)

        import tempfile
        f = tempfile.NamedTemporaryFile(mode='w', prefix='pb-', delete=False)
        f.write(f'* #variable= {var_count} #constraint= {len(constraints)}\n')
        for c in constraints:
            c.write(f)
        f.close()

        start = time.time()
        import subprocess
        result = subprocess.run(f'java -jar sat4j-pb.jar Default {f.name}', capture_output=True)
        end = time.time()

        print(f.name)

        for l in result.stdout.decode('ascii').splitlines():
            if l.startswith("s UNSATISFIABLE"):
                return Solution(False, end - start)
            elif l.startswith("v"):
                import re
                ones = [int(match.group(1)) for match in re.finditer(r' x(\d+)', l)]

                def get_user(s):
                    for u in range(self.instance.n):
                        if x[s][u] is not None and x[s][u] in ones:
                            return u
                    raise Exception()

                return Solution([get_user(s) for s in range(self.instance.k)], end - start)


class SAT4JPBPBWSPSolver(BaseWSPSolver):
    """Pattern-Based Pseudo-Boolean encoding using SAT4J"""

    def __init__(self, instance, active_constraints):
        super().__init__(instance, active_constraints)

        # Initialize JVM for SAT4J
        init_jvm()
    
    def solve(self) -> Dict:
        var_count = 0
        constraints = []

        def var():
            nonlocal var_count
            var_count += 1
            return var_count

        x = []
        for s in range(self.instance.k):
            row = []
            for u in range(self.instance.n):
                if self.instance.auths[u].collection[s]:
                    v = var()
                    row.append(v)
                else:
                    row.append(None)
            constraints.append(BinaryWeightedClause([v for v in row if v is not None], '=', [], 1))
            x.append(row)

        M = [[None for s1 in range(self.instance.k)] for s2 in range(self.instance.k)]
        for s1 in range(self.instance.k):
            for s2 in range(s1 + 1, self.instance.k):
                M[s1][s2] = M[s2][s1] = var()

        for (s1, s2) in combinations(range(self.instance.k), 2):
            for s3 in range(self.instance.k):
                if s1 == s3 or s2 == s3:
                    continue

                constraints.append(BinaryWeightedClause([M[s1][s2]], '>=', [M[s1][s3], M[s2][s3]], -1))

        for (s1, s2) in combinations(range(self.instance.k), 2):
            for u in range(self.instance.n):
                if x[s1][u] is not None and x[s2][u] is not None:
                    constraints.append(BinaryWeightedClause([x[s1][u], M[s1][s2]], '<=', [x[s2][u]], 1))
                    constraints.append(BinaryWeightedClause([x[s2][u], M[s1][s2]], '<=', [x[s1][u]], 1))
                    constraints.append(BinaryWeightedClause([x[s1][u], x[s2][u]], '<=', [M[s1][s2]], 1))
                if x[s2][u] is None and x[s1][u] is not None:
                    constraints.append(BinaryWeightedClause([x[s1][u], M[s1][s2]], '<=', [], 1))
                if x[s1][u] is None and x[s2][u] is not None:
                    constraints.append(BinaryWeightedClause([x[s2][u], M[s1][s2]], '<=', [], 1))

        for c in self.instance.cons:
            if isinstance(c, NotEquals):
                for u in range(self.instance.n):
                    if x[c.s1][u] is not None and x[c.s2][u] is not None:
                        constraints.append(BinaryWeightedClause([M[c.s1][c.s2]], '=', [], 0))

            elif isinstance(c, AtMost):
                for T1 in combinations(c.scope, c.limit + 1):
                    constraints.append(BinaryWeightedClause([M[s1][s2] for (s1, s2) in combinations(T1, 2)], '>=', [], 1))

            else:
                print('Unknown constraint ' + type(c))
                exit(1)

        import tempfile
        f = tempfile.NamedTemporaryFile(mode='w', prefix='pb-', delete=False)
        f.write(f'* #variable= {var_count} #constraint= {len(constraints)}\n')
        for c in constraints:
            c.write(f)
        f.close()

        start = time.time()
        import subprocess
        result = subprocess.run(f'java -jar sat4j-pb.jar Default {f.name}', capture_output=True)
        end = time.time()

        print(f.name)

        for l in result.stdout.decode('ascii').splitlines():
            if l.startswith("s UNSATISFIABLE"):
                return Solution(False, end - start)
            elif l.startswith("v"):
                import re
                ones = [int(match.group(1)) for match in re.finditer(r' x(\d+)', l)]

                def get_user(s):
                    for u in range(self.instance.n):
                        if x[s][u] is not None and x[s][u] in ones:
                            return u
                    raise Exception()

                return Solution([get_user(s) for s in range(self.instance.k)], end - start)
