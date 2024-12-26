from typing import Dict
import time
import z3

from utils import log
from constants import SolverType
from solvers import BaseSolver
from constraints.zthree_constraints import Z3VariableManager, Z3ConstraintManager
from typings import Solution, UniquenessChecker, Verifier


class Z3Solver(BaseSolver):
    """Z3 solver implementation for WSP instances"""
    SOLVER_TYPE = SolverType.Z_THREE

    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        super().__init__(instance, active_constraints, gui_mode)
        self.solver = z3.Solver()
        self._setup_solver()
        
        # Initialize Z3-specific managers
        self.var_manager = Z3VariableManager(self.solver, instance)
        self.solution_verifier = Verifier(instance)
        
    def _setup_solver(self):
        """Configure Z3 solver parameters"""
        # Set timeout to 5 minutes
        self.solver.set("timeout", 300000)
        
        # Enable parallel solving if available
        self.solver.set("parallel.enable", True)
        
        # Use tactical solving
        self.solver.set("smt.tactical_solving", True)

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
            status = self.solver.check()
            
            self.solve_time = time.time() - start_time
            
            if status == z3.sat:
                log(self.gui_mode, "Found solution, checking uniqueness...")
                
                # Get first solution
                model = self.solver.model()
                first_solution = self.var_manager.get_assignment_from_model(model)
                
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
                result = self._handle_infeasible(start_time, status, conflicts)
                self._update_statistics(result, conflicts)
                return result
                
        except Exception as e:
            log(self.gui_mode, f"Error during solving: {str(e)}")
            result = self._handle_error(start_time, e)
            self._update_statistics(result, conflicts)
            return result

    def _build_model(self):
        """Build Z3 model"""
        try:
            log(self.gui_mode, "Creating variables...")
            if not self.var_manager.create_variables():
                return False
            
            log(self.gui_mode, "Adding constraints...")
            self.constraint_manager = Z3ConstraintManager(
                self.solver,
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
                
            return True
            
        except Exception as e:
            log(self.gui_mode, f"Error building model: {str(e)}")
            return False

    def _check_solution_uniqueness(self, solution: Dict[int, int]) -> bool:
        """Check if solution is unique by trying to find another one"""
        # Create blocking clause
        blocking_clause = []
        for step, user in solution.items():
            # Negate current assignment
            blocking_clause.append(
                z3.Not(self.var_manager.user_step_variables[user-1][step-1])
            )
            
        # Add blocking clause
        self.solver.add(z3.Or(blocking_clause))
        
        # Check for another solution
        status = self.solver.check()
        return status == z3.unsat  # Unique if no other solution exists
