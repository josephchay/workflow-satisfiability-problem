from ortools.sat.python import cp_model
from typing import Dict
import time
import itertools

from utils import SolutionCollector
from solvers import BaseWSPSolver


class ORToolsCSWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        model = cp_model.CpModel()
        
        y = []
        for s in range(self.instance.number_of_steps):
            users = [u for u in range(self.instance.number_of_users)]
            v = model.NewIntVarFromDomain(cp_model.Domain.FromValues(users), f'y{s}')
            y.append(v)

        for s in range(self.instance.number_of_steps):
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u] and s not in self.instance.auth[u]:
                    model.Add(y[s] != u)
        
        for s1, s2 in self.instance.SOD:
            model.Add(y[s1] != y[s2])
        
        for s1, s2 in self.instance.BOD:
            model.Add(y[s1] == y[s2])

        for k, steps in self.instance.at_most_k:
            z = [model.NewBoolVar(f'z_{u}') for u in range(self.instance.number_of_users)]
            for u in range(self.instance.number_of_users):
                step_vars = [y[s] == u for s in steps]
                model.AddMaxEquality(z[u], step_vars)
            model.Add(sum(z) <= k)

        for steps, teams in self.instance.one_team:
            team_selected = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
            model.AddExactlyOne(team_selected)
            for team_idx, team in enumerate(teams):
                for s in steps:
                    model.Add(y[s].In(team)).OnlyEnforceIf(team_selected[team_idx])

        solver = cp_model.CpSolver()
        collector = SolutionCollector("CS", y)
        start_time = time.time()
        status = solver.SearchForAllSolutions(model, collector)
        end_time = time.time()

        return {
            'sat': 'sat' if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': collector.get_solutions(),
            'solution_count': collector.solution_count(),
            'is_unique': collector.solution_count() == 1
        }


class ORToolsPBPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        model = cp_model.CpModel()

        x = [[model.NewBoolVar(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        M = [[model.NewBoolVar(f'M_{s1}_{s2}') if s1 != s2 else None
              for s2 in range(self.instance.number_of_steps)]
             for s1 in range(self.instance.number_of_steps)]

        for s in range(self.instance.number_of_steps):
            model.AddExactlyOne(x[s])

        for s1, s2 in itertools.combinations(range(self.instance.number_of_steps), 2):
            for u in range(self.instance.number_of_users):
                model.Add(x[s1][u] == x[s2][u]).OnlyEnforceIf(M[s1][s2])
                model.Add(x[s1][u] != x[s2][u]).OnlyEnforceIf(M[s1][s2].Not())

        for s1 in range(self.instance.number_of_steps):
            for s2 in range(s1 + 1, self.instance.number_of_steps):
                for s3 in range(self.instance.number_of_steps):
                    if s1 != s3 and s2 != s3:
                        model.Add(M[s1][s2] == 1).OnlyEnforceIf([M[s1][s3], M[s2][s3]])

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
                team_selected = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
                model.AddExactlyOne(team_selected)
                for team_idx, team in enumerate(teams):
                    for s1, s2 in itertools.combinations(steps, 2):
                        model.Add(M[min(s1,s2)][max(s1,s2)] == 1).OnlyEnforceIf(team_selected[team_idx])

        solver = cp_model.CpSolver()
        collector = SolutionCollector("PBPB", x)
        start_time = time.time()
        status = solver.SearchForAllSolutions(model, collector)
        end_time = time.time()

        return {
            'sat': 'sat' if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': collector.get_solutions(),
            'solution_count': collector.solution_count(),
            'is_unique': collector.solution_count() == 1
        }


class ORToolsUDPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        model = cp_model.CpModel()

        x = [[model.NewBoolVar(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        for s in range(self.instance.number_of_steps):
            model.AddExactlyOne(x[s])

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
                z = [model.NewBoolVar(f'z_{u}') for u in range(self.instance.number_of_users)]
                for u in range(self.instance.number_of_users):
                    step_vars = [x[s][u] for s in steps]
                    model.AddMaxEquality(z[u], step_vars)
                model.Add(sum(z) <= k)

        if self.active_constraints['one_team']:
            for steps, teams in self.instance.one_team:
                team_selected = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
                model.AddExactlyOne(team_selected)
                for team_idx, team in enumerate(teams):
                    for s in steps:
                        for u in range(self.instance.number_of_users):
                            if u not in team:
                                model.Add(x[s][u] == 0).OnlyEnforceIf(team_selected[team_idx])

        solver = cp_model.CpSolver()
        collector = SolutionCollector("UDPB", x)
        
        start_time = time.time()
        status = solver.SearchForAllSolutions(model, collector)
        end_time = time.time()

        return {
            'sat': 'sat' if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': collector.get_solutions(),
            'solution_count': collector.solution_count(),
            'is_unique': collector.solution_count() == 1
        }
