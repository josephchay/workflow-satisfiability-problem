# solver.py
from ortools.sat.python import cp_model
from typing import List, Dict, Optional
import time

class WSPSolver:
    def __init__(self, instance, active_constraints):
        self.instance = instance
        self.active_constraints = active_constraints
        
    def solve(self) -> Dict:
        # Create model
        model = cp_model.CpModel()

        # Create variables: user_assignment[s][u] means step s is assigned to user u
        user_assignment = [[model.NewBoolVar(f's{s + 1}: u{u + 1}') 
                        for u in range(self.instance.number_of_users)] 
                        for s in range(self.instance.number_of_steps)]

        # Constraint: each step must be assigned to exactly one user
        for step in range(self.instance.number_of_steps):
            model.AddExactlyOne(user_assignment[step][user] for user in range(self.instance.number_of_users))

        # Add active constraints
        if self.active_constraints['authorizations']:
            self._add_authorization_constraints(model, user_assignment)
        
        if self.active_constraints['separation_of_duty']:
            self._add_separation_of_duty_constraints(model, user_assignment)
        
        if self.active_constraints['binding_of_duty']:
            self._add_binding_of_duty_constraints(model, user_assignment)
        
        if self.active_constraints['at_most_k']:
            self._add_at_most_k_constraints(model, user_assignment)
        
        if self.active_constraints['one_team']:
            self._add_one_team_constraints(model, user_assignment)

        # Solve the model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60.0  # Set timeout to 60 seconds
        
        # Timing the solver process
        start_time = time.time()
        status = solver.Solve(model)
        end_time = time.time()

        # Process results
        result = {
            'sat': 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': []
        }

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            result['sat'] = 'sat'
            # Extract solution
            result['sol'] = [
                f's{s + 1}: u{u + 1}'
                for s in range(self.instance.number_of_steps)
                for u in range(self.instance.number_of_users)
                if solver.Value(user_assignment[s][u])
            ]

        return result
    
    def _add_authorization_constraints(self, model, user_assignment):
        for user in range(self.instance.number_of_users):
            if self.instance.auth[user]:  # If user has specific authorizations
                for step in range(self.instance.number_of_steps):
                    if step not in self.instance.auth[user]:
                        model.Add(user_assignment[step][user] == 0)

    def _add_separation_of_duty_constraints(self, model, user_assignment):
        for (separated_step1, separated_step2) in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                # If user is assigned to step1, they cannot be assigned to step2
                model.Add(user_assignment[separated_step2][user] == 0).OnlyEnforceIf(user_assignment[separated_step1][user])
                model.Add(user_assignment[separated_step1][user] == 0).OnlyEnforceIf(user_assignment[separated_step2][user])

    def _add_binding_of_duty_constraints(self, model, user_assignment):
        for (bound_step1, bound_step2) in self.instance.BOD:
            for user in range(self.instance.number_of_users):
                # If user is assigned to step1, they must be assigned to step2 and vice versa
                model.Add(user_assignment[bound_step2][user] == 1).OnlyEnforceIf(user_assignment[bound_step1][user])
                model.Add(user_assignment[bound_step1][user] == 1).OnlyEnforceIf(user_assignment[bound_step2][user])

    def _add_at_most_k_constraints(self, model, user_assignment):
        for (k, steps) in self.instance.at_most_k:
            # Create indicator variables for users involved in the steps
            user_involved = [model.NewBoolVar(f'at-most-k_u{u}') for u in range(self.instance.number_of_users)]
            for user in range(self.instance.number_of_users):
                # User is involved if they're assigned to any of the steps
                step_assignments = [user_assignment[step][user] for step in steps]
                model.AddMaxEquality(user_involved[user], step_assignments)
            
            # Ensure at most k users are involved
            model.Add(sum(user_involved) <= k)

    def _add_one_team_constraints(self, model, user_assignment):
        for (steps, teams) in self.instance.one_team:
            # Create variables for team selection
            team_selected = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
            
            # Exactly one team must be selected
            model.AddExactlyOne(team_selected)
            
            # For each team
            for team_idx, team in enumerate(teams):
                # For each step in the constraint
                for step in steps:
                    # If this team is selected
                    # Only users from this team can be assigned to the steps
                    for user in range(self.instance.number_of_users):
                        if user not in team:
                            model.Add(user_assignment[step][user] == 0).OnlyEnforceIf(team_selected[team_idx])