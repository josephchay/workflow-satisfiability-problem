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

        # Assignment variables
        x = [[Bool(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        # Pattern variables - only create for s1 < s2 to avoid redundancy
        M = [[Bool(f'M_{s1}_{s2}') if s1 < s2 else None
              for s2 in range(self.instance.number_of_steps)]
             for s1 in range(self.instance.number_of_steps)]

        # Helper function to get M[s1][s2] regardless of order
        def get_M(s1: int, s2: int) -> Bool:
            if s1 < s2:
                return M[s1][s2]
            elif s1 > s2:
                return M[s2][s1]
            else:
                return True  # Same step is always assigned same user

        # Each step must be assigned exactly one user
        for s in range(self.instance.number_of_steps):
            solver.add(PbEq([(x[s][u], 1) for u in range(self.instance.number_of_users)], 1))

        # Link M variables with x variables
        for s1 in range(self.instance.number_of_steps):
            for s2 in range(s1 + 1, self.instance.number_of_steps):
                # Same user means M[s1][s2] must be True
                solver.add(Implies(
                    Or([And(x[s1][u], x[s2][u]) for u in range(self.instance.number_of_users)]),
                    M[s1][s2]
                ))
                # Different users means M[s1][s2] must be False
                solver.add(Implies(
                    M[s1][s2],
                    Or([And(x[s1][u], x[s2][u]) for u in range(self.instance.number_of_users)])
                ))
                
                # Alternative formulation for linking
                for u in range(self.instance.number_of_users):
                    # If steps assigned same user, M must be true
                    solver.add(Implies(And(x[s1][u], x[s2][u]), M[s1][s2]))
                    # If M is true and one step assigned to u, other must also be
                    solver.add(Implies(And(M[s1][s2], x[s1][u]), x[s2][u]))
                    solver.add(Implies(And(M[s1][s2], x[s2][u]), x[s1][u]))

        # Transitivity constraints for M variables
        for s1 in range(self.instance.number_of_steps):
            for s2 in range(s1 + 1, self.instance.number_of_steps):
                for s3 in range(s2 + 1, self.instance.number_of_steps):
                    # If s1,s2 same user and s2,s3 same user then s1,s3 must be same user
                    solver.add(Implies(
                        And(get_M(s1, s2), get_M(s2, s3)),
                        get_M(s1, s3)
                    ))
                    # If s1,s2 same user and s1,s3 different user then s2,s3 must be different user
                    solver.add(Implies(
                        And(get_M(s1, s2), Not(get_M(s1, s3))),
                        Not(get_M(s2, s3))
                    ))
                    # If s1,s2 different user and s2,s3 same user then s1,s3 must be different user
                    solver.add(Implies(
                        And(Not(get_M(s1, s2)), get_M(s2, s3)),
                        Not(get_M(s1, s3))
                    ))

        # Handle authorizations
        if self.active_constraints['authorizations']:
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u]:  # If user has authorizations
                    for s in range(self.instance.number_of_steps):
                        if s not in self.instance.auth[u]:
                            solver.add(Not(x[s][u]))

        # Handle separation of duty
        if self.active_constraints['separation_of_duty']:
            for s1, s2 in self.instance.SOD:
                solver.add(Not(get_M(s1, s2)))

        # Handle binding of duty
        if self.active_constraints['binding_of_duty']:
            for s1, s2 in self.instance.BOD:
                solver.add(get_M(s1, s2))

        # Handle at-most-k
        if self.active_constraints['at_most_k']:
            for k, steps in self.instance.at_most_k:
                for subset in itertools.combinations(steps, k + 1):
                    # At least one pair in subset must be same user
                    solver.add(Or([get_M(s1, s2) 
                               for s1, s2 in itertools.combinations(subset, 2)]))

        # Handle one-team
        if self.active_constraints['one_team']:
            for steps, teams in self.instance.one_team:
                # Create team selection variables
                team_selected = [Bool(f'team_{t}') for t in range(len(teams))]
                solver.add(PbEq([(t, 1) for t in team_selected], 1))
                
                for team_idx, team in enumerate(teams):
                    # If team selected, all pairs of steps must be assigned same user
                    for s1, s2 in itertools.combinations(steps, 2):
                        solver.add(Implies(team_selected[team_idx], get_M(s1, s2)))
                    
                    # If team selected, only users from team can be assigned
                    for step in steps:
                        for u in range(self.instance.number_of_users):
                            if u not in team:
                                solver.add(Implies(team_selected[team_idx], Not(x[step][u])))

        # Find solutions
        solutions = []
        solution_count = 0
        start_time = time.time()

        while solver.check() == sat and solution_count < self.solution_limit:
            solution_count += 1
            model = solver.model()
            
            # Extract solution
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
