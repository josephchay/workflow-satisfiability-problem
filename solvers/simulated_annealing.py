import random
import math
from collections import defaultdict
import time

from dataclasses import dataclass
from typing import List, Dict, Set, Tuple

from utils import log
from constants import SolverType
from solvers import BaseSolver
from constraints.simulated_annealing_constraints import SAVariableManager, SAConstraintManager
from typings import Solution, UniquenessChecker, Verifier


@dataclass
class SAState:
    """Represents a state in the simulated annealing process"""
    assignment: Dict[int, int]  # Maps steps to users
    energy: float              # Current solution cost/energy
    violations: List[str]      # List of constraint violations
    temperature: float         # Current temperature


class SimulatedAnnealingSolver:
    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        self.instance = instance
        self.active_constraints = active_constraints
        self.gui_mode = gui_mode
        
        # SA Parameters
        self.initial_temp = 100.0
        self.final_temp = 0.1
        self.cooling_rate = 0.95
        self.iterations_per_temp = 100
        self.stagnation_limit = 20
        
        # Best solution tracking
        self.best_state = None
        self.best_energy = float('inf')
        
        # Statistics tracking
        self.iterations = 0
        self.accepted_moves = 0
        self.rejected_moves = 0
        self.constraint_violations = defaultdict(int)
        
    def solve(self) -> Solution:
        """Main solving method using simulated annealing"""
        start_time = time.time()
        
        try:
            # Generate initial solution
            current_state = self._generate_initial_state()
            self.best_state = current_state
            self.best_energy = current_state.energy
            
            # Initialize temperature
            temp = self.initial_temp
            stagnant_temps = 0
            
            # Main annealing loop
            while temp > self.final_temp and stagnant_temps < self.stagnation_limit:
                improved = False
                
                for _ in range(self.iterations_per_temp):
                    self.iterations += 1
                    
                    # Generate neighbor state
                    neighbor_state = self._generate_neighbor(current_state)
                    
                    # Calculate energy difference
                    delta_e = neighbor_state.energy - current_state.energy
                    
                    # Accept or reject new solution
                    if self._should_accept(delta_e, temp):
                        current_state = neighbor_state
                        self.accepted_moves += 1
                        
                        # Update best solution if improved
                        if neighbor_state.energy < self.best_energy:
                            self.best_state = neighbor_state
                            self.best_energy = neighbor_state.energy
                            improved = True
                    else:
                        self.rejected_moves += 1
                
                # Update temperature
                temp *= self.cooling_rate
                
                # Check for stagnation
                if not improved:
                    stagnant_temps += 1
                else:
                    stagnant_temps = 0
                    
                # Log progress
                self._log_progress(temp, current_state)
            
            # Create solution object
            solve_time = time.time() - start_time
            if self.best_energy == 0:  # Perfect solution found
                result = Solution.create_sat(
                    solve_time,
                    self.best_state.assignment,
                    violations=[]
                )

            else:  # Imperfect solution found
                result = Solution.create_unsat(
                    solve_time,
                    self.best_state.assignment,
                    violations=self.best_state.violations
                )

            return result
        
        except Exception as e:
            log(self.gui_mode, f"Error during solving: {str(e)}")
            return Solution.create_error(time.time() - start_time)

    def _generate_initial_state(self) -> SAState:
        """Generate initial solution ensuring authorization constraints"""
        assignment = {}
        
        # Assign each step to a random authorized user
        for step in range(self.instance.number_of_steps):
            authorized_users = self._get_authorized_users(step)
            if not authorized_users:
                raise ValueError(f"No authorized users for step {step+1}")
            assignment[step + 1] = random.choice(list(authorized_users)) + 1
            
        # Calculate initial energy and violations
        energy, violations = self._evaluate_state(assignment)
        
        return SAState(
            assignment=assignment,
            energy=energy,
            violations=violations,
            temperature=self.initial_temp
        )
        
    def _generate_neighbor(self, current: SAState) -> SAState:
        """Generate neighbor state by modifying current solution"""
        # Copy current assignment
        new_assignment = current.assignment.copy()
        
        # Choose random move type
        move_type = random.choice(['reassign', 'swap', 'chain'])
        
        if move_type == 'reassign':
            # Reassign single step to different authorized user
            step = random.randint(1, self.instance.number_of_steps)
            authorized = self._get_authorized_users(step - 1)
            if authorized:
                new_assignment[step] = random.choice(list(authorized)) + 1
                
        elif move_type == 'swap':
            # Swap assignments between two steps
            steps = list(new_assignment.keys())
            if len(steps) >= 2:
                s1, s2 = random.sample(steps, 2)
                if (self._is_authorized(new_assignment[s1]-1, s2-1) and 
                    self._is_authorized(new_assignment[s2]-1, s1-1)):
                    new_assignment[s1], new_assignment[s2] = new_assignment[s2], new_assignment[s1]
                    
        else:  # chain move
            # Perform cyclic reassignment among multiple steps
            steps = list(new_assignment.keys())
            chain_length = min(random.randint(3, 5), len(steps))
            chain_steps = random.sample(steps, chain_length)
            
            # Check if chain move is possible
            valid_chain = True
            for i in range(chain_length):
                next_i = (i + 1) % chain_length
                if not self._is_authorized(new_assignment[chain_steps[i]]-1, 
                                        chain_steps[next_i]-1):
                    valid_chain = False
                    break
                    
            if valid_chain:
                # Perform cyclic shift of assignments
                old_values = [new_assignment[s] for s in chain_steps]
                for i in range(chain_length):
                    new_assignment[chain_steps[i]] = old_values[(i-1)%chain_length]
        
        # Calculate new energy and violations
        energy, violations = self._evaluate_state(new_assignment)
        
        return SAState(
            assignment=new_assignment,
            energy=energy,
            violations=violations,
            temperature=current.temperature * self.cooling_rate
        )
        
    def _evaluate_state(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        """Calculate energy and violations for a state"""
        violations = []
        energy = 0
        
        # Check authorization constraints
        for step, user in assignment.items():
            if not self._is_authorized(user-1, step-1):
                violations.append(f"Authorization violation: User {user} not authorized for step {step}")
                energy += 100  # Heavy penalty for authorization violations
                
        # Check separation of duty
        if self.active_constraints.get('separation_of_duty', True):
            for s1, s2 in self.instance.SOD:
                if (s1+1 in assignment and s2+1 in assignment and 
                    assignment[s1+1] == assignment[s2+1]):
                    violations.append(
                        f"Separation of duty violation: Steps {s1+1} and {s2+1} assigned to same user"
                    )
                    energy += 50
                    
        # Check binding of duty
        if self.active_constraints.get('binding_of_duty', True):
            for s1, s2 in self.instance.BOD:
                if (s1+1 in assignment and s2+1 in assignment and 
                    assignment[s1+1] != assignment[s2+1]):
                    violations.append(
                        f"Binding of duty violation: Steps {s1+1} and {s2+1} not assigned to same user"
                    )
                    energy += 50
                    
        # Check at-most-k
        if self.active_constraints.get('at_most_k', True):
            for k, steps in self.instance.at_most_k:
                user_counts = defaultdict(int)
                for step in steps:
                    if step+1 in assignment:
                        user_counts[assignment[step+1]] += 1
                        
                for user, count in user_counts.items():
                    if count > k:
                        violations.append(
                            f"At-most-{k} violation: User {user} assigned {count} steps"
                        )
                        energy += 30 * (count - k)
                        
        # Check one-team constraints
        if self.active_constraints.get('one_team', True):
            for steps, teams in self.instance.one_team:
                assigned_users = {assignment[s+1] for s in steps if s+1 in assignment}
                if assigned_users:
                    valid_team = False
                    for team in teams:
                        if all(user in team for user in assigned_users):
                            valid_team = True
                            break
                    if not valid_team:
                        violations.append(
                            f"One-team violation: Users {list(assigned_users)} not from same team"
                        )
                        energy += 40
                        
        # Check super user at least
        if self.active_constraints.get('super_user_at_least', True):
            for scope, h, super_users in self.instance.sual:
                assigned_users = {assignment[s+1] for s in scope if s+1 in assignment}
                if len(assigned_users) <= h:
                    if not any(user in super_users for user in assigned_users):
                        violations.append(
                            f"SUAL violation: No super user in assignment {list(assigned_users)}"
                        )
                        energy += 45
                        
        # Check wang-li constraints
        if self.active_constraints.get('wang_li', True):
            for scope, departments in self.instance.wang_li:
                assigned_users = {assignment[s+1] for s in scope if s+1 in assignment}
                if assigned_users:
                    valid_dept = False
                    for dept in departments:
                        if all(user in dept for user in assigned_users):
                            valid_dept = True
                            break
                    if not valid_dept:
                        violations.append(
                            f"Wang-Li violation: Users {list(assigned_users)} not from same department"
                        )
                        energy += 40
                        
        # Check assignment dependent authorization
        if self.active_constraints.get('assignment_dependent', True):
            for s1, s2, source_users, target_users in self.instance.ada:
                if (s1+1 in assignment and s2+1 in assignment and 
                    assignment[s1+1] in source_users):
                    if assignment[s2+1] not in target_users:
                        violations.append(
                            f"ADA violation: Step {s2+1} not assigned to target user"
                        )
                        energy += 35
                        
        return energy, violations

    def _should_accept(self, delta_e: float, temp: float) -> bool:
        """Decide whether to accept a neighbor solution"""
        if delta_e <= 0:  # Better solution
            return True
            
        # Accept worse solution with probability e^(-delta_e/temp)
        probability = math.exp(-delta_e / temp)
        return random.random() < probability
