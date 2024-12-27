from typing import Dict
import time
import networkx as nx
import numpy as np
import re
from typing import List, Tuple
from pgmpy.models import BayesianNetwork
from pgmpy.inference import VariableElimination
from pgmpy.factors.discrete import TabularCPD

from utils import log
from constants import SolverType
from solvers import BaseSolver
from constraints.bayesian_network_constraints import PGMPYVariableManager, PGMPYConstraintManager
from typings import Solution, Verifier


class BayesianNetworkSolver(BaseSolver):
    """PGMPY Bayesian Network solver for WSP instances"""
    SOLVER_TYPE = SolverType.BAYESIAN_NETWORK

    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        super().__init__(instance, active_constraints, gui_mode)
        self.model = BayesianNetwork()
        self.inference_engine = None
        self._setup_solver()
        
        # Initialize managers
        self.var_manager = PGMPYVariableManager(self.model, instance)
        self.solution_verifier = Verifier(instance)
        
    def _setup_solver(self):
        """Configure solver parameters"""
        # Use Variable Elimination as inference engine
        self.inference_engine = VariableElimination(self.model)
        
        # Set inference parameters
        self.max_iterations = 1000
        self.timeout = 300  # 5 minutes
        self.evidence_threshold = 0.9  # Probability threshold for accepting evidence

    def solve(self):
        """Main solving method"""
        conflicts = self.identify_constraint_conflicts()
        
        try:
            start_time = time.time()
            self.solve_time = 0
            
            log(self.gui_mode, "Building Bayesian Network...")
            if not self._build_model():
                log(self.gui_mode, "Failed to build model. Analyzing infeasibility...")
                result = self._handle_build_failure(start_time, conflicts)
                self._update_statistics(result, conflicts)
                return result

            # Initialize inference engine with built model
            self.inference_engine = VariableElimination(self.model)
            
            log(self.gui_mode, "Performing probabilistic inference...")
            assignment = None
            is_unique = False
            
            # Try to find solution through iterative inference
            for iteration in range(self.max_iterations):
                if time.time() - start_time > self.timeout:
                    break
                    
                # Get current solution
                current_assignment = self._find_most_likely_assignment()
                
                if current_assignment:
                    # Verify solution
                    violations = self.solution_verifier.verify_solution(current_assignment)
                    
                    if not violations:
                        # Found valid solution
                        assignment = current_assignment
                        is_unique = self._check_solution_uniqueness(assignment)
                        break
                    else:
                        # Add evidence to avoid this invalid solution
                        self._add_violation_evidence(violations)
                        
                # Update model beliefs
                self._update_model_beliefs()
            
            self.solve_time = time.time() - start_time
            
            if assignment:
                log(self.gui_mode, "Found solution, checking probabilistic uniqueness...")
                
                result = Solution.create_sat(
                    self.solve_time,
                    assignment
                )
                
                # Store uniqueness result
                self.solution_unique = is_unique
                
                # Add violations if any
                result.violations = []  # No violations since we found valid solution
                
                log(self.gui_mode, f"Solution is {'unique' if is_unique else 'not unique'}")
                
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
        """Build Bayesian Network model"""
        try:
            log(self.gui_mode, "Creating variables...")
            if not self.var_manager.create_variables():
                return False
            
            log(self.gui_mode, "Adding constraints...")
            self.constraint_manager = PGMPYConstraintManager(
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
                
            # Check network consistency
            is_consistent, consistency_errors = self.constraint_manager.check_network_consistency()
            if not is_consistent:
                log(self.gui_mode, "Network consistency errors:")
                for error in consistency_errors:
                    log(self.gui_mode, f"  - {error}")
                return False
                
            return True
            
        except Exception as e:
            log(self.gui_mode, f"Error building model: {str(e)}")
            return False

    def _find_most_likely_assignment(self) -> Dict[int, int]:
        """Find most likely assignment using probabilistic inference"""
        try:
            # Get marginal probabilities for all step variables
            queries = [self.var_manager.get_step_node(s) 
                      for s in range(self.instance.number_of_steps)]
            queries = [q for q in queries if q]
            
            marginalized = self.inference_engine.query(queries)
            
            # Extract most likely assignment for each step
            assignment = {}
            for step, node in enumerate(queries):
                if node in marginalized:
                    probs = marginalized[node].values
                    state_names = marginalized[node].state_names[node]
                    max_idx = probs.argmax()
                    assignment[step + 1] = state_names[max_idx]
                    
            return assignment
            
        except Exception as e:
            log(self.gui_mode, f"Error in inference: {str(e)}")
            return None

    def _check_solution_uniqueness(self, solution: Dict[int, int]) -> bool:
        """Check if solution is probabilistically unique"""
        try:
            # A solution is considered unique if:
            # 1. All assignments have high probability (>threshold)
            # 2. Alternative assignments have very low probability
            
            for step, user in solution.items():
                node = self.var_manager.get_step_node(step - 1)
                if node:
                    marginalized = self.inference_engine.query([node])
                    probs = marginalized[node].values
                    state_names = marginalized[node].state_names[node]
                    
                    # Get probability of assigned user
                    user_idx = state_names.index(user)
                    user_prob = probs[user_idx]
                    
                    if user_prob < self.evidence_threshold:
                        return False
                        
                    # Check if any alternative has significant probability
                    for idx, prob in enumerate(probs):
                        if idx != user_idx and prob > (1 - self.evidence_threshold):
                            return False
                            
            return True
            
        except Exception as e:
            log(self.gui_mode, f"Error checking uniqueness: {str(e)}")
            return False

    def _add_violation_evidence(self, violations: List[str]):
        """Add evidence to avoid constraint violations"""
        try:
            for violation in violations:
                # Parse violation to identify involved steps/users
                if "Binding of duty violation" in violation:
                    s1, s2 = self._parse_steps_from_violation(violation)
                    if s1 and s2:
                        # Add evidence to encourage same user
                        node1 = self.var_manager.get_step_node(s1 - 1)
                        node2 = self.var_manager.get_step_node(s2 - 1)
                        if node1 and node2:
                            cpd = self.model.get_cpds(node2)
                            if cpd:
                                # Modify CPD to increase probability of same user
                                values = cpd.values
                                values *= 0.5  # Reduce all probabilities
                                np.fill_diagonal(values, 1.0)  # Increase same-user probability
                                new_cpd = TabularCPD(
                                    variable=node2,
                                    variable_card=cpd.variable_card,
                                    values=values,
                                    evidence=cpd.evidence,
                                    evidence_card=cpd.evidence_card,
                                    state_names=cpd.state_names
                                )
                                self.model.remove_cpds(cpd)
                                self.model.add_cpds(new_cpd)
                                
                # Handle other violation types similarly...
                
        except Exception as e:
            log(self.gui_mode, f"Error adding violation evidence: {str(e)}")

    def _update_model_beliefs(self):
        """Update model beliefs based on current state"""
        try:
            # Get current probabilities
            marginals = self.constraint_manager.get_marginal_probabilities()
            
            # Update model based on constraint violation probabilities
            violation_probs = self.constraint_manager.get_constraint_violation_probabilities()
            
            # Modify CPDs to reduce violation probabilities
            for name, prob in violation_probs.items():
                if prob > 0:
                    self._reduce_violation_probability(name, prob)
                    
        except Exception as e:
            log(self.gui_mode, f"Error updating beliefs: {str(e)}")

    def _reduce_violation_probability(self, constraint_name: str, prob: float):
        """Modify network to reduce probability of specific constraint violation"""
        try:
            if constraint_name == 'binding_of_duty':
                for s1, s2 in self.instance.BOD:
                    node1 = self.var_manager.get_step_node(s1)
                    node2 = self.var_manager.get_step_node(s2)
                    if node1 and node2:
                        cpd = self.model.get_cpds(node2)
                        if cpd:
                            # Modify CPD to reduce different-user probability
                            values = cpd.values
                            values *= (1 - prob)  # Reduce all probabilities
                            np.fill_diagonal(values, 1.0)  # Keep same-user probability high
                            new_cpd = TabularCPD(
                                variable=node2,
                                variable_card=cpd.variable_card,
                                values=values,
                                evidence=cpd.evidence,
                                evidence_card=cpd.evidence_card,
                                state_names=cpd.state_names
                            )
                            self.model.remove_cpds(cpd)
                            self.model.add_cpds(new_cpd)
                            
            # Handle other constraint types similarly...
            
        except Exception as e:
            log(self.gui_mode, f"Error reducing violation probability: {str(e)}")

    def _parse_steps_from_violation(self, violation: str) -> Tuple[int, int]:
        """Parse step numbers from violation message"""
        try:
            match = re.search(r"Steps (\d+) and (\d+)", violation)
            if match:
                return int(match.group(1)), int(match.group(2))
        except:
            pass
        return None, None
