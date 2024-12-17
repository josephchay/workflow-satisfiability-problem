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
            - exe_time: execution time in ms
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

    def _verify_solution(self, solution: List[Dict[str, int]]) -> bool:
        """Helper to verify if solution satisfies all constraints"""
        # Implementation of constraint checking logic
        pass
