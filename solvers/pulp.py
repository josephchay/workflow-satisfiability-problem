from typing import Dict
import time
import pulp

from utils import log
from constants import SolverType
from solvers import BaseSolver
from constraints.pulp_constraints import PuLPVariableManager, PuLPConstraintManager
from typings import Solution, UniquenessChecker, Verifier


class PuLPSolver(BaseSolver):
    """PuLP solver implementation for WSP instances"""
    SOLVER_TYPE = SolverType.PULP

    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        super().__init__(instance, active_constraints, gui_mode)
        self.model = pulp.LpProblem("WSP", pulp.LpMinimize)
        self._setup_solver()
        
        # Initialize PuLP-specific managers
        self.var_manager = PuLPVariableManager(self.model, instance)
        self.solution_verifier = Verifier(instance)
        
    def _setup_solver(self):
        """Configure PuLP solver parameters"""
        # We'll use CBC solver with customized parameters
        self.solver = pulp.PULP_CBC_CMD(
            msg=False,         # Suppress output
            timeLimit=300,     # 5 minute timeout
            threads=8,         # Use parallel processing
            gapRel=0.0,       # Require optimal solution
            presolve=True     # Enable presolving
        )

    def solve(self):
        """Main solving method"""
        conflicts = self.identify_constraint_conflicts()
        
        try:
            start_time = time.time()
            self.solve_time = 0
            
            log(self.gui_mode, "Building model...")
            if not self._build_model():
                log(self.gui_mode, "Failed to build model. Analyzing infeasibility...")
                result = self._handle_build_failure(start_time, conflicts)
                self._update_statistics(result, conflicts)
                return result

            log(self.gui_mode, "Solving model...")
            self.model.solve(self.solver)
            
            self.solve_time = time.time() - start_time
            
            if pulp.LpStatus[self.model.status] == 'Optimal':
                log(self.gui_mode, "Found solution, checking uniqueness...")
                
                # Get first solution
                first_solution = self.var_manager.get_assignment_from_solution()
                
                # Check uniqueness by trying to find another solution
                self.solution_unique = self._check_solution_uniqueness(first_solution)
                
                log(self.gui_mode, f"Solution is {'unique' if self.solution_unique else 'not unique'}")
                
                # Create solution object
                result = Solution.create_sat(
                    self.solve_time,
                    first_solution
                )
                
                # Add violations if any
                violations = self.solution_verifier.verify_solution(first_solution)
                result.violations = violations
                
                if violations:
                    log(self.gui_mode, "\nCONSTRAINT VIOLATIONS FOUND!")
                else:
                    log(self.gui_mode, "\nALL CONSTRAINTS SATISFIED!")
                
                self._update_statistics(result, conflicts)
                return result
                
            else:
                log(self.gui_mode, "No solution found, analyzing infeasibility...")
                result = self._handle_infeasible(start_time, self.model.status, conflicts)
                self._update_statistics(result, conflicts)
                return result
                
        except Exception as e:
            log(self.gui_mode, f"Error during solving: {str(e)}")
            result = self._handle_error(start_time, e)
            self._update_statistics(result, conflicts)
            return result

    def _build_model(self):
        """Build PuLP model"""
        try:
            log(self.gui_mode, "Creating variables...")
            if not self.var_manager.create_variables():
                return False
            
            log(self.gui_mode, "Adding constraints...")
            self.constraint_manager = PuLPConstraintManager(
                self.model,
                self.instance,
                self.var_manager
            )
            
            # Add active constraints
            is_feasible, errors = self.constraint_manager.add_constraints(self.active_constraints)
            if not is_feasible:
                log(self.gui_mode, "Failed to add constraints:")
                for error in errors:
                    log(self.gui_mode, f"  - {error}")
                return False
                
            # Add objective function (minimize total assignments as simple default)
            all_vars = []
            for user_vars in self.var_manager.user_step_variables.values():
                all_vars.extend(user_vars.values())
            self.model += pulp.lpSum(all_vars)
                
            return True
            
        except Exception as e:
            log(self.gui_mode, f"Error building model: {str(e)}")
            return False

    def _check_solution_uniqueness(self, solution: Dict[int, int]) -> bool:
        """Check if solution is unique by trying to find another one"""
        try:
            # Create new constraint to exclude current solution
            exclude_expr = []
            for step, user in solution.items():
                var = self.var_manager.user_step_variables[user-1][step-1]
                exclude_expr.append(var)
            
            # Add constraint: sum of all variables in current solution must be less than total
            num_assignments = len(solution)
            self.model += (pulp.lpSum(exclude_expr) <= num_assignments - 1,
                         'uniqueness_check')
            
            # Try to solve again
            self.model.solve(self.solver)
            
            # Solution is unique if no other feasible solution exists
            return pulp.LpStatus[self.model.status] != 'Optimal'
            
        except Exception as e:
            log(self.gui_mode, f"Error checking uniqueness: {str(e)}")
            return False
