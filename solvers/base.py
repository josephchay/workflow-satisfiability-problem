import itertools
from abc import ABC, abstractmethod
from typing import Dict, List


class BaseWSPSolver(ABC):
    """Base class for all WSP solvers"""
    
    def __init__(self, instance, active_constraints):
        self.instance = instance
        self.active_constraints = active_constraints
        self.solution_limit = 2  # For uniqueness checking

    @abstractmethod
    def solve(self) -> Dict:
        """
        Solve the WSP instance.
        Returns:
            Dict with:
            - sat: 'sat' or 'unsat'
            - result_exe_time: execution time in ms
            - sol: list of assignments (step -> user)
            - solution_count: number of solutions found
            - is_unique: whether solution is unique
        """
        pass

    def _enforce_pattern_constraints(self, model, M, x=None):
        """Helper to enforce pattern-based constraints efficiently"""
        # Transitivity constraints for M variables
        for s1 in range(self.instance.number_of_steps):
            for s2 in range(s1 + 1, self.instance.number_of_steps):
                for s3 in range(self.instance.number_of_steps):
                    if s1 != s3 and s2 != s3:
                        model.Add(M[s1][s2] == 1).OnlyEnforceIf([M[s1][s3], M[s2][s3]])
                        model.Add(M[s1][s2] == 0).OnlyEnforceIf([M[s2][s3].Not(), M[s1][s3]])
                        model.Add(M[s1][s2] == 0).OnlyEnforceIf([M[s2][s3], M[s1][s3].Not()])

    def _add_at_most_k_constraint(self, model, M, k, steps):
        """Helper to add at-most-k constraint efficiently"""
        import itertools
        for subset in itertools.combinations(steps, k + 1):
            same_user_vars = []
            for s1, s2 in itertools.combinations(subset, 2):
                same_user_vars.append(M[min(s1,s2)][max(s1,s2)])
            model.AddBoolOr(same_user_vars)

    def verify_solution(self, solution: List[Dict[str, int]]) -> Dict[str, int]:
        """Helper to verify if solution satisfies all constraints"""
        
        """Verify solution satisfies all constraints and return violations count"""
        violations = {
            'authorization': 0,
            'separation_of_duty': 0,
            'binding_of_duty': 0,
            'at_most_k': 0,
            'one_team': 0
        }
        
        if not solution:
            return violations

        # Check step coverage
        assigned_steps = set(a['step'] for a in solution)
        if len(assigned_steps) != self.instance.number_of_steps:
            violations['step_coverage'] = self.instance.number_of_steps - len(assigned_steps)
            return violations

        # Check authorization violations
        for assignment in solution:
            step = assignment['step'] - 1  # Convert to 0-based
            user = assignment['user'] - 1  # Convert to 0-based
            
            if not self.instance.auth[user] or step not in self.instance.auth[user]:
                violations['authorization'] += 1

        # Check separation of duty
        for s1, s2 in self.instance.SOD:
            user1 = next(a['user'] for a in solution if a['step'] - 1 == s1)
            user2 = next(a['user'] for a in solution if a['step'] - 1 == s2)
            if user1 == user2:
                violations['separation_of_duty'] += 1

        # Check binding of duty
        for s1, s2 in self.instance.BOD:
            user1 = next(a['user'] for a in solution if a['step'] - 1 == s1)
            user2 = next(a['user'] for a in solution if a['step'] - 1 == s2)
            if user1 != user2:
                violations['binding_of_duty'] += 1

        # Check at-most-k
        for k, steps in self.instance.at_most_k:
            users = set()
            for step in steps:
                user = next(a['user'] for a in solution if a['step'] - 1 == step)
                users.add(user)
            if len(users) > k:
                violations['at_most_k'] += 1

        # Check one-team
        for steps, teams in self.instance.one_team:
            users = set()
            for step in steps:
                user = next(a['user'] for a in solution if a['step'] - 1 == step)
                users.add(user - 1)  # Convert to 0-based
            
            valid_team = False
            for team in teams:
                if users.issubset(set(team)):
                    valid_team = True
                    break
            if not valid_team:
                violations['one_team'] += 1

        return violations

    def _verify_pattern_consistency(self, solution: List[Dict[str, int]], M) -> bool:
        """Verify pattern variables are consistent with solution"""
        # Create pattern from solution
        pattern = {}
        for s1 in range(self.instance.number_of_steps):
            for s2 in range(s1 + 1, self.instance.number_of_steps):
                user1 = next(a['user'] for a in solution if a['step'] == s1 + 1)
                user2 = next(a['user'] for a in solution if a['step'] == s2 + 1)
                pattern[(s1, s2)] = (user1 == user2)
                
        # Verify M variables match pattern
        for (s1, s2), same_user in pattern.items():
            if bool(M[s1][s2]) != same_user:
                return False
                
        return True
    
    def _verify_variable_consistency(self, M):
        """Verify all variables are properly linked"""
        # Check symmetry
        for s1 in range(self.instance.number_of_steps):
            for s2 in range(s1 + 1, self.instance.number_of_steps):
                if M[s1][s2] != M[s2][s1]:
                    return False

        # Check transitivity
        for s1, s2, s3 in itertools.combinations(range(self.instance.number_of_steps), 3):
            # If s1,s2 same user and s2,s3 same user then s1,s3 must be same user
            if M[s1][s2] and M[s2][s3] and not M[s1][s3]:
                return False
            # If s1,s2 different user and s2,s3 same user then s1,s3 must be different user
            if not M[s1][s2] and M[s2][s3] and M[s1][s3]:
                return False

        return True