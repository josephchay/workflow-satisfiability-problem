from ortools.sat.python import cp_model
from typing import Dict
import time
import numpy
import itertools

from utils import SolutionCollector
from solvers import BaseWSPSolver


class ORToolsCSWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        print(f"Starting CS solving...")
        model = cp_model.CpModel()

        # Create variables - only once
        y = [model.NewIntVar(0, self.instance.number_of_users - 1, f'y_{s}')
             for s in range(self.instance.number_of_steps)]

        # Handle authorizations
        if self.active_constraints['authorizations']:
            for user in range(self.instance.number_of_users):
                if self.instance.auth[user]:  # If user has authorizations
                    for step in range(self.instance.number_of_steps):
                        if step not in self.instance.auth[user]:
                            # Create a proper linear constraint
                            model.Add(y[step] != user)

        # Handle separation of duty
        if self.active_constraints['separation_of_duty']:
            for (s1, s2) in self.instance.SOD:
                # Create proper linear constraint for inequality
                model.Add(y[s1] != y[s2])

        # Handle binding of duty
        if self.active_constraints['binding_of_duty']:
            for (s1, s2) in self.instance.BOD:
                model.Add(y[s1] == y[s2])

        # Handle at-most-k
        if self.active_constraints['at_most_k']:
            for (k, steps) in self.instance.at_most_k:
                # Create indicator variables for each user
                used_vars = []
                for u in range(self.instance.number_of_users):
                    # Create a boolean variable indicating if user u is used
                    used = model.NewBoolVar(f'used_{u}')
                    # Create constraints for steps
                    step_constraints = []
                    for s in steps:
                        # Create linear equality constraint
                        is_assigned = model.NewBoolVar(f'assigned_{s}_{u}')
                        model.Add(y[s] == u).OnlyEnforceIf(is_assigned)
                        model.Add(y[s] != u).OnlyEnforceIf(is_assigned.Not())
                        step_constraints.append(is_assigned)
                    
                    # Link used variable with step assignments
                    model.Add(sum(step_constraints) >= 1).OnlyEnforceIf(used)
                    model.Add(sum(step_constraints) == 0).OnlyEnforceIf(used.Not())
                    used_vars.append(used)
                
                # Add constraint on total number of users used
                model.Add(sum(used_vars) <= k)

        # Handle one-team
        if self.active_constraints['one_team']:
            for (steps, teams) in self.instance.one_team:
                # Create team selection variables
                team_vars = [model.NewBoolVar(f'team_{i}') for i in range(len(teams))]
                model.AddExactlyOne(team_vars)
                
                for team_idx, team in enumerate(teams):
                    for step in steps:
                        # Create constraints for team membership
                        team_constraints = []
                        for user in team:
                            # Create linear equality constraint
                            is_member = model.NewBoolVar(f'member_{step}_{user}_{team_idx}')
                            model.Add(y[step] == user).OnlyEnforceIf(is_member)
                            model.Add(y[step] != user).OnlyEnforceIf(is_member.Not())
                            team_constraints.append(is_member)
                        
                        # Only allow team members when team is selected
                        model.AddBoolOr(team_constraints).OnlyEnforceIf(team_vars[team_idx])
                        
                        # Prevent non-team members when team is selected
                        for user in range(self.instance.number_of_users):
                            if user not in team:
                                not_member = model.NewBoolVar(f'not_member_{step}_{user}_{team_idx}')
                                model.Add(y[step] != user).OnlyEnforceIf([team_vars[team_idx], not_member])

        solver = cp_model.CpSolver()
        solution_collector = SolutionCollector("CS", y)
        solver.parameters.enumerate_all_solutions = True

        start_time = time.time()
        status = solver.Solve(model, solution_collector)
        end_time = time.time()

        result = {
            'sat': 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': [],
            'solution_count': 0,
            'is_unique': False
        }

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            result['sat'] = 'sat'
            result['sol'] = solution_collector.get_solutions()
            result['solution_count'] = solution_collector.solution_count()
            result['is_unique'] = result['solution_count'] == 1

        return result


class ORToolsPBPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        print(f"Starting PBPB solving...")
        model = cp_model.CpModel()

        # Assignment variables
        x = [[model.NewBoolVar(f'x_{s}_{u}') 
              for u in range(self.instance.number_of_users)]
             for s in range(self.instance.number_of_steps)]

        # Pattern variables
        M = [[model.NewBoolVar(f'm_{s1}_{s2}') if s1 < s2 else None
              for s2 in range(self.instance.number_of_steps)]
             for s1 in range(self.instance.number_of_steps)]

        # Each step must be assigned exactly one user
        for s in range(self.instance.number_of_steps):
            model.Add(sum(x[s]) == 1)

        # Link M variables with x variables
        for s1 in range(self.instance.number_of_steps):
            for s2 in range(s1 + 1, self.instance.number_of_steps):
                # If M[s1][s2] is true, steps must be assigned same user
                for u in range(self.instance.number_of_users):
                    model.Add(x[s1][u] == x[s2][u]).OnlyEnforceIf(M[s1][s2])
                    model.Add(x[s1][u] + x[s2][u] <= 1).OnlyEnforceIf(M[s1][s2].Not())

        # Transitivity constraints
        for s1 in range(self.instance.number_of_steps):
            for s2 in range(s1 + 1, self.instance.number_of_steps):
                for s3 in range(s2 + 1, self.instance.number_of_steps):
                    # If s1,s2 same user and s2,s3 same user then s1,s3 must be same user
                    model.Add(M[s1][s3] == 1).OnlyEnforceIf([M[s1][s2], M[s2][s3]])

        if self.active_constraints['authorizations']:
            for u in range(self.instance.number_of_users):
                if self.instance.auth[u]:
                    for s in range(self.instance.number_of_steps):
                        if s not in self.instance.auth[u]:
                            model.Add(x[s][u] == 0)

        if self.active_constraints['separation_of_duty']:
            for (s1, s2) in self.instance.SOD:
                if s1 < s2:
                    model.Add(M[s1][s2] == 0)
                else:
                    model.Add(M[s2][s1] == 0)

        if self.active_constraints['binding_of_duty']:
            for (s1, s2) in self.instance.BOD:
                if s1 < s2:
                    model.Add(M[s1][s2] == 1)
                else:
                    model.Add(M[s2][s1] == 1)

        if self.active_constraints['at_most_k']:
            for (k, steps) in self.instance.at_most_k:
                for subset in itertools.combinations(steps, k + 1):
                    same_user_vars = []
                    for s1, s2 in itertools.combinations(subset, 2):
                        if s1 < s2:
                            same_user_vars.append(M[s1][s2])
                        else:
                            same_user_vars.append(M[s2][s1])
                    model.AddBoolOr(same_user_vars)

        solver = cp_model.CpSolver()
        solution_collector = SolutionCollector("PBPB", x)
        solver.parameters.enumerate_all_solutions = True

        start_time = time.time()
        status = solver.Solve(model, solution_collector)
        end_time = time.time()

        result = {
            'sat': 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': [],
            'solution_count': 0,
            'is_unique': False
        }

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            result['sat'] = 'sat'
            result['sol'] = solution_collector.get_solutions()
            result['solution_count'] = solution_collector.solution_count()
            result['is_unique'] = result['solution_count'] == 1

        return result


class ORToolsUDPBWSPSolver(BaseWSPSolver):
    def solve(self) -> Dict:
        print(f"Starting UDPB solving...")
        model = cp_model.CpModel()
        user_assignment = [[model.NewBoolVar(f'x_{s}_{u}') 
                        for u in range(self.instance.number_of_users)] 
                        for s in range(self.instance.number_of_steps)]

        for step in range(self.instance.number_of_steps):
            model.AddExactlyOne(user_assignment[step])

        if self.active_constraints['authorizations']:
            for user in range(self.instance.number_of_users):
                if self.instance.auth[user]:
                    for step in range(self.instance.number_of_steps):
                        if step not in self.instance.auth[user]:
                            model.Add(user_assignment[step][user] == 0)

        if self.active_constraints['separation_of_duty']:
            for (separated_step1, separated_step2) in self.instance.SOD:
                for user in range(self.instance.number_of_users):
                    model.Add(user_assignment[separated_step2][user] == 0).OnlyEnforceIf(user_assignment[separated_step1][user])
                    model.Add(user_assignment[separated_step1][user] == 0).OnlyEnforceIf(user_assignment[separated_step2][user])

        if self.active_constraints['binding_of_duty']:
            for (bound_step1, bound_step2) in self.instance.BOD:
                for user in range(self.instance.number_of_users):
                    model.Add(user_assignment[bound_step2][user] == 1).OnlyEnforceIf(user_assignment[bound_step1][user])
                    model.Add(user_assignment[bound_step1][user] == 1).OnlyEnforceIf(user_assignment[bound_step2][user])

        if self.active_constraints['at_most_k']:
            for (k, steps) in self.instance.at_most_k:
                user_assignment_flag = [model.NewBoolVar(f'flag_{u}') for u in range(self.instance.number_of_users)]
                for user in range(self.instance.number_of_users):
                    for step in steps:
                        model.Add(user_assignment_flag[user] == 1).OnlyEnforceIf(user_assignment[step][user])
                    model.Add(sum(user_assignment[step][user] for step in steps) >= user_assignment_flag[user])
                model.Add(sum(user_assignment_flag) <= k)

        if self.active_constraints['one_team']:
            for (steps, teams) in self.instance.one_team:
                team_flag = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
                model.AddExactlyOne(team_flag)
                for team_index in range(len(teams)):
                    for step in steps:
                        for user in teams[team_index]:
                            model.Add(user_assignment[step][user] == 0).OnlyEnforceIf(team_flag[team_index].Not())
                users_in_teams = list(numpy.concatenate(teams).flat)
                for step in steps:
                    for user in range(self.instance.number_of_users):
                        if user not in users_in_teams:
                            model.Add(user_assignment[step][user] == 0)

        solver = cp_model.CpSolver()
        solver.parameters.enumerate_all_solutions = False
        solver.parameters.num_search_workers = 4

        start_time = time.time()
        status = solver.Solve(model)
        end_time = time.time()

        result = {
            'sat': 'unsat', 
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': []
        }

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            result['sat'] = 'sat'
            solution = []
            for s in range(self.instance.number_of_steps):
                for u in range(self.instance.number_of_users):
                    if solver.Value(user_assignment[s][u]):
                        solution.append({'step': s + 1, 'user': u + 1})
            result['sol'] = solution

        return result
