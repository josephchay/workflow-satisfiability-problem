from collections import defaultdict
from typing import Dict
from ortools.sat.python import cp_model
import time

from utils import log
from constants import SolverType
from solvers import BaseSolver
from constraints.ortools_constraints import VariableManager, ConstraintManager
from typings import Solution, Verifier, UniquenessChecker


class ORToolsCPSolver(BaseSolver):
    SOLVER_TYPE = SolverType.ORTOOLS_CP

    """Main solver class for WSP instances"""
    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        self.instance = instance
        self.active_constraints = active_constraints
        self.gui_mode = gui_mode
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.solve_time = 0
        self._setup_solver()
        
        # Initialize managers
        self.var_manager = VariableManager(self.model, instance)

        # Initialize constraint manager
        self.constraint_manager = None
        self.solution_verifier = Verifier(instance)
        
        # Initialize statistics storage
        self.statistics = {
            "solution_status": {},
            "problem_size": {},
            "workload_distribution": {},
            "constraint_compliance": {},
            "constraint_distribution": {},
            "detailed_analysis": {}
        }

    def _setup_solver(self):
        """Configure solver parameters"""
        self.solver.parameters.num_search_workers = 8
        self.solver.parameters.log_search_progress = False
        self.solver.parameters.cp_model_presolve = True
        self.solver.parameters.linearization_level = 2
        self.solver.parameters.optimize_with_core = True

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
            # First find initial solution
            status = self.solver.Solve(self.model)
            
            # If solution found, save it and check uniqueness
            is_unique = None
            first_solution = None
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                # Save first solution
                log(self.gui_mode, "Found first solution, saving it...")
                first_solution = self.var_manager.get_assignment_from_solution(self.solver)
                
                log(self.gui_mode, "Checking solution uniqueness...")
                try:
                    # Create uniqueness checker
                    uniqueness_checker = UniquenessChecker(self.var_manager)
                    
                    # Configure solver for finding all solutions
                    self.solver.parameters.enumerate_all_solutions = True
                    self.solver.parameters.num_search_workers = 1  # Use single thread for enumeration
                    
                    # Try to find second solution
                    _ = self.solver.Solve(self.model, solution_callback=uniqueness_checker)
                    
                    # Store uniqueness result
                    is_unique = uniqueness_checker.solutions_found == 1
                    self.solution_unique = is_unique  # Store for statistics
                    
                    log(self.gui_mode, f"Uniqueness check complete: {'unique' if is_unique else 'not unique'}")
                except Exception as e:
                    log(self.gui_mode, f"Error during uniqueness check: {str(e)}")
                    # If uniqueness check fails, assume non-unique
                    is_unique = False
                    self.solution_unique = False
            
            self.solve_time = time.time() - start_time
            
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                log(self.gui_mode, "Processing solution...")
                # Use first solution we saved
                if first_solution:
                    # Create solution object using first solution found
                    result = Solution.create_sat(
                        self.solve_time,
                        first_solution
                    )
                else:
                    # Fallback to current solution if something went wrong
                    result = self._process_solution(start_time)
                    
                self._update_statistics(result, conflicts)
                return result
            else:
                log(self.gui_mode, "No solution found. Analyzing infeasibility...")
                result = self._handle_infeasible(start_time, status, conflicts)
                self._update_statistics(result, conflicts)
                return result
                
        except Exception as e:
            log(self.gui_mode, f"Error during solving: {str(e)}")
            result = self._handle_error(start_time, e)
            self._update_statistics(result, conflicts)
            return result

    def _process_solution(self, start_time):
        solution_dict =  self.var_manager.get_assignment_from_solution(self.solver)

        # log(self.gui_mode, "\nSolution found. Verifying constraints...")
        result = Solution.create_sat(
            time.time() - start_time,
            solution_dict
        )
        
        # Ensure violations field exists
        violations = self.solution_verifier.verify_solution(solution_dict) if hasattr(self.solution_verifier, 'verify_solution') else []
        result.violations = violations
        
        # Add required fields for metadata
        result.solve_time = self.solve_time
        result.solver_type = self.SOLVER_TYPE.value
        
        if violations:
            log(self.gui_mode, "\nCONSTRAINT VIOLATIONS FOUND!")
            # log(self.gui_mode, "\nConstraint Violations Found:")
            # for violation in violations:
            #     log(violation)
        else:
            log(self.gui_mode, "\nALL CONSTRAINTS SATISFIED!")

        return result
    
    def _build_model(self):
        """Build model with active constraints"""
        try:
            log(self.gui_mode, "Creating variables...")
            self.var_manager.create_variables()
            
            log(self.gui_mode, "Adding constraints...")
            self.constraint_manager = ConstraintManager(
                self.model,
                self.instance,
                self.var_manager
            )
            
            # Add active constraints only
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
