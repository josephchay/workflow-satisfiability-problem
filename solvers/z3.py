import time
import itertools
from typing import Dict
from z3 import Optimize, PbEq, PbLe, Bool, Not, And, Or, Implies, is_true, sat

from .base import BaseWSPSolver


class Z3UDPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        solver = Optimize()

        x = [[Bool(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        for s in range(self.instance.number_of_steps):
            solver.add(PbEq([(x[s][u], 1) for u in range(self.instance.number_of_users)], 1))

        if self.active_constraints['authorizations']:
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u]:
                    for s in range(self.instance.number_of_steps):
                        if s not in self.instance.auth[u]:
                            solver.add(Not(x[s][u]))

        if self.active_constraints['separation_of_duty']:
            for s1, s2 in self.instance.SOD:
                for u in range(self.instance.number_of_users):
                    solver.add(Not(And(x[s1][u], x[s2][u])))

        if self.active_constraints['binding_of_duty']:
            for s1, s2 in self.instance.BOD:
                for u in range(self.instance.number_of_users):
                    solver.add(x[s1][u] == x[s2][u])

        if self.active_constraints['at_most_k']:
            for k, steps in self.instance.at_most_k:
                z = [Bool(f'z_{u}') for u in range(self.instance.number_of_users)]
                for u in range(self.instance.number_of_users):
                    solver.add(z[u] == Or([x[s][u] for s in steps]))
                solver.add(PbLe([(z[u], 1) for u in range(self.instance.number_of_users)], k))

        if self.active_constraints['one_team']:
            for steps, teams in self.instance.one_team:
                team_selected = [Bool(f'team_{t}') for t in range(len(teams))]
                solver.add(PbEq([(t, 1) for t in team_selected], 1))
                for team_idx, team in enumerate(teams):
                    for s in steps:
                        for u in range(self.instance.number_of_users):
                            if u not in team:
                                solver.add(Implies(team_selected[team_idx], Not(x[s][u])))

        solutions = []
        solution_count = 0
        start_time = time.time()

        while solver.check() == sat and solution_count < self.solution_limit:
            solution_count += 1
            model = solver.model()
            solution = []
            for s in range(self.instance.number_of_steps):
                for u in range(self.instance.number_of_users):
                    if is_true(model[x[s][u]]):
                        solution.append({'step': s + 1, 'user': u + 1})
            solutions.append(solution)
            block = Not(And([x[s][u] == model[x[s][u]] 
                                 for s in range(self.instance.number_of_steps) 
                                 for u in range(self.instance.number_of_users)]))
            solver.add(block)

        end_time = time.time()

        return {
            'sat': 'sat' if solutions else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': solutions[0] if solutions else [],
            'solution_count': solution_count,
            'is_unique': solution_count == 1
        }


class Z3PBPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        solver = Optimize()

        x = [[Bool(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        M = [[Bool(f'M_{s1}_{s2}') if s1 < s2 else None
              for s2 in range(self.instance.number_of_steps)]
             for s1 in range(self.instance.number_of_steps)]

        for s in range(self.instance.number_of_steps):
            solver.add(PbEq([(x[s][u], 1) for u in range(self.instance.number_of_users)], 1))

        for s1, s2 in itertools.combinations(range(self.instance.number_of_steps), 2):
            for u in range(self.instance.number_of_users):
                solver.add(And(x[s1][u] == x[s2][u]) == M[s1][s2])

        for s1, s2, s3 in itertools.combinations(range(self.instance.number_of_steps), 3):
            if s1 < s2 and s2 < s3:
                solver.add(Implies(And(M[s1][s2], M[s2][s3]), M[s1][s3]))

        if self.active_constraints['authorizations']:
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u]:
                    for s in range(self.instance.number_of_steps):
                        if s not in self.instance.auth[u]:
                            solver.add(Not(x[s][u]))

        if self.active_constraints['separation_of_duty']:
            for s1, s2 in self.instance.SOD:
                if s1 < s2:
                    solver.add(Not(M[s1][s2]))

        if self.active_constraints['binding_of_duty']:
            for s1, s2 in self.instance.BOD:
                if s1 < s2:
                    solver.add(M[s1][s2])

        if self.active_constraints['at_most_k']:
            for k, steps in self.instance.at_most_k:
                for subset in itertools.combinations(steps, k + 1):
                    solver.add(Or([M[min(s1,s2)][max(s1,s2)] 
                                   for s1, s2 in itertools.combinations(subset, 2)]))

        if self.active_constraints['one_team']:
            for steps, teams in self.instance.one_team:
                team_selected = [Bool(f'team_{t}') for t in range(len(teams))]
                solver.add(PbEq([(t, 1) for t in team_selected], 1))
                for team_idx, team in enumerate(teams):
                    for s1, s2 in itertools.combinations(steps, 2):
                        if s1 < s2:
                            solver.add(Implies(team_selected[team_idx], M[s1][s2]))

        solutions = []
        solution_count = 0
        start_time = time.time()

        while solver.check() == sat and solution_count < self.solution_limit:
            solution_count += 1
            model = solver.model()
            solution = []
            for s in range(self.instance.number_of_steps):
                for u in range(self.instance.number_of_users):
                    if is_true(model[x[s][u]]):
                        solution.append({'step': s + 1, 'user': u + 1})
            solutions.append(solution)
            # Block current solution
            block = Not(And([x[s][u] == model[x[s][u]] 
                                 for s in range(self.instance.number_of_steps) 
                                 for u in range(self.instance.number_of_users)]))
            solver.add(block)

        end_time = time.time()

        return {
            'sat': 'sat' if solutions else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': solutions[0] if solutions else [],
            'solution_count': solution_count,
            'is_unique': solution_count == 1
        }
