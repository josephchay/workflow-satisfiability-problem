from typing import Dict
import time
from jpype import startJVM, getDefaultJVMPath, JClass, JInt, java

from utils import log
from constants import SolverType
from solvers import BaseSolver
from constraints.satfourj_constraints import SAT4JVariableManager, SAT4JConstraintManager
from typings import Solution, Verifier


class SAT4JSolver(BaseSolver):
    """SAT4J solver implementation for WSP instances"""
    SOLVER_TYPE = SolverType.SAT4J

    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        super().__init__(instance, active_constraints, gui_mode)
        self._init_jvm()
        self._setup_solver()
        
        # Initialize SAT4J-specific managers
        self.var_manager = SAT4JVariableManager(self.solver, instance)
        self.solution_verifier = Verifier(instance)
        
    def _setup_solver(self):
        """Configure SAT4J solver"""
        # Create new default solver
        self.solver = self.SolverFactory.newDefault()
        
        # Configure solver parameters
        self.solver.setTimeout(300)  # 5 minute timeout
        self.solver.setVerbose(False)  # Suppress output
        
        # Set expected number of variables and clauses
        max_vars = self.instance.number_of_steps * self.instance.number_of_users
        max_clauses = max_vars * max_vars  # Conservative estimate
        self.solver.newVar(max_vars)
        self.solver.setExpectedNumberOfClauses(max_clauses)

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
            
            # Save original clauses for uniqueness checking
            self.var_manager.save_original_clauses()
            
            # Find solution
            is_sat = self.solver.isSatisfiable()
            self.solve_time = time.time() - start_time
            
            if is_sat:
                log(self.gui_mode, "Found solution, checking uniqueness...")
                
                # Get first solution
                model = self.solver.model()
                first_solution = self.var_manager.get_assignment_from_model(model)
                
                # Check uniqueness
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
                
            else:
                log(self.gui_mode, "No solution found, analyzing infeasibility...")
                result = self._handle_infeasible(start_time, conflicts)
                
            self._update_statistics(result, conflicts)
            return result
                
        except Exception as e:
            log(self.gui_mode, f"Error during solving: {str(e)}")
            result = self._handle_error(start_time, e)
            self._update_statistics(result, conflicts)
            return result

    def _build_model(self):
        """Build SAT4J model"""
        try:
            log(self.gui_mode, "Creating variables...")
            if not self.var_manager.create_variables():
                return False
            
            log(self.gui_mode, "Adding constraints...")
            self.constraint_manager = SAT4JConstraintManager(
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
        try:
            # Create blocking clause for current solution
            blocking_literals = []
            for step, user in solution.items():
                var_id = self.var_manager.user_step_variables[user-1][step-1]
                blocking_literals.append(-var_id)  # Negate each variable
            
            # Add blocking clause
            self.solver.addClause(blocking_literals)
            
            # Try to find another solution
            return not self.solver.isSatisfiable()
            
        except Exception as e:
            log(self.gui_mode, f"Error checking uniqueness: {str(e)}")
            return False
