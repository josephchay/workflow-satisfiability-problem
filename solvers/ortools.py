from ortools.sat.python import cp_model
from typing import Dict
import time
import itertools

from utils import SolutionCollector
from solvers import BaseWSPSolver


class ORToolsCSWSPSolver(BaseWSPSolver):
    """Constraint Satisfaction encoding using OR-Tools"""

    def solve(self) -> Dict:
        model = cp_model.CpModel()

        # Variables: y[s] = u means step s is assigned to user u
        y = []
        for s in range(self.instance.number_of_steps):
            users = [u for u in range(self.instance.number_of_users)]
            v = model.NewIntVarFromDomain(cp_model.Domain.FromValues(users), f'y{s}')
            y.append(v)

        # Add constraints
        if self.active_constraints['authorizations']:
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u]:
                    for s in range(self.instance.number_of_steps):
                        if s not in self.instance.auth[u]:
                            model.Add(y[s] != u)

        if self.active_constraints['separation_of_duty']:
            for s1, s2 in self.instance.SOD:
                model.Add(y[s1] != y[s2])

        if self.active_constraints['binding_of_duty']:
            for s1, s2 in self.instance.BOD:
                model.Add(y[s1] == y[s2])

        if self.active_constraints['at_most_k']:
            for k, steps in self.instance.at_most_k:
                # Create helper variables for each user
                user_used = []
                for u in range(self.instance.number_of_users):
                    used = model.NewBoolVar(f'used_{u}')
                    # User is used if they're assigned to any step
                    used_constraints = []
                    for s in steps:
                        used_constraints.append(y[s] == u)
                    model.AddBoolOr(used_constraints).OnlyEnforceIf(used)
                    model.AddBoolAnd([c.Not() for c in used_constraints]).OnlyEnforceIf(used.Not())
                    user_used.append(used)
                model.Add(sum(user_used) <= k)

        if self.active_constraints['one_team']:
            for steps, teams in self.instance.one_team:
                # Create team selection variables
                team_selected = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
                model.AddExactlyOne(team_selected)
                
                # Enforce team assignments
                for team_idx, team in enumerate(teams):
                    for s in steps:
                        for u in range(self.instance.number_of_users):
                            if u not in team:
                                model.Add(y[s] != u).OnlyEnforceIf(team_selected[team_idx])

        # Solve
        solver = cp_model.CpSolver()
        solution_collector = SolutionCollector("CS", y)
        
        start_time = time.time()
        status = solver.SearchForAllSolutions(model, solution_collector)
        end_time = time.time()

        return {
            'sat': 'sat' if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': solution_collector.get_solutions(),
            'solution_count': solution_collector.solution_count(),
            'is_unique': solution_collector.solution_count() == 1
        }


class ORToolsPBPBWSPSolver(BaseWSPSolver):
    """Pattern-Based Pseudo-Boolean encoding using OR-Tools"""
    
    def solve(self) -> Dict:
        model = cp_model.CpModel()

        # Variables: x[s][u] means step s is assigned to user u
        x = [[model.NewBoolVar(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        # M[s1][s2] means steps s1 and s2 are assigned to same user
        M = [[model.NewBoolVar(f'M_{s1}_{s2}') if s1 != s2 else None
              for s2 in range(self.instance.number_of_steps)]
             for s1 in range(self.instance.number_of_steps)]

        # Each step must be assigned exactly one user
        for s in range(self.instance.number_of_steps):
            model.AddExactlyOne(x[s])

        # Link M variables with x variables
        for s1, s2 in itertools.combinations(range(self.instance.number_of_steps), 2):
            for u in range(self.instance.number_of_users):
                # If M[s1][s2] = 1, then x[s1][u] = x[s2][u]
                model.Add(x[s1][u] == x[s2][u]).OnlyEnforceIf(M[s1][s2])
                model.Add(x[s1][u] != x[s2][u]).OnlyEnforceIf(M[s1][s2].Not())

        # Add transitivity constraints for M variables
        for s1, s2 in itertools.combinations(range(self.instance.number_of_steps), 2):
            for s3 in range(s2 + 1, self.instance.number_of_steps):
                model.AddBoolOr([M[s1][s2].Not(), M[s2][s3].Not(), M[s1][s3]])
                model.AddBoolOr([M[s1][s2], M[s2][s3], M[s1][s3].Not()])

        # Add constraints
        if self.active_constraints['authorizations']:
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u]:
                    for s in range(self.instance.number_of_steps):
                        if s not in self.instance.auth[u]:
                            model.Add(x[s][u] == 0)

        if self.active_constraints['separation_of_duty']:
            for s1, s2 in self.instance.SOD:
                model.Add(M[s1][s2] == 0)

        if self.active_constraints['binding_of_duty']:
            for s1, s2 in self.instance.BOD:
                model.Add(M[s1][s2] == 1)

        if self.active_constraints['at_most_k']:
            for k, steps in self.instance.at_most_k:
                for subset in itertools.combinations(steps, k + 1):
                    same_user_vars = []
                    for s1, s2 in itertools.combinations(subset, 2):
                        same_user_vars.append(M[min(s1,s2)][max(s1,s2)])
                    model.AddBoolOr(same_user_vars)

        if self.active_constraints['one_team']:
            for steps, teams in self.instance.one_team:
                # Create team selection variables
                team_selected = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
                model.AddExactlyOne(team_selected)
                
                # If team is selected, only its members can be assigned
                for team_idx, team in enumerate(teams):
                    for s in steps:
                        for u in range(self.instance.number_of_users):
                            if u not in team:
                                model.Add(x[s][u] == 0).OnlyEnforceIf(team_selected[team_idx])

        # Solve
        solver = cp_model.CpSolver()
        solution_collector = SolutionCollector("PBPB", x)
        
        start_time = time.time()
        status = solver.SearchForAllSolutions(model, solution_collector)
        end_time = time.time()

        return {
            'sat': 'sat' if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': solution_collector.get_solutions(),
            'solution_count': solution_collector.solution_count(),
            'is_unique': solution_collector.solution_count() == 1
        }


class ORToolsUDPBWSPSolver(BaseWSPSolver):
    """User-Dependent Pseudo-Boolean encoding using OR-Tools"""

    def solve(self) -> Dict:
        model = cp_model.CpModel()

        # Variables: x[s][u] means step s is assigned to user u
        x = [[model.NewBoolVar(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        # Each step must be assigned exactly one user
        for s in range(self.instance.number_of_steps):
            model.AddExactlyOne(x[s])

        # Add constraints
        if self.active_constraints['authorizations']:
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u]:
                    for s in range(self.instance.number_of_steps):
                        if s not in self.instance.auth[u]:
                            model.Add(x[s][u] == 0)

        if self.active_constraints['separation_of_duty']:
            for s1, s2 in self.instance.SOD:
                for u in range(self.instance.number_of_users):
                    model.Add(x[s1][u] + x[s2][u] <= 1)

        if self.active_constraints['binding_of_duty']:
            for s1, s2 in self.instance.BOD:
                for u in range(self.instance.number_of_users):
                    model.Add(x[s1][u] == x[s2][u])

        if self.active_constraints['at_most_k']:
            for k, steps in self.instance.at_most_k:
                # Create indicator variables for each user
                z = [model.NewBoolVar(f'z_{u}') for u in range(self.instance.number_of_users)]
                for u in range(self.instance.number_of_users):
                    # z[u] = 1 if user u is assigned any step in steps
                    step_vars = [x[s][u] for s in steps]
                    model.AddMaxEquality(z[u], step_vars)
                model.Add(sum(z) <= k)

        if self.active_constraints['one_team']:
            for steps, teams in self.instance.one_team:
                # Create team selection variables
                team_selected = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
                # Exactly one team must be selected
                model.AddExactlyOne(team_selected)
                
                # If team is selected, only its members can be assigned
                for team_idx, team in enumerate(teams):
                    team_users = set(team)
                    for s in steps:
                        # Create implications for each non-team user
                        for u in range(self.instance.number_of_users):
                            if u not in team_users:
                                # When team is selected, user cannot be assigned
                                model.Add(x[s][u] == 0).OnlyEnforceIf(team_selected[team_idx])

        # Solve
        solver = cp_model.CpSolver()
        solution_collector = SolutionCollector("UDPB", x)
        
        start_time = time.time()
        status = solver.SearchForAllSolutions(model, solution_collector)
        end_time = time.time()

        return {
            'sat': 'sat' if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': solution_collector.get_solutions(),
            'solution_count': solution_collector.solution_count(),
            'is_unique': solution_collector.solution_count() == 1
        }