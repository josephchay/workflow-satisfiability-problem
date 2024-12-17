import time
import itertools
from typing import Dict
import z3

from .base import BaseWSPSolver


class Z3UDPBWSPSolver(BaseWSPSolver):
    """User-Dependent Pseudo-Boolean encoding using Z3"""

    def solve(self) -> Dict:
        solver = z3.Solver()

        # Variables: x[s][u] means step s is assigned to user u
        x = [[z3.Bool(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        # Each step must be assigned exactly one user
        for s in range(self.instance.number_of_steps):
            solver.add(sum([z3.If(x[s][u], 1, 0) for u in range(self.instance.number_of_users)]) == 1)

        # Add constraints
        if self.active_constraints['authorizations']:
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u]:
                    for s in range(self.instance.number_of_steps):
                        if s not in self.instance.auth[u]:
                            solver.add(z3.Not(x[s][u]))

        if self.active_constraints['separation_of_duty']:
            for s1, s2 in self.instance.SOD:
                for u in range(self.instance.number_of_users):
                    solver.add(z3.Not(z3.And(x[s1][u], x[s2][u])))

        if self.active_constraints['binding_of_duty']:
            for s1, s2 in self.instance.BOD:
                for u in range(self.instance.number_of_users):
                    solver.add(x[s1][u] == x[s2][u])

        if self.active_constraints['at_most_k']:
            for k, steps in self.instance.at_most_k:
                # Create indicator variables for users involved
                z = [z3.Bool(f'z_{u}') for u in range(self.instance.number_of_users)]
                for u in range(self.instance.number_of_users):
                    # z[u] is true if user u is assigned to any step in steps
                    solver.add(z[u] == z3.Or([x[s][u] for s in steps]))
                solver.add(sum([z3.If(z[u], 1, 0) for u in range(self.instance.number_of_users)]) <= k)

        if self.active_constraints['one_team']:
            for steps, teams in self.instance.one_team:
                # Create team selection variables
                team_selected = [z3.Bool(f'team_{t}') for t in range(len(teams))]
                # Exactly one team must be selected
                solver.add(sum([z3.If(t, 1, 0) for t in team_selected]) == 1)
                
                # If team is selected, only its members can be assigned
                for team_idx, team in enumerate(teams):
                    for s in steps:
                        for u in range(self.instance.number_of_users):
                            if u not in team:
                                solver.add(z3.Implies(team_selected[team_idx], z3.Not(x[s][u])))

        # Count solutions
        solutions = []
        solution_count = 0
        
        start_time = time.time()

        # Keep finding solutions until unsat
        while solver.check() == z3.sat:
            solution_count += 1
            model = solver.model()

            # Extract solution
            solution = []
            for s in range(self.instance.number_of_steps):
                for u in range(self.instance.number_of_users):
                    if z3.is_true(model[x[s][u]]):
                        solution.append({'step': s + 1, 'user': u + 1})
            
            solutions.append(solution)

            # Block this solution
            block = []
            for s in range(self.instance.number_of_steps):
                for u in range(self.instance.number_of_users):
                    if z3.is_true(model[x[s][u]]):
                        block.append(x[s][u])
            solver.add(z3.Not(z3.And(block)))
            
            # Stop after finding two solutions if we only care about uniqueness
            if solution_count >= 2:
                break

        end_time = time.time()

        return {
            'sat': 'sat' if solutions else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': solutions[0] if solutions else [],
            'solution_count': solution_count,
            'is_unique': solution_count == 1
        }


class Z3PBPBWSPSolver(BaseWSPSolver):
    """Pattern-Based Pseudo-Boolean encoding using Z3"""

    def solve(self) -> Dict:
        solver = z3.Solver()

        # Variables: x[s][u] means step s is assigned to user u
        x = [[z3.Bool(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        # M[s1][s2] means steps s1 and s2 are assigned to same user
        M = [[z3.Bool(f'M_{s1}_{s2}') if s1 < s2 else None
              for s2 in range(self.instance.number_of_steps)]
             for s1 in range(self.instance.number_of_steps)]

        # Each step must be assigned exactly one user
        for s in range(self.instance.number_of_steps):
            solver.add(sum([z3.If(x[s][u], 1, 0) for u in range(self.instance.number_of_users)]) == 1)

        # Link M variables with x variables
        for s1, s2 in itertools.combinations(range(self.instance.number_of_steps), 2):
            for u in range(self.instance.number_of_users):
                solver.add(z3.Implies(M[s1][s2], x[s1][u] == x[s2][u]))
                solver.add(z3.Implies(z3.And(x[s1][u], x[s2][u]), M[s1][s2]))

        # Add constraints using pattern-based encoding
        if self.active_constraints['authorizations']:
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u]:
                    for s in range(self.instance.number_of_steps):
                        if s not in self.instance.auth[u]:
                            solver.add(z3.Not(x[s][u]))

        if self.active_constraints['separation_of_duty']:
            for s1, s2 in self.instance.SOD:
                if s1 < s2:
                    solver.add(z3.Not(M[s1][s2]))
                else:
                    solver.add(z3.Not(M[s2][s1]))

        if self.active_constraints['binding_of_duty']:
            for s1, s2 in self.instance.BOD:
                if s1 < s2:
                    solver.add(M[s1][s2])
                else:
                    solver.add(M[s2][s1])

        if self.active_constraints['at_most_k']:
            for k, steps in self.instance.at_most_k:
                # For each subset of k+1 steps, at least one pair must be same user
                for subset in itertools.combinations(steps, k + 1):
                    same_user_vars = []
                    for s1, s2 in itertools.combinations(subset, 2):
                        if s1 < s2:
                            same_user_vars.append(M[s1][s2])
                        else:
                            same_user_vars.append(M[s2][s1])
                    solver.add(z3.Or(same_user_vars))

        if self.active_constraints['one_team']:
            for steps, teams in self.instance.one_team:
                # Create team selection variables
                team_selected = [z3.Bool(f'team_{t}') for t in range(len(teams))]
                # Exactly one team must be selected
                solver.add(sum([z3.If(t, 1, 0) for t in team_selected]) == 1)
                
                # If team is selected, only its members can be assigned
                for team_idx, team in enumerate(teams):
                    for s in steps:
                        for u in range(self.instance.number_of_users):
                            if u not in team:
                                solver.add(z3.Implies(team_selected[team_idx], z3.Not(x[s][u])))

        # Find all solutions
        solutions = []
        solution_count = 0
        
        start_time = time.time()
        
        while len(solutions) < self.solution_limit and solver.check() == z3.sat:
            solution_count += 1
            model = solver.model()
            
            # Extract solution
            solution = []
            for s in range(self.instance.number_of_steps):
                for u in range(self.instance.number_of_users):
                    if z3.is_true(model.evaluate(x[s][u])):
                        solution.append({'step': s + 1, 'user': u + 1})
            
            solutions.append(solution)
            
            # Block this solution
            block = []
            for s in range(self.instance.number_of_steps):
                for u in range(self.instance.number_of_users):
                    if z3.is_true(model.evaluate(x[s][u])):
                        block.append(x[s][u])
            solver.add(z3.Not(z3.And(block)))
        
        end_time = time.time()

        return {
            'sat': 'sat' if solutions else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': solutions[0] if solutions else [],
            'solution_count': solution_count,
            'is_unique': solution_count == 1
        }
