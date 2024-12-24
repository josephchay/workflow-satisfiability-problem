from abc import ABC, abstractmethod
from collections import defaultdict
from ortools.sat.python import cp_model
from typing import List, Tuple, Set, Dict


class VariableManager:
    """Manages CP-SAT variables for the WSP problem"""
    def __init__(self, model: cp_model.CpModel, instance):
        self.model = model
        self.instance = instance
        self.step_variables: Dict[int, List[Tuple[int, cp_model.IntVar]]] = {}
        self.user_step_variables: Dict[int, Dict[int, cp_model.IntVar]] = defaultdict(dict)
        self._initialized = False
        self.user_sets = {}
        
    def create_variables(self) -> bool:
        """
        Create boolean variables for user-step assignments.
        Returns True if variables were created successfully.
        """
        try:
            self.step_variables.clear()
            self.user_step_variables.clear()
            
            # Create variables only for authorized user-step pairs
            for step in range(self.instance.number_of_steps):
                self.step_variables[step] = []
                for user in range(self.instance.number_of_users):
                    if self.instance.user_step_matrix[user][step]:
                        var = self.model.NewBoolVar(f's{step + 1}_u{user + 1}')
                        self.step_variables[step].append((user, var))
                        self.user_step_variables[user][step] = var
                        
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Error creating variables: {str(e)}")
            return False
            
    def get_step_variables(self, step: int) -> List[Tuple[int, cp_model.IntVar]]:
        """Get list of (user, variable) pairs for a step"""
        self._check_initialized()
        return self.step_variables.get(step, [])
        
    def get_user_variables(self, user: int) -> Dict[int, cp_model.IntVar]:
        """Get dictionary of {step: variable} for a user"""
        self._check_initialized()
        return self.user_step_variables[user]
        
    def get_user_step_variable(self, user: int, step: int) -> cp_model.IntVar:
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
                
    def has_variable(self, user: int, step: int) -> bool:
        """Check if variable exists for user-step pair"""
        return step in self.user_step_variables[user]
        
    def _check_initialized(self):
        """Ensure variables have been created"""
        if not self._initialized:
            raise RuntimeError("Variables not initialized. Call create_variables() first.")
        
    def get_assignment_from_solution(self, solver: cp_model.CpSolver) -> Dict[int, int]:
        """
        Extract step -> user assignment from solver solution
        Returns dictionary mapping step numbers (1-based) to user numbers (1-based)
        """
        self._check_initialized()
        
        assignment = {}
        for step in range(self.instance.number_of_steps):
            for user, var in self.step_variables[step]:
                if solver.Value(var):
                    assignment[step + 1] = user + 1
                    break
                    
        return assignment
    
    def get_user_count_for_step(self, step: int) -> int:
        """Get number of authorized users for a step"""
        return len(self.get_authorized_users(step))
    
    def get_department_authorized_users(self, step: int, department: Set[int]) -> Set[int]:
        """Get users from a specific department authorized for a step"""
        return self.get_authorized_users(step) & department
        
    def get_user_step_variables_filtered(self, step: int, user_set: Set[int]) -> List[Tuple[int, cp_model.IntVar]]:
        """Get variables for a step filtered by a specific set of users"""
        return [(user, var) for user, var in self.step_variables[step] 
                if user in user_set]


class BaseConstraint(ABC):
    """Abstract base class for all WSP constraints"""
    def __init__(self, model, instance, var_manager):
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


class AuthorizationConstraint(BaseConstraint):
    """Ensures each step is assigned to exactly one authorized user"""
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
            self.model.AddExactlyOne(var for _, var in user_vars)
        return True


class BindingOfDutyConstraint(BaseConstraint):
    """Ensures specified steps are assigned to the same user"""
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        infeasible = []
        for s1, s2 in self.instance.BOD:
            common_users = self._get_common_users(s1, s2)
            if not common_users:
                infeasible.append((s1 + 1, s2 + 1))
                
        return (len(infeasible) == 0,
                [f"No users authorized for both steps {s1} and {s2}" 
                 for s1, s2 in infeasible])

    def _get_common_users(self, s1: int, s2: int) -> Set[int]:
        """Get users authorized for both steps"""
        return {user for user in range(self.instance.number_of_users)
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2])}

    def add_to_model(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for s1, s2 in self.instance.BOD:
            s1_vars = []
            s2_vars = []
            
            for user in range(self.instance.number_of_users):
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    self.model.Add(var1 == var2)
                    s1_vars.append(var1)
                    s2_vars.append(var2)
            
            self.model.Add(sum(s1_vars) == 1)
            self.model.Add(sum(s2_vars) == 1)
            
        return True


class SeparationOfDutyConstraint(BaseConstraint):
    """Ensures specified steps are assigned to different users"""
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        # SOD constraints are always potentially feasible if there are at least 
        # two authorized users across both steps
        return True, []

    def add_to_model(self) -> bool:
        for s1, s2 in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                if (s1 in self.var_manager.user_step_variables[user] and 
                    s2 in self.var_manager.user_step_variables[user]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    self.model.Add(var1 + var2 <= 1)
        return True


class AtMostKConstraint(BaseConstraint):
    """Ensures users are not assigned more than k steps from specified groups"""
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
                    self.model.Add(sum(user_step_vars) <= k)
        
        # Add global limit based on minimum k
        if self.instance.at_most_k:
            min_k = min(k for k, _ in self.instance.at_most_k)
            for user in range(self.instance.number_of_users):
                user_vars = []
                for step in range(self.instance.number_of_steps):
                    if step in self.var_manager.user_step_variables[user]:
                        user_vars.append(self.var_manager.user_step_variables[user][step])
                if user_vars:
                    self.model.Add(sum(user_vars) <= min_k)
                    
        return True


class OneTeamConstraint(BaseConstraint):
    """Ensures steps are assigned to users from the same team"""
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        # One team constraints are always potentially feasible if teams are non-empty
        return True, []

    def add_to_model(self) -> bool:
        for steps, teams in self.instance.one_team:
            team_vars = [self.model.NewBoolVar(f'team_{i}') 
                        for i in range(len(teams))]
            self.model.AddExactlyOne(team_vars)
            
            for step in steps:
                for team_idx, team in enumerate(teams):
                    team_var = team_vars[team_idx]
                    for user, var in self.var_manager.step_variables[step]:
                        if user not in team:
                            self.model.Add(var == 0).OnlyEnforceIf(team_var)
        return True


"""NEW ADDITIONAL CONSTRAINTS"""


class SUALConstraint(BaseConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        errors = []
        
        for scope, h, super_users in self.instance.sual:
            # Check each step in scope has either:
            # 1. More than h authorized users, or
            # 2. At least one authorized super user
            for step in scope:
                authorized = self.var_manager.get_authorized_users(step)
                if len(authorized) <= h:
                    super_auth = authorized.intersection(super_users)
                    if not super_auth:
                        errors.append(
                            f"Step {step+1} must have either >{h} authorized users "
                            f"or at least one authorized super user"
                        )
                        
            # Verify at least one super user is authorized for all steps in scope
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
            # For each step in scope
            for step in scope:
                # Get all users assigned to this step
                step_vars = [var for _, var in self.var_manager.get_step_variables(step)]
                
                # Get super users assigned to this step
                super_vars = [var for user, var in self.var_manager.get_step_variables(step)
                            if user in super_users]
                
                # Create indicator for when total assignments <= h
                condition = self.model.NewBoolVar(f'sual_cond_{step}')
                self.model.Add(sum(step_vars) <= h).OnlyEnforceIf(condition)
                self.model.Add(sum(step_vars) > h).OnlyEnforceIf(condition.Not())
                
                # If condition true, must use a super user
                if super_vars:
                    self.model.AddBoolOr(super_vars).OnlyEnforceIf(condition)
                
        return True


class WangLiConstraint(BaseConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        errors = []
        
        for scope, departments in self.instance.wang_li:
            # For each department, check if it can handle all steps
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
            dept_vars = [self.model.NewBoolVar(f'dept_{i}') 
                        for i in range(len(departments))]
            
            # Exactly one department must be chosen
            self.model.AddExactlyOne(dept_vars)
            
            # For each step in scope
            for step in scope:
                # For each user-step assignment
                for user, var in self.var_manager.get_step_variables(step):
                    # For each department
                    user_dept_assignments = []
                    for dept_idx, dept in enumerate(departments):
                        if user in dept:
                            # User can be assigned if their department is chosen
                            user_dept_assignments.append(dept_vars[dept_idx])
                    
                    # User can only be assigned if they're in the chosen department
                    if user_dept_assignments:
                        self.model.AddImplication(var, self.model.AddBoolOr(user_dept_assignments))
                    else:
                        self.model.Add(var == 0)  # User cannot be assigned
                        
        return True
    

class AssignmentDependentConstraint(BaseConstraint):
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
                
            # Create an indicator for when a source user is assigned
            source_assigned = self.model.NewBoolVar(f'ada_{s1}_{s2}')
            self.model.Add(sum(var for _, var in source_vars) >= 1).OnlyEnforceIf(source_assigned)
            self.model.Add(sum(var for _, var in source_vars) == 0).OnlyEnforceIf(source_assigned.Not())
            
            # If source assigned, must use target user
            self.model.Add(sum(var for _, var in target_vars) >= 1).OnlyEnforceIf(source_assigned)
            
            # Non-target users cannot be assigned when source is assigned
            for user, var in self.var_manager.get_step_variables(s2):
                if user not in target_users:
                    self.model.Add(var == 0).OnlyEnforceIf(source_assigned)
                    
        return True


class ConstraintManager:
    """Manages WSP constraints using individual constraint classes"""
    def __init__(self, model, instance, var_manager):
        self.model = model
        self.instance = instance
        self.var_manager = var_manager
        
        # Initialize all constraints
        self.constraints = {
            'authorization': AuthorizationConstraint(model, instance, var_manager),
            'binding_of_duty': BindingOfDutyConstraint(model, instance, var_manager),
            'separation_of_duty': SeparationOfDutyConstraint(model, instance, var_manager),
            'at_most_k': AtMostKConstraint(model, instance, var_manager),
            'one_team': OneTeamConstraint(model, instance, var_manager),
            'super_user_at_least': SUALConstraint(model, instance, var_manager),
            'wang_li': WangLiConstraint(model, instance, var_manager),
            'assignment_dependent': AssignmentDependentConstraint(model, instance, var_manager)
        }
        
    def add_constraints(self, active_constraints: dict) -> Tuple[bool, List[str]]:
        """Add active constraints to the model"""
        errors = []
        
        for name, constraint in self.constraints.items():
            # Only add if constraint is active and exists in instance
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
                        errors.append(f"Failed to add {name} constraints to model")
                    
        return len(errors) == 0, errors
