from typing import Dict
import time
import gurobipy as gp
from gurobipy import GRB

from utils import log
from constants import SolverType
from solvers import BaseSolver
from constraints.gurobi_constraints import GurobiVariableManager, GurobiConstraintManager
from typings import Solution, UniquenessChecker, Verifier


class GurobiSolver(BaseSolver):
    """Gurobi solver implementation for WSP instances"""
    SOLVER_TYPE = SolverType.GUROBI

    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        super().__init__(instance, active_constraints, gui_mode)
        self.model = gp.Model("WSP")
        self._setup_solver()
        
        # Initialize Gurobi-specific managers
        self.var_manager = GurobiVariableManager(self.model, instance)
        self.solution_verifier = Verifier(instance)
        
    def _setup_solver(self):
        """Configure Gurobi solver parameters"""
        # Set timeout to 5 minutes
        self.model.setParam('TimeLimit', 300)
        
        # Enable parallel solving
        self.model.setParam('Threads', 8)
        
        # Tuning parameters
        self.model.setParam('MIPFocus', 1)  # Focus on finding feasible solutions
        self.model.setParam('Cuts', 2)      # Aggressive cut generation
        self.model.setParam('Presolve', 2)  # Aggressive presolve

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
            self.model.optimize()
            
            self.solve_time = time.time() - start_time
            
            if self.model.Status == GRB.OPTIMAL or self.model.Status == GRB.SOLUTION_LIMIT:
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
                result = self._handle_infeasible(start_time, self.model.Status, conflicts)
                self._update_statistics(result, conflicts)
                return result
                
        except Exception as e:
            log(self.gui_mode, f"Error during solving: {str(e)}")
            result = self._handle_error(start_time, e)
            self._update_statistics(result, conflicts)
            return result

    def _build_model(self):
        """Build Gurobi model"""
        try:
            log(self.gui_mode, "Creating variables...")
            if not self.var_manager.create_variables():
                return False
            
            log(self.gui_mode, "Adding constraints...")
            self.constraint_manager = GurobiConstraintManager(
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
                
            return True
            
        except Exception as e:
            log(self.gui_mode, f"Error building model: {str(e)}")
            return False
    
    def _check_solution_uniqueness(self, solution: Dict[int, int]) -> bool:
        """Check if solution is unique by trying to find another one"""
        # Create blocking constraint
        lhs = gp.LinExpr()
        for step, user in solution.items():
            var = self.var_manager.user_step_variables[user-1][step-1]
            lhs += var
            
        # Add constraint to exclude current solution
        num_assignments = len(solution)
        self.model.addConstr(lhs <= num_assignments - 1)
        
        # Try to find another solution
        self.model.optimize()
        
        return self.model.Status != GRB.OPTIMAL
