from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple, Any
import pulp
from collections import defaultdict


class PuLPVariableManager:
    """Manages PuLP variables for the WSP problem"""
    def __init__(self, model: pulp.LpProblem, instance):
        self.model = model
        self.instance = instance
        self.step_variables: Dict[int, List[Tuple[int, pulp.LpVariable]]] = {}
        self.user_step_variables: Dict[int, Dict[int, pulp.LpVariable]] = defaultdict(dict)
        self._initialized = False
        
    def create_variables(self) -> bool:
        try:
            self.step_variables.clear()
            self.user_step_variables.clear()
            
            # Create variables only for authorized user-step pairs
            for step in range(self.instance.number_of_steps):
                self.step_variables[step] = []
                for user in range(self.instance.number_of_users):
                    if self.instance.user_step_matrix[user][step]:
                        var = pulp.LpVariable(
                            f's{step + 1}_u{user + 1}',
                            cat='Binary'
                        )
                        self.step_variables[step].append((user, var))
                        self.user_step_variables[user][step] = var
                        
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Error creating PuLP variables: {str(e)}")
            return False

    def get_step_variables(self, step: int) -> List[Tuple[int, pulp.LpVariable]]:
        """Get list of (user, variable) pairs for a step"""
        self._check_initialized()
        return self.step_variables.get(step, [])

    def get_user_variables(self, user: int) -> Dict[int, pulp.LpVariable]:
        """Get dictionary of {step: variable} for a user"""
        self._check_initialized()
        return self.user_step_variables[user]

    def get_user_step_variable(self, user: int, step: int) -> pulp.LpVariable:
        """Get variable for specific user-step pair"""
        self._check_initialized()
        return self.user_step_variables[user].get(step)

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

    def get_user_step_variables_filtered(self, step: int, user_set: Set[int]) -> List[Tuple[int, pulp.LpVariable]]:
        """Get variables for a step filtered by a specific set of users"""
        return [(user, var) for user, var in self.step_variables[step] 
                if user in user_set]

    def _check_initialized(self):
        """Ensure variables have been created"""
        if not self._initialized:
            raise RuntimeError("Variables not initialized. Call create_variables() first.")

    def get_assignment_from_solution(self) -> Dict[int, int]:
        """Extract step -> user assignment from solver solution"""
        self._check_initialized()
        
        assignment = {}
        for step in range(self.instance.number_of_steps):
            for user, var in self.step_variables[step]:
                if abs(pulp.value(var)) > 0.5:  # Binary variable is set
                    assignment[step + 1] = user + 1
                    break
        return assignment

class PuLPConstraint(ABC):
    """Base class for PuLP constraints"""
    def __init__(self, model: pulp.LpProblem, instance, var_manager: PuLPVariableManager):
        self.model = model
        self.instance = instance
        self.var_manager = var_manager

    @abstractmethod
    def add_to_model(self) -> bool:
        """Add constraint to the model. Returns False if infeasible."""
        pass

    @abstractmethod
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        """Check if constraint can potentially be satisfied."""
        pass

class PuLPAuthorizationConstraint(PuLPConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        infeasible_steps = []
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                infeasible_steps.append(step + 1)
                
        return (len(infeasible_steps) == 0, 
                [f"No authorized users for step {step}" for step in infeasible_steps])

    def add_to_model(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for step, user_vars in self.var_manager.step_variables.items():
            # Exactly one user per step
            self.model += pulp.lpSum(var for _, var in user_vars) == 1, f'auth_step_{step}'
        return True

class PuLPBindingOfDutyConstraint(PuLPConstraint):
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

    def add_to_model(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for s1, s2 in self.instance.BOD:
            for user in range(self.instance.number_of_users):
                if (s1 in self.var_manager.user_step_variables[user] and 
                    s2 in self.var_manager.user_step_variables[user]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    self.model += var1 == var2, f'bod_{s1}_{s2}_{user}'
        return True

class PuLPSeparationOfDutyConstraint(PuLPConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []

    def add_to_model(self) -> bool:
        for s1, s2 in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                if (s1 in self.var_manager.user_step_variables[user] and 
                    s2 in self.var_manager.user_step_variables[user]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    self.model += var1 + var2 <= 1, f'sod_{s1}_{s2}_{user}'
        return True

class PuLPAtMostKConstraint(PuLPConstraint):
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

    def add_to_model(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for k, steps in self.instance.at_most_k:
            for user in range(self.instance.number_of_users):
                user_step_vars = []
                for step in steps:
                    if step in self.var_manager.user_step_variables[user]:
                        user_step_vars.append(
                            self.var_manager.user_step_variables[user][step]
                        )
                
                if user_step_vars:
                    self.model += (pulp.lpSum(user_step_vars) <= k, 
                                 f'at_most_{k}_user_{user}')
        
        # Add global limit based on minimum k
        if self.instance.at_most_k:
            min_k = min(k for k, _ in self.instance.at_most_k)
            for user in range(self.instance.number_of_users):
                user_vars = []
                for step in range(self.instance.number_of_steps):
                    if step in self.var_manager.user_step_variables[user]:
                        user_vars.append(self.var_manager.user_step_variables[user][step])
                if user_vars:
                    self.model += (pulp.lpSum(user_vars) <= min_k,
                                 f'global_limit_user_{user}')
                    
        return True
    
class PuLPOneTeamConstraint(PuLPConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []

    def add_to_model(self) -> bool:
        for steps, teams in self.instance.one_team:
            # Create team choice variables
            team_vars = []
            for i in range(len(teams)):
                team_var = pulp.LpVariable(
                    f'team_{len(self.model.constraints)}_{i}',
                    cat='Binary'
                )
                team_vars.append(team_var)
            
            # Exactly one team must be chosen
            self.model += (pulp.lpSum(team_vars) == 1,
                         f'one_team_choice_{len(self.model.constraints)}')
            
            for step in steps:
                for user, var in self.var_manager.get_step_variables(step):
                    # For each department
                    user_team_possible = []
                    for team_idx, team in enumerate(teams):
                        if user in team:
                            user_team_possible.append(team_vars[team_idx])
                    
                    if user_team_possible:
                        # User can only be assigned if their team is chosen
                        self.model += (var <= pulp.lpSum(user_team_possible),
                                     f'team_assign_{step}_{user}')
                    else:
                        # User cannot be assigned if not in any team
                        self.model += (var == 0,
                                     f'team_forbid_{step}_{user}')
        return True

class PuLPSUALConstraint(PuLPConstraint):
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

    def add_to_model(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for scope, h, super_users in self.instance.sual:
            for step in scope:
                step_vars = [var for _, var in self.var_manager.get_step_variables(step)]
                super_vars = [var for user, var in self.var_manager.get_step_variables(step)
                            if user in super_users]
                
                if step_vars:
                    condition = pulp.LpVariable(
                        f'sual_cond_{step}',
                        cat='Binary'
                    )
                    
                    M = len(step_vars)  # Big-M value
                    assign_sum = pulp.lpSum(step_vars)
                    
                    # condition = 1 iff assign_sum <= h
                    self.model += (assign_sum - h <= M * (1 - condition),
                                 f'sual_cond1_{step}')
                    self.model += (assign_sum - h >= -M * condition - 0.1,
                                 f'sual_cond2_{step}')
                    
                    # If condition true, must use a super user
                    if super_vars:
                        self.model += (pulp.lpSum(super_vars) >= condition,
                                     f'sual_enforce_{step}')
                        
        return True

class PuLPWangLiConstraint(PuLPConstraint):
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

    def add_to_model(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for scope, departments in self.instance.wang_li:
            # Create department choice variables
            dept_vars = []
            for i in range(len(departments)):
                dept_var = pulp.LpVariable(
                    f'dept_{len(self.model.constraints)}_{i}',
                    cat='Binary'
                )
                dept_vars.append(dept_var)
            
            # Exactly one department must be chosen
            self.model += (pulp.lpSum(dept_vars) == 1,
                         f'dept_choice_{len(self.model.constraints)}')
            
            # For each step in scope
            for step in scope:
                for user, var in self.var_manager.get_step_variables(step):
                    # For each department
                    user_dept_possible = []
                    for dept_idx, dept in enumerate(departments):
                        if user in dept:
                            user_dept_possible.append(dept_vars[dept_idx])
                    
                    if user_dept_possible:
                        # User can only be assigned if their department is chosen
                        self.model += (var <= pulp.lpSum(user_dept_possible),
                                     f'dept_assign_{step}_{user}')
                    else:
                        # User cannot be assigned if not in any department
                        self.model += (var == 0,
                                     f'dept_forbid_{step}_{user}')
        return True

class PuLPAssignmentDependentConstraint(PuLPConstraint):
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

    def add_to_model(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for s1, s2, source_users, target_users in self.instance.ada:
            # Get variables for source step with source users
            source_vars = self.var_manager.get_user_step_variables_filtered(s1, source_users)
            if not source_vars:
                continue
                
            # Get variables for target step with target users
            target_vars = self.var_manager.get_user_step_variables_filtered(s2, target_users)
            if not target_vars:
                continue
                
            # Binary variable to indicate if any source user is assigned
            source_used = pulp.LpVariable(
                f'ada_source_{s1}_{s2}',
                cat='Binary'
            )
            
            # Link source_used to source assignments
            M = len(source_vars)  # Big-M value
            self.model += (pulp.lpSum(var[1] for var in source_vars) <= M * source_used,
                         f'ada_source_used1_{s1}_{s2}')
            self.model += (pulp.lpSum(var[1] for var in source_vars) >= source_used,
                         f'ada_source_used2_{s1}_{s2}')
            
            # If source used, must assign to target user
            if target_vars:
                self.model += (pulp.lpSum(var[1] for var in target_vars) >= source_used,
                             f'ada_target_used_{s1}_{s2}')
            
            # When source used, non-target users cannot be assigned
            for user, var in self.var_manager.get_step_variables(s2):
                if user not in target_users:
                    self.model += (var <= 1 - source_used,
                                 f'ada_non_target_{s1}_{s2}_{user}')
                    
        return True

class PuLPConstraintManager:
    """Manages PuLP solver constraints"""
    def __init__(self, model: pulp.LpProblem, instance, var_manager: PuLPVariableManager):
        self.model = model
        self.instance = instance
        self.var_manager = var_manager
        
        # Initialize all constraints
        self.constraints = {
            'authorization': PuLPAuthorizationConstraint(model, instance, var_manager),
            'binding_of_duty': PuLPBindingOfDutyConstraint(model, instance, var_manager),
            'separation_of_duty': PuLPSeparationOfDutyConstraint(model, instance, var_manager),
            'at_most_k': PuLPAtMostKConstraint(model, instance, var_manager),
            'one_team': PuLPOneTeamConstraint(model, instance, var_manager),
            'super_user_at_least': PuLPSUALConstraint(model, instance, var_manager),
            'wang_li': PuLPWangLiConstraint(model, instance, var_manager),
            'assignment_dependent': PuLPAssignmentDependentConstraint(model, instance, var_manager)
        }

    def add_constraints(self, active_constraints: dict) -> Tuple[bool, List[str]]:
        """Add active constraints to the model"""
        errors = []
        
        for name, constraint in self.constraints.items():
            if active_constraints.get(name, True):
                # Check if constraint type exists in instance
                has_constraints = (
                    (name == 'super_user_at_least' and hasattr(self.instance, 'sual') and self.instance.sual) or
                    (name == 'wang_li' and hasattr(self.instance, 'wang_li') and self.instance.wang_li) or
                    (name == 'assignment_dependent' and hasattr(self.instance, 'ada') and self.instance.ada) or
                    (name in ['authorization', 'binding_of_duty', 'separation_of_duty', 'at_most_k', 'one_team'])
                )
                
                if has_constraints:
                    is_feasible, constraint_errors = constraint.check_feasibility()
                    if not is_feasible:
                        errors.extend(constraint_errors)
                        continue
                        
                    if not constraint.add_to_model():
                        errors.append(f"Failed to add {name} constraints to PuLP model")
                    
        return len(errors) == 0, errors
