from typing import List, Tuple, Dict, Set
from abc import ABC, abstractmethod
from collections import defaultdict
import z3


class Z3VariableManager:
    """Manages Z3 variables for the WSP problem"""
    def __init__(self, solver: z3.Solver, instance):
        self.solver = solver
        self.instance = instance
        self.step_variables: Dict[int, List[Tuple[int, z3.BoolRef]]] = {}
        self.user_step_variables: Dict[int, Dict[int, z3.BoolRef]] = defaultdict(dict)
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
                        var = z3.Bool(f's{step + 1}_u{user + 1}')
                        self.step_variables[step].append((user, var))
                        self.user_step_variables[user][step] = var
                        
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Error creating Z3 variables: {str(e)}")
            return False

    def get_step_variables(self, step: int) -> List[Tuple[int, z3.BoolRef]]:
        """Get list of (user, variable) pairs for a step"""
        self._check_initialized()
        return self.step_variables.get(step, [])

    def get_user_variables(self, user: int) -> Dict[int, z3.BoolRef]:
        """Get dictionary of {step: variable} for a user"""
        self._check_initialized()
        return self.user_step_variables[user]

    def get_user_step_variable(self, user: int, step: int) -> z3.BoolRef:
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
        
    def has_variable(self, user: int, step: int) -> bool:
        """Check if variable exists for user-step pair"""
        return step in self.user_step_variables[user]

    def get_user_step_variables_filtered(self, step: int, user_set: Set[int]) -> List[Tuple[int, z3.BoolRef]]:
        """Get variables for a step filtered by a specific set of users"""
        return [(user, var) for user, var in self.step_variables[step] 
                if user in user_set]

    def _check_initialized(self):
        """Ensure variables have been created"""
        if not self._initialized:
            raise RuntimeError("Variables not initialized. Call create_variables() first.")

    def get_assignment_from_model(self, model: z3.ModelRef) -> Dict[int, int]:
        """Extract step -> user assignment from solver model"""
        self._check_initialized()
        
        assignment = {}
        for step in range(self.instance.number_of_steps):
            for user, var in self.step_variables[step]:
                if z3.is_true(model[var]):
                    assignment[step + 1] = user + 1
                    break
        return assignment


class Z3Constraint(ABC):
    """Base class for Z3 constraints"""
    def __init__(self, solver: z3.Solver, instance, var_manager: Z3VariableManager):
        self.solver = solver
        self.instance = instance
        self.var_manager = var_manager

    @abstractmethod
    def add_to_solver(self) -> bool:
        """Add constraint to the solver. Returns False if infeasible."""
        pass

    @abstractmethod
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        """Check if constraint can potentially be satisfied."""
        pass


class Z3ConstraintManager:
    """Manages Z3 solver constraints"""
    def __init__(self, solver: z3.Solver, instance, var_manager: Z3VariableManager):
        self.solver = solver
        self.instance = instance
        self.var_manager = var_manager
        
        # Initialize all constraints - using Z3 versions
        self.constraints = {
            'authorization': Z3AuthorizationConstraint(solver, instance, var_manager),
            'binding_of_duty': Z3BindingOfDutyConstraint(solver, instance, var_manager),
            'separation_of_duty': Z3SeparationOfDutyConstraint(solver, instance, var_manager),
            'at_most_k': Z3AtMostKConstraint(solver, instance, var_manager),
            'one_team': Z3OneTeamConstraint(solver, instance, var_manager),
            'super_user_at_least': Z3SUALConstraint(solver, instance, var_manager),
            'wang_li': Z3WangLiConstraint(solver, instance, var_manager),
            'assignment_dependent': Z3AssignmentDependentConstraint(solver, instance, var_manager)
        }

    def add_constraints(self, active_constraints: dict) -> Tuple[bool, List[str]]:
        """Add active constraints to the solver"""
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
                        
                    if not constraint.add_to_solver():
                        errors.append(f"Failed to add {name} constraints to Z3 solver")
                    
        return len(errors) == 0, errors

# Individual Z3 Constraint Classes
class Z3AuthorizationConstraint(Z3Constraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        infeasible_steps = []
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                infeasible_steps.append(step + 1)
                
        return (len(infeasible_steps) == 0, 
                [f"No authorized users for step {step}" for step in infeasible_steps])

    def add_to_solver(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for step, user_vars in self.var_manager.step_variables.items():
            # Exactly one user per step
            self.solver.add(z3.PbEq([(var, 1) for _, var in user_vars], 1))
        return True

class Z3BindingOfDutyConstraint(Z3Constraint):
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

    def add_to_solver(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for s1, s2 in self.instance.BOD:
            for user in range(self.instance.number_of_users):
                if (s1 in self.var_manager.user_step_variables[user] and 
                    s2 in self.var_manager.user_step_variables[user]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    self.solver.add(var1 == var2)
        return True

class Z3SeparationOfDutyConstraint(Z3Constraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []

    def add_to_solver(self) -> bool:
        for s1, s2 in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                if (s1 in self.var_manager.user_step_variables[user] and 
                    s2 in self.var_manager.user_step_variables[user]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    self.solver.add(z3.Not(z3.And(var1, var2)))
        return True

class Z3AtMostKConstraint(Z3Constraint):
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

    def add_to_solver(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for k, steps in self.instance.at_most_k:
            for user in range(self.instance.number_of_users):
                user_step_vars = []
                for step in steps:
                    if step in self.var_manager.user_step_variables[user]:
                        user_step_vars.append(self.var_manager.user_step_variables[user][step])
                
                if user_step_vars:
                    self.solver.add(z3.PbLe([(var, 1) for var in user_step_vars], k))
        
        # Add global limit based on minimum k
        if self.instance.at_most_k:
            min_k = min(k for k, _ in self.instance.at_most_k)
            for user in range(self.instance.number_of_users):
                user_vars = []
                for step in range(self.instance.number_of_steps):
                    if step in self.var_manager.user_step_variables[user]:
                        user_vars.append(self.var_manager.user_step_variables[user][step])
                if user_vars:
                    self.solver.add(z3.PbLe([(var, 1) for var in user_vars], min_k))
                    
        return True

class Z3OneTeamConstraint(Z3Constraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []

    def add_to_solver(self) -> bool:
        for steps, teams in self.instance.one_team:
            # Create team choice variables
            team_vars = [z3.Bool(f'team_{len(self.solver.assertions())}_{i}') 
                        for i in range(len(teams))]
            
            # Exactly one team must be chosen
            self.solver.add(z3.PbEq([(var, 1) for var in team_vars], 1))
            
            for step in steps:
                for user, var in self.var_manager.get_step_variables(step):
                    # User can only be assigned if they're in the chosen team
                    user_team_assignments = []
                    for team_idx, team in enumerate(teams):
                        if user in team:
                            user_team_assignments.append(team_vars[team_idx])
                    
                    if user_team_assignments:
                        self.solver.add(z3.Implies(var, z3.Or(user_team_assignments)))
                    else:
                        self.solver.add(z3.Not(var))
        return True

class Z3SUALConstraint(Z3Constraint):
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

    def add_to_solver(self) -> bool:
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
                
                # Create condition for when total assignments <= h
                if step_vars:
                    # Count total assignments for this step
                    step_count = z3.Sum([z3.If(var, 1, 0) for var in step_vars])
                    
                    # Add constraint: if step_count <= h, must use super user
                    condition = step_count <= h
                    if super_vars:
                        self.solver.add(z3.Implies(condition, z3.Or(super_vars)))
                        
        return True

class Z3WangLiConstraint(Z3Constraint):
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

    def add_to_solver(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for scope, departments in self.instance.wang_li:
            # Create department choice variables
            dept_vars = [z3.Bool(f'dept_{len(self.solver.assertions())}_{i}') 
                        for i in range(len(departments))]
            
            # Exactly one department must be chosen
            self.solver.add(z3.PbEq([(var, 1) for var in dept_vars], 1))
            
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
                        self.solver.add(z3.Implies(var, z3.Or(user_dept_assignments)))
                    else:
                        self.solver.add(z3.Not(var))
                        
        return True

class Z3AssignmentDependentConstraint(Z3Constraint):
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

    def add_to_solver(self) -> bool:
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
                
            # Create indicator for any source user being assigned
            source_used = z3.Bool(f'ada_source_{s1}_{s2}')
            source_count = z3.Sum([z3.If(var[1], 1, 0) for var in source_vars])
            
            # Define when source is used (when any source user is assigned)
            self.solver.add(source_used == (source_count > 0))
            
            # If source used, must assign to target user
            if target_vars:
                self.solver.add(z3.Implies(source_used, 
                                         z3.Or([var[1] for var in target_vars])))
            
            # When source used, non-target users cannot be assigned
            for user, var in self.var_manager.get_step_variables(s2):
                if user not in target_users:
                    self.solver.add(z3.Implies(source_used, z3.Not(var)))
                    
        return True
