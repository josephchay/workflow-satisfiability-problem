from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from abc import ABC, abstractmethod


class SAVariableManager:
    """Manages variables for Simulated Annealing WSP solver"""
    def __init__(self, instance):
        self.instance = instance
        self.step_variables = {}
        self.user_step_variables = defaultdict(dict)
        self._initialized = False

    def create_variables(self) -> bool:
        """Create initial solution state"""
        try:
            self.step_variables.clear()
            self.user_step_variables.clear()
            
            # Map available assignments for each step
            for step in range(self.instance.number_of_steps):
                self.step_variables[step] = []
                for user in range(self.instance.number_of_users):
                    if self.instance.user_step_matrix[user][step]:
                        self.step_variables[step].append(user)
                        self.user_step_variables[user][step] = True
                        
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Error creating SA variables: {str(e)}")
            return False

    def get_authorized_users(self, step: int) -> Set[int]:
        """Get set of users authorized for a step"""
        return {user for user in range(self.instance.number_of_users)
                if self.instance.user_step_matrix[user][step]}

    def get_authorized_steps(self, user: int) -> Set[int]:
        """Get set of steps a user is authorized for"""
        return {step for step in range(self.instance.number_of_steps)
                if self.instance.user_step_matrix[user][step]}

    def get_department_authorized_users(self, step: int, department: Set[int]) -> Set[int]:
        """Get users from a specific department authorized for a step"""
        return self.get_authorized_users(step) & department

    def _check_initialized(self):
        """Ensure variables have been created"""
        if not self._initialized:
            raise RuntimeError("Variables not initialized. Call create_variables() first.")


class SAConstraint(ABC):
    """Base class for Simulated Annealing constraints"""
    def __init__(self, instance, var_manager: SAVariableManager):
        self.instance = instance
        self.var_manager = var_manager

    @abstractmethod
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        """Check if constraint can potentially be satisfied"""
        pass

    @abstractmethod
    def evaluate_violations(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        """Evaluate constraint violations and their contribution to energy"""
        pass


class SAAuthorizationConstraint(SAConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        infeasible_steps = []
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                infeasible_steps.append(step + 1)
                
        return (len(infeasible_steps) == 0, 
                [f"No authorized users for step {step}" for step in infeasible_steps])

    def evaluate_violations(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        violations = []
        energy = 0
        
        for step, user in assignment.items():
            if not self.instance.user_step_matrix[user-1][step-1]:
                violations.append(
                    f"Authorization violation: User {user} not authorized for step {step}"
                )
                energy += 100  # Heavy penalty for authorization violations
                
        return energy, violations


class SABindingOfDutyConstraint(SAConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        infeasible = []
        for s1, s2 in self.instance.BOD:
            common_users = {user for user in range(self.instance.number_of_users)
                          if (self.instance.user_step_matrix[user][s1] and 
                              self.instance.user_step_matrix[user][s2])}
            if not common_users:
                infeasible.append((s1 + 1, s2 + 1))
                
        return (len(infeasible) == 0,
                [f"No users authorized for both steps {s1} and {s2}" 
                 for s1, s2 in infeasible])

    def evaluate_violations(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        violations = []
        energy = 0
        
        for s1, s2 in self.instance.BOD:
            if (s1+1 in assignment and s2+1 in assignment and 
                assignment[s1+1] != assignment[s2+1]):
                violations.append(
                    f"Binding of duty violation: Steps {s1+1} and {s2+1} "
                    f"assigned to different users"
                )
                energy += 50
                
        return energy, violations


class SASeparationOfDutyConstraint(SAConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []  # Always potentially feasible if steps have multiple users

    def evaluate_violations(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        violations = []
        energy = 0
        
        for s1, s2 in self.instance.SOD:
            if (s1+1 in assignment and s2+1 in assignment and 
                assignment[s1+1] == assignment[s2+1]):
                violations.append(
                    f"Separation of duty violation: Steps {s1+1} and {s2+1} "
                    f"assigned to same user"
                )
                energy += 50
                
        return energy, violations


class SAAtMostKConstraint(SAConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        infeasible = []
        for k, steps in self.instance.at_most_k:
            total_users = len(set(u for u in range(self.instance.number_of_users)
                                for s in steps if self.instance.user_step_matrix[u][s]))
            min_users_needed = len(steps) / k
            if total_users < min_users_needed:
                infeasible.append((k, steps, total_users, min_users_needed))
                
        return (len(infeasible) == 0,
                [f"At-most-{k} constraint on steps {[s+1 for s in steps]} requires "
                 f"at least {min_needed:.0f} users but only has {total}" 
                 for k, steps, total, min_needed in infeasible])

    def evaluate_violations(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        violations = []
        energy = 0
        
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
                    
        return energy, violations


class SAOneTeamConstraint(SAConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []  # Always potentially feasible if teams not empty

    def evaluate_violations(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        violations = []
        energy = 0
        
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
                        f"One-team violation: Users {list(assigned_users)} "
                        f"not from same team"
                    )
                    energy += 40
                    
        return energy, violations


class SASUALConstraint(SAConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        errors = []
        
        for scope, h, super_users in self.instance.sual:
            for step in scope:
                authorized = self.var_manager.get_authorized_users(step)
                if len(authorized) <= h:
                    super_auth = authorized.intersection(super_users)
                    if not super_auth:
                        errors.append(
                            f"Step {step+1} must have either >{h} authorized users "
                            f"or at least one authorized super user"
                        )
                        
            common_super_users = set(super_users)
            for step in scope:
                common_super_users &= self.var_manager.get_authorized_users(step)
            if not common_super_users:
                errors.append(
                    f"No super user is authorized for all steps in scope {[s+1 for s in scope]}"
                )
                    
        return len(errors) == 0, errors

    def evaluate_violations(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        violations = []
        energy = 0
        
        for scope, h, super_users in self.instance.sual:
            assigned_users = {assignment[s+1] for s in scope if s+1 in assignment}
            if len(assigned_users) <= h:
                if not any(user in super_users for user in assigned_users):
                    violations.append(
                        f"SUAL violation: No super user assigned when {len(assigned_users)} "
                        f"users assigned to scope"
                    )
                    energy += 45
                    
        return energy, violations


class SAWangLiConstraint(SAConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        errors = []
        
        for scope, departments in self.instance.wang_li:
            valid_dept_found = False
            for dept_idx, dept in enumerate(departments):
                can_handle_all = True
                for step in scope:
                    auth_dept_users = self.var_manager.get_department_authorized_users(step, dept)
                    if not auth_dept_users:
                        can_handle_all = False
                        break
                if can_handle_all:
                    valid_dept_found = True
                    break
                    
            if not valid_dept_found:
                errors.append(
                    f"No department can handle all steps in scope {[s+1 for s in scope]}"
                )
                
        return len(errors) == 0, errors

    def evaluate_violations(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        violations = []
        energy = 0
        
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
                        f"Wang-Li violation: Users {list(assigned_users)} "
                        f"not from same department"
                    )
                    energy += 40
                    
        return energy, violations


class SAAssignmentDependentConstraint(SAConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        errors = []
        
        for s1, s2, source_users, target_users in self.instance.ada:
            # Verify there are authorized users in source_users for s1
            auth_source = self.var_manager.get_authorized_users(s1)
            if not auth_source.intersection(source_users):
                errors.append(
                    f"No authorized users from source set for step {s1+1}"
                )
                continue
                
            # If s1 can be assigned to source_users, verify s2 has target users
            auth_target = self.var_manager.get_authorized_users(s2)
            if not auth_target.intersection(target_users):
                errors.append(
                    f"No authorized users from target set for step {s2+1}"
                )
                
        return len(errors) == 0, errors

    def evaluate_violations(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        violations = []
        energy = 0
        
        for s1, s2, source_users, target_users in self.instance.ada:
            if (s1+1 in assignment and s2+1 in assignment and 
                assignment[s1+1] in source_users):
                if assignment[s2+1] not in target_users:
                    violations.append(
                        f"ADA violation: Step {s2+1} not assigned to target user when "
                        f"step {s1+1} assigned to source user"
                    )
                    energy += 35
                    
        return energy, violations


class SAConstraintManager:
    """Manages Simulated Annealing WSP constraints"""
    def __init__(self, instance, var_manager: SAVariableManager):
        self.instance = instance
        self.var_manager = var_manager
        
        # Initialize all constraints
        self.constraints = {
            'authorization': SAAuthorizationConstraint(instance, var_manager),
            'binding_of_duty': SABindingOfDutyConstraint(instance, var_manager),
            'separation_of_duty': SASeparationOfDutyConstraint(instance, var_manager),
            'at_most_k': SAAtMostKConstraint(instance, var_manager),
            'one_team': SAOneTeamConstraint(instance, var_manager),
            'super_user_at_least': SASUALConstraint(instance, var_manager),
            'wang_li': SAWangLiConstraint(instance, var_manager),
            'assignment_dependent': SAAssignmentDependentConstraint(instance, var_manager)
        }
        
        # Active constraints and weights
        self.active_constraints = {}
        self.constraint_weights = {
            'authorization': 100,
            'binding_of_duty': 50,
            'separation_of_duty': 50,
            'at_most_k': 30,
            'one_team': 40,
            'super_user_at_least': 45,
            'wang_li': 40,
            'assignment_dependent': 35
        }

    def check_all_feasibility(self) -> Tuple[bool, List[str]]:
        """Check if all active constraints are potentially feasible"""
        errors = []
        for name, constraint in self.constraints.items():
            if self.active_constraints.get(name, True):
                is_feasible, constraint_errors = constraint.check_feasibility()
                if not is_feasible:
                    errors.extend(constraint_errors)
        return len(errors) == 0, errors

    def evaluate_assignment(self, assignment: Dict[int, int]) -> Tuple[float, List[str]]:
        """Evaluate total energy and violations for an assignment"""
        total_energy = 0
        all_violations = []
        
        for name, constraint in self.constraints.items():
            if self.active_constraints.get(name, True):
                energy, violations = constraint.evaluate_violations(assignment)
                
                # Apply constraint-specific weight
                weighted_energy = energy * self.constraint_weights[name]
                total_energy += weighted_energy
                
                all_violations.extend(violations)
        
        return total_energy, all_violations

    def setup_constraints(self, active_constraints: dict) -> Tuple[bool, List[str]]:
        """Setup active constraints and check initial feasibility"""
        self.active_constraints = active_constraints
        
        # Check feasibility of active constraints
        return self.check_all_feasibility()
        
    def get_authorized_moves(self, step: int, current_assignment: Dict[int, int]) -> Set[int]:
        """Get set of authorized users that could be assigned to a step"""
        potential_users = self.var_manager.get_authorized_users(step)
        
        # Filter based on active constraints
        valid_users = set()
        for user in potential_users:
            # Try assignment temporarily
            test_assignment = current_assignment.copy()
            test_assignment[step + 1] = user + 1
            
            # Check if assignment would violate any hard constraints
            energy, _ = self.evaluate_assignment(test_assignment)
            
            # Consider only assignments that don't violate hard constraints
            if energy < float('inf'):
                valid_users.add(user)
                
        return valid_users
        
    def get_possible_swaps(self, current_assignment: Dict[int, int]) -> List[Tuple[int, int]]:
        """Find possible step pairs that could be swapped"""
        possible_swaps = []
        steps = list(current_assignment.keys())
        
        for i, s1 in enumerate(steps):
            for s2 in steps[i+1:]:
                # Check if users could be swapped
                user1 = current_assignment[s1]
                user2 = current_assignment[s2]
                
                if (self.instance.user_step_matrix[user2-1][s1-1] and 
                    self.instance.user_step_matrix[user1-1][s2-1]):
                    test_assignment = current_assignment.copy()
                    test_assignment[s1], test_assignment[s2] = user2, user1
                    
                    # Verify swap doesn't violate hard constraints
                    energy, _ = self.evaluate_assignment(test_assignment)
                    if energy < float('inf'):
                        possible_swaps.append((s1, s2))
                        
        return possible_swaps

    def get_constraint_violations(self, assignment: Dict[int, int]) -> Dict[str, List[str]]:
        """Get detailed breakdown of violations by constraint type"""
        violations_by_type = {}
        
        for name, constraint in self.constraints.items():
            if self.active_constraints.get(name, True):
                _, violations = constraint.evaluate_violations(assignment)
                if violations:
                    violations_by_type[name] = violations
                    
        return violations_by_type

    def adjust_weights(self, violation_history: List[Dict[str, int]]):
        """Dynamically adjust constraint weights based on violation history"""
        if not violation_history:
            return
            
        # Calculate average violations per constraint
        avg_violations = defaultdict(float)
        for violations in violation_history:
            for constraint, count in violations.items():
                avg_violations[constraint] += count
                
        for constraint in avg_violations:
            avg_violations[constraint] /= len(violation_history)
            
        # Adjust weights: increase weight for frequently violated constraints
        for constraint, avg_count in avg_violations.items():
            if avg_count > 0:
                self.constraint_weights[constraint] *= (1 + avg_count / 10)
                
        # Normalize weights to maintain relative scale
        max_weight = max(self.constraint_weights.values())
        if max_weight > 100:
            scale = 100 / max_weight
            for constraint in self.constraint_weights:
                self.constraint_weights[constraint] *= scale
