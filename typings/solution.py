from collections import defaultdict


class Solution:
    """Represents the result of solving a WSP instance"""
    def __init__(self, is_sat=False, solve_time=0, assignment=None, violations=None, reason=None):
        self.is_sat = is_sat
        self.solve_time = solve_time
        self.assignment = assignment or {}
        self.violations = violations or []
        self.reason = reason
        
    @staticmethod
    def create_unsat(solve_time, reason=None):
        """Create an UNSAT result"""
        return Solution(
            is_sat=False,
            solve_time=solve_time,
            reason=reason
        )
    
    @staticmethod
    def create_sat(solve_time, assignment):
        """Create a SAT result"""
        return Solution(
            is_sat=True,
            solve_time=solve_time,
            assignment=assignment
        )
        
    def get_metrics(self):
        """Get solving metrics and results"""
        return {
            'sat': 'sat' if self.is_sat else 'unsat',
            'exe_time': f"{self.solve_time * 1000:.2f}ms",
            'sol': [(step, user) for step, user in self.assignment.items()],
            'violations': self.violations,
            'reason': self.reason
        }


class Verifier:
    """Verifies and validates solutions to WSP instances"""
    def __init__(self, instance):
        self.instance = instance
        
    def verify(self, solution_dict):
        """Verify all constraints and return violations"""
        violations = []
        violations.extend(self._verify_authorizations(solution_dict))
        violations.extend(self._verify_sod(solution_dict))
        violations.extend(self._verify_bod(solution_dict))
        violations.extend(self._verify_at_most_k(solution_dict))
        violations.extend(self._verify_one_team(solution_dict))
        return violations
        
    def _verify_authorizations(self, solution_dict):
        """Verify authorization constraints"""
        violations = []
        for step, user in solution_dict.items():
            if not self.instance.user_step_matrix[user-1][step-1]:
                violations.append(
                    f"Authorization Violation: User {user} not authorized for Step {step}"
                )
        return violations
        
    def _verify_sod(self, solution_dict):
        """Verify separation of duty constraints"""
        violations = []
        for s1, s2 in self.instance.SOD:
            s1, s2 = s1+1, s2+1  # Convert to 1-based indexing
            if solution_dict.get(s1) == solution_dict.get(s2):
                violations.append(
                    f"Separation of Duty Violation: Steps {s1} and {s2} "
                    f"both assigned to user {solution_dict[s1]}"
                )
        return violations
        
    def _verify_bod(self, solution_dict):
        """Verify binding of duty constraints"""
        violations = []
        for s1, s2 in self.instance.BOD:
            s1, s2 = s1+1, s2+1  # Convert to 1-based indexing
            if solution_dict.get(s1) != solution_dict.get(s2):
                violations.append(
                    f"Binding of Duty Violation: Step {s1} assigned to user "
                    f"{solution_dict.get(s1)} but step {s2} assigned to user "
                    f"{solution_dict.get(s2)}"
                )
        return violations
        
    def _verify_at_most_k(self, solution_dict):
        """Verify at-most-k constraints"""
        violations = []
        for k, steps in self.instance.at_most_k:
            user_counts = defaultdict(list)
            for step in steps:
                step_1based = step + 1
                if step_1based in solution_dict:
                    user = solution_dict[step_1based]
                    user_counts[user].append(step_1based)
            
            for user, assigned_steps in user_counts.items():
                if len(assigned_steps) > k:
                    violations.append(
                        f"At-most-{k} Violation: User {user} assigned to "
                        f"{len(assigned_steps)} steps {sorted(assigned_steps)} in "
                        f"constraint group {[s+1 for s in steps]}"
                    )
        return violations
        
    def _verify_one_team(self, solution_dict):
        """Verify one-team constraints"""
        violations = []
        for steps, teams in self.instance.one_team:
            steps_base1 = [s+1 for s in steps]
            assigned_users = set()
            
            for step in steps:
                step_1based = step + 1
                if step_1based in solution_dict:
                    assigned_users.add(solution_dict[step_1based] - 1)
            
            valid_team_found = False
            for team in teams:
                if all(user in team for user in assigned_users):
                    valid_team_found = True
                    break
            
            if not valid_team_found:
                violations.append(
                    f"One-team Violation: Assigned users {sorted(u+1 for u in assigned_users)} "
                    f"for steps {steps_base1} do not form a valid team"
                )
        return violations
