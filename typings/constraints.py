from abc import ABC, abstractmethod
from typing import Protocol, List, Tuple, Any, Set, Dict
from collections import defaultdict
import z3
from ortools.sat.python import cp_model


class Solver(Protocol):
    """Protocol defining solver interface"""
    def add(self, constraint: Any) -> None:
        """Add constraint to solver"""
        pass


class Variable(Protocol):
    """Protocol defining variable interface"""
    pass


class VariableManagerBase(ABC):
    """Abstract base class for variable managers"""
    def __init__(self, instance):
        self.instance = instance
        self.step_variables = {}
        self.user_step_variables = defaultdict(dict)
        self._initialized = False
        self.user_sets = {}

    @abstractmethod
    def create_variables(self) -> bool:
        """Create solver variables"""
        pass
        
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
    """Abstract base constraint class usable by any solver"""
    
    @abstractmethod
    def add_to_solver(self, solver: Solver, var_manager: VariableManagerBase) -> bool:
        """Add constraint to solver"""
        pass
        
    @abstractmethod
    def check_feasibility(self, var_manager: VariableManagerBase) -> Tuple[bool, List[str]]:
        """Check if constraint can potentially be satisfied"""
        pass


class CPSATVariableManager(VariableManagerBase):
    """Concrete CPSAT implementations"""
    def __init__(self, model: cp_model.CpModel, instance):
        super().__init__(instance)
        self.model = model
        
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
        except Exception:
            return False


class Z3VariableManager:
    """Manages Z3 variables and assignments"""
    def __init__(self, solver: z3.Solver, instance):
        self.solver = solver
        self.instance = instance
        self.step_variables = {}
        self.user_step_variables = defaultdict(dict)
        self._initialized = False
        
    def create_variables(self) -> bool:
        """Create Z3 boolean variables for user-step assignments"""
        try:
            self.step_variables.clear()
            self.user_step_variables.clear()
            
            for step in range(self.instance.number_of_steps):
                self.step_variables[step] = []
                for user in range(self.instance.number_of_users):
                    if self.instance.user_step_matrix[user][step]:
                        var = z3.Bool(f's{step + 1}_u{user + 1}')
                        self.step_variables[step].append((user, var))
                        self.user_step_variables[user][step] = var
                        
            self._initialized = True
            return True
        except Exception:
            return False

    def get_assignment_from_model(self, model: z3.ModelRef) -> Dict[int, int]:
        """Extract step -> user assignment from model"""
        assignment = {}
        for step in range(self.instance.number_of_steps):
            for user, var in self.step_variables[step]:
                if z3.is_true(model[var]):
                    assignment[step + 1] = user + 1
                    break
        return assignment


class CPSATConstraintManager:
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


class Z3ConstraintManager:
    """Manages Z3 constraints"""
    def __init__(self, solver: z3.Solver, instance, var_manager: Z3VariableManager):
        self.solver = solver
        self.instance = instance
        self.var_manager = var_manager
        
        # Initialize all constraint classes
        self.constraints = {
            'authorization': AuthorizationConstraint(),
            'binding_of_duty': BindingOfDutyConstraint(), 
            'separation_of_duty': SeparationOfDutyConstraint(),
            'at_most_k': AtMostKConstraint(),
            'one_team': OneTeamConstraint(),
            'super_user_at_least': SUALConstraint(),
            'wang_li': WangLiConstraint(),
            'assignment_dependent': AssignmentDependentConstraint()
        }

    def add_constraints(self, active_constraints: Dict[str, bool]) -> Tuple[bool, List[str]]:
        """Add active constraints to solver"""
        errors = []
        
        for name, constraint in self.constraints.items():
            if active_constraints.get(name, True):
                has_constraints = (
                    (name == 'super_user_at_least' and hasattr(self.instance, 'sual') and self.instance.sual) or
                    (name == 'wang_li' and hasattr(self.instance, 'wang_li') and self.instance.wang_li) or
                    (name == 'assignment_dependent' and hasattr(self.instance, 'ada') and self.instance.ada) or
                    (name in ['authorization', 'binding_of_duty', 'separation_of_duty', 'at_most_k', 'one_team'])
                )
                
                if has_constraints:
                    is_feasible, constraint_errors = constraint.check_feasibility(self.var_manager)
                    if not is_feasible:
                        errors.extend(constraint_errors)
                        continue
                        
                    if not constraint.add_to_solver(self.solver, self.var_manager):
                        errors.append(f"Failed to add {name} constraints to model")
                    
        return len(errors) == 0, errors


class AuthorizationConstraint(BaseConstraint):
    def check_feasibility(self, var_manager: VariableManagerBase) -> Tuple[bool, List[str]]:
        # Common feasibility check logic
        infeasible_steps = []
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                infeasible_steps.append(step + 1)
                
        return (len(infeasible_steps) == 0, 
                [f"No authorized users for step {step}" for step in infeasible_steps])

    def add_to_solver(self, solver: Solver, var_manager: VariableManagerBase) -> bool:
        is_feasible, errors = self.check_feasibility(var_manager)
        if not is_feasible:
            return False
            
        # Add solver-specific constraints
        if isinstance(solver, cp_model.CpModel):
            self._add_to_cpsat(solver, var_manager)
        elif isinstance(solver, z3.Solver):
            self._add_to_z3(solver, var_manager)
            
        return True
        
    def _add_to_cpsat(self, model: cp_model.CpModel, var_manager: CPSATVariableManager):
        for step, user_vars in var_manager.step_variables.items():
            model.AddExactlyOne(var for _, var in user_vars)
            
    def _add_to_z3(self, solver: z3.Solver, var_manager: Z3VariableManager):
        for step, user_vars in var_manager.step_variables.items():
            # At least one user
            solver.add(z3.Or([var for _, var in user_vars]))
            # At most one user 
            for i, (_, var1) in enumerate(user_vars):
                for var2 in (v for _, v in user_vars[i+1:]):
                    solver.add(z3.Not(z3.And(var1, var2)))


class BindingOfDutyConstraint(BaseConstraint):
    def check_feasibility(self, var_manager: VariableManagerBase) -> Tuple[bool, List[str]]:
        infeasible = []
        for s1, s2 in var_manager.instance.BOD:
            common_users = set(var_manager.get_authorized_users(s1)) & set(var_manager.get_authorized_users(s2))
            if not common_users:
                infeasible.append((s1 + 1, s2 + 1))
                
        return (len(infeasible) == 0,
                [f"No users authorized for both steps {s1} and {s2}" for s1, s2 in infeasible])

    def add_to_solver(self, solver: Solver, var_manager: VariableManagerBase) -> bool:
        is_feasible, errors = self.check_feasibility(var_manager)
        if not is_feasible:
            return False

        if isinstance(solver, cp_model.CpModel):
            self._add_to_cpsat(solver, var_manager)
        elif isinstance(solver, z3.Solver):
            self._add_to_z3(solver, var_manager)
        return True

    def _add_to_cpsat(self, model: cp_model.CpModel, var_manager: CPSATVariableManager):
        for s1, s2 in var_manager.instance.BOD:
            s1_vars = []
            s2_vars = []
            for user in range(var_manager.instance.number_of_users):
                if (s1 in var_manager.user_step_variables[user] and 
                    s2 in var_manager.user_step_variables[user]):
                    var1 = var_manager.user_step_variables[user][s1]
                    var2 = var_manager.user_step_variables[user][s2]
                    model.Add(var1 == var2)
                    s1_vars.append(var1)
                    s2_vars.append(var2)
            model.Add(sum(s1_vars) == 1)
            model.Add(sum(s2_vars) == 1)

    def _add_to_z3(self, solver: z3.Solver, var_manager: Z3VariableManager):
        for s1, s2 in var_manager.instance.BOD:
            common_users = []
            for user in range(var_manager.instance.number_of_users):
                if (s1 in var_manager.user_step_variables[user] and 
                    s2 in var_manager.user_step_variables[user]):
                    var1 = var_manager.user_step_variables[user][s1]
                    var2 = var_manager.user_step_variables[user][s2]
                    solver.add(var1 == var2)
                    common_users.append(var1)
            if common_users:
                solver.add(z3.PbEq([(v, 1) for v in common_users], 1))


class SeparationOfDutyConstraint(BaseConstraint):
    def check_feasibility(self, var_manager: VariableManagerBase) -> Tuple[bool, List[str]]:
        return True, []

    def add_to_solver(self, solver: Solver, var_manager: VariableManagerBase) -> bool:
        if isinstance(solver, cp_model.CpModel):
            self._add_to_cpsat(solver, var_manager)
        elif isinstance(solver, z3.Solver):
            self._add_to_z3(solver, var_manager)
        return True

    def _add_to_cpsat(self, model: cp_model.CpModel, var_manager: CPSATVariableManager):
        for s1, s2 in var_manager.instance.SOD:
            for user in range(var_manager.instance.number_of_users):
                if (s1 in var_manager.user_step_variables[user] and 
                    s2 in var_manager.user_step_variables[user]):
                    var1 = var_manager.user_step_variables[user][s1]
                    var2 = var_manager.user_step_variables[user][s2]
                    model.Add(var1 + var2 <= 1)

    def _add_to_z3(self, solver: z3.Solver, var_manager: Z3VariableManager):
        for s1, s2 in var_manager.instance.SOD:
            for user in range(var_manager.instance.number_of_users):
                if (s1 in var_manager.user_step_variables[user] and 
                    s2 in var_manager.user_step_variables[user]):
                    var1 = var_manager.user_step_variables[user][s1]
                    var2 = var_manager.user_step_variables[user][s2]
                    solver.add(z3.Not(z3.And(var1, var2)))


class AtMostKConstraint(BaseConstraint):
    def check_feasibility(self, var_manager: VariableManagerBase) -> Tuple[bool, List[str]]:
        infeasible = []
        for k, steps in var_manager.instance.at_most_k:
            total_users = len(set().union(*[var_manager.get_authorized_users(s) for s in steps]))
            min_users_needed = len(steps) / k
            if total_users < min_users_needed:
                infeasible.append((k, steps, total_users, min_users_needed))
                
        return (len(infeasible) == 0,
                [f"At-most-{k} constraint on steps {[s+1 for s in steps]} requires "
                 f"at least {min_needed:.0f} users but only has {total}" 
                 for k, steps, total, min_needed in infeasible])

    def add_to_solver(self, solver: Solver, var_manager: VariableManagerBase) -> bool:
        is_feasible, errors = self.check_feasibility(var_manager)
        if not is_feasible:
            return False

        if isinstance(solver, cp_model.CpModel):
            self._add_to_cpsat(solver, var_manager)
        elif isinstance(solver, z3.Solver):
            self._add_to_z3(solver, var_manager)
        return True

    def _add_to_cpsat(self, model: cp_model.CpModel, var_manager: CPSATVariableManager):
        for k, steps in var_manager.instance.at_most_k:
            for user in range(var_manager.instance.number_of_users):
                user_step_vars = []
                for step in steps:
                    if step in var_manager.user_step_variables[user]:
                        user_step_vars.append(var_manager.user_step_variables[user][step])
                if user_step_vars:
                    model.Add(sum(user_step_vars) <= k)

    def _add_to_z3(self, solver: z3.Solver, var_manager: Z3VariableManager):
        for k, steps in var_manager.instance.at_most_k:
            for user in range(var_manager.instance.number_of_users):
                user_step_vars = []
                for step in steps:
                    if step in var_manager.user_step_variables[user]:
                        user_step_vars.append(var_manager.user_step_variables[user][step])
                if user_step_vars:
                    solver.add(z3.PbLe([(v, 1) for v in user_step_vars], k))


class OneTeamConstraint(BaseConstraint):
    def check_feasibility(self, var_manager: VariableManagerBase) -> Tuple[bool, List[str]]:
        if not hasattr(var_manager.instance, 'one_team'):
            return True, []
            
        errors = []
        for idx, (steps, teams) in enumerate(var_manager.instance.one_team):
            for team_idx, team in enumerate(teams):
                authorized = False
                for step in steps:
                    if any(var_manager.instance.user_step_matrix[user][step] for user in team):
                        authorized = True
                        break
                if not authorized:
                    errors.append(f"Team {team_idx + 1} has no authorized users for any step in scope {[s+1 for s in steps]}")
        return len(errors) == 0, errors

    def add_to_solver(self, solver: Solver, var_manager: VariableManagerBase) -> bool:
        if not hasattr(var_manager.instance, 'one_team'):
            return True
            
        is_feasible, errors = self.check_feasibility(var_manager)
        if not is_feasible:
            return False

        if isinstance(solver, cp_model.CpModel):
            self._add_to_cpsat(solver, var_manager)
        elif isinstance(solver, z3.Solver):
            self._add_to_z3(solver, var_manager)
        return True

    def _add_to_cpsat(self, model: cp_model.CpModel, var_manager: CPSATVariableManager):
        for steps, teams in var_manager.instance.one_team:
            team_vars = [model.NewBoolVar(f'team_{i}') for i in range(len(teams))]
            model.AddExactlyOne(team_vars)
            
            for step in steps:
                for team_idx, team in enumerate(teams):
                    team_var = team_vars[team_idx]
                    for user, var in var_manager.step_variables[step]:
                        if user not in team:
                            model.Add(var == 0).OnlyEnforceIf(team_var)

    def _add_to_z3(self, solver: z3.Solver, var_manager: Z3VariableManager):
        for steps, teams in var_manager.instance.one_team:
            team_vars = [z3.Bool(f'team_{len(solver.assertions())}_{i}') for i in range(len(teams))]
            # Exactly one team
            solver.add(z3.PbEq([(v, 1) for v in team_vars], 1))
            
            for step in steps:
                for team_idx, team in enumerate(teams):
                    team_var = team_vars[team_idx]
                    for user, var in var_manager.step_variables[step]:
                        if user not in team:
                            solver.add(z3.Implies(team_var, z3.Not(var)))


class SUALConstraint(BaseConstraint):
    def check_feasibility(self, var_manager: VariableManagerBase) -> Tuple[bool, List[str]]:
        if not hasattr(var_manager.instance, 'sual'):
            return True, []
            
        errors = []
        for scope, h, super_users in var_manager.instance.sual:
            authorized_super_users = set(super_users)
            for step in scope:
                authorized_super_users &= var_manager.get_authorized_users(step)
            if len(authorized_super_users) < h:
                errors.append(f"Only {len(authorized_super_users)} super users authorized for all steps "
                            f"{[s+1 for s in scope]}, but {h} required")
        return len(errors) == 0, errors

    def add_to_solver(self, solver: Solver, var_manager: VariableManagerBase) -> bool:
        if not hasattr(var_manager.instance, 'sual'):
            return True
            
        is_feasible, errors = self.check_feasibility(var_manager)
        if not is_feasible:
            return False

        if isinstance(solver, cp_model.CpModel):
            self._add_to_cpsat(solver, var_manager)
        elif isinstance(solver, z3.Solver):
            self._add_to_z3(solver, var_manager)
        return True

    def _add_to_cpsat(self, model: cp_model.CpModel, var_manager: CPSATVariableManager):
        for scope, h, super_users in var_manager.instance.sual:
            for step in scope:
                step_vars = [var for _, var in var_manager.get_step_variables(step)]
                super_vars = [var for user, var in var_manager.get_step_variables(step)
                            if user in super_users]
                
                condition = model.NewBoolVar(f'sual_cond_{step}')
                model.Add(sum(step_vars) <= h).OnlyEnforceIf(condition)
                model.Add(sum(step_vars) > h).OnlyEnforceIf(condition.Not())
                
                if super_vars:
                    model.AddBoolOr(super_vars).OnlyEnforceIf(condition)

    def _add_to_z3(self, solver: z3.Solver, var_manager: Z3VariableManager):
        for scope, h, super_users in var_manager.instance.sual:
            for step in scope:
                step_vars = [var for _, var in var_manager.get_step_variables(step)]
                super_vars = [var for user, var in var_manager.get_step_variables(step)
                            if user in super_users]
                
                condition = z3.Bool(f'sual_cond_{step}')
                
                # Encode condition as step_count <= h
                step_count = z3.Sum([z3.If(var, 1, 0) for var in step_vars])
                solver.add(z3.Implies(condition, step_count <= h))
                solver.add(z3.Implies(z3.Not(condition), step_count > h))
                
                if super_vars:
                    solver.add(z3.Implies(condition, z3.Or(super_vars)))


class WangLiConstraint(BaseConstraint):
    def check_feasibility(self, var_manager: VariableManagerBase) -> Tuple[bool, List[str]]:
        if not hasattr(var_manager.instance, 'wang_li'):
            return True, []
            
        errors = []
        for scope, departments in var_manager.instance.wang_li:
            valid_dept = False
            for dept_idx, dept in enumerate(departments):
                if all(any(var_manager.instance.user_step_matrix[u][s] for u in dept) 
                      for s in scope):
                    valid_dept = True
                    break
            if not valid_dept:
                errors.append(f"No department can cover all steps {[s+1 for s in scope]}")
        return len(errors) == 0, errors

    def add_to_solver(self, solver: Solver, var_manager: VariableManagerBase) -> bool:
        if not hasattr(var_manager.instance, 'wang_li'):
            return True
            
        is_feasible, errors = self.check_feasibility(var_manager)
        if not is_feasible:
            return False

        if isinstance(solver, cp_model.CpModel):
            self._add_to_cpsat(solver, var_manager)
        elif isinstance(solver, z3.Solver):
            self._add_to_z3(solver, var_manager)
        return True

    def _add_to_cpsat(self, model: cp_model.CpModel, var_manager: CPSATVariableManager):
        for scope, departments in var_manager.instance.wang_li:
            dept_vars = [model.NewBoolVar(f'dept_{i}') for i in range(len(departments))]
            model.AddExactlyOne(dept_vars)
            
            for step in scope:
                for user, var in var_manager.step_variables[step]:
                    # Find which departments the user belongs to
                    user_depts = []
                    for dept_idx, dept in enumerate(departments):
                        if user in dept:
                            user_depts.append(dept_vars[dept_idx])
                    
                    if user_depts:
                        model.AddImplication(var, model.AddBoolOr(user_depts))
                    else:
                        model.Add(var == 0)

    def _add_to_z3(self, solver: z3.Solver, var_manager: Z3VariableManager):
        for scope, departments in var_manager.instance.wang_li:
            dept_vars = [z3.Bool(f'dept_{len(solver.assertions())}_{i}') 
                        for i in range(len(departments))]
            
            # Exactly one department
            solver.add(z3.PbEq([(v, 1) for v in dept_vars], 1))
            
            for step in scope:
                for user, var in var_manager.step_variables[step]:
                    user_depts = []
                    for dept_idx, dept in enumerate(departments):
                        if user in dept:
                            user_depts.append(dept_vars[dept_idx])
                    
                    if user_depts:
                        solver.add(z3.Implies(var, z3.Or(user_depts)))
                    else:
                        solver.add(z3.Not(var))


class AssignmentDependentConstraint(BaseConstraint):
    def check_feasibility(self, var_manager: VariableManagerBase) -> Tuple[bool, List[str]]:
        if not hasattr(var_manager.instance, 'ada'):
            return True, []
            
        errors = []
        for s1, s2, source_users, target_users in var_manager.instance.ada:
            auth_source = var_manager.get_authorized_users(s1) & set(source_users)
            if not auth_source:
                errors.append(f"No authorized source users for step {s1+1}")
                continue
                
            auth_target = var_manager.get_authorized_users(s2) & set(target_users)
            if not auth_target:
                errors.append(f"No authorized target users for step {s2+1}")
                
        return len(errors) == 0, errors

    def add_to_solver(self, solver: Solver, var_manager: VariableManagerBase) -> bool:
        if not hasattr(var_manager.instance, 'ada'):
            return True
            
        is_feasible, errors = self.check_feasibility(var_manager)
        if not is_feasible:
            return False

        if isinstance(solver, cp_model.CpModel):
            self._add_to_cpsat(solver, var_manager)
        elif isinstance(solver, z3.Solver):
            self._add_to_z3(solver, var_manager)
        return True

    def _add_to_cpsat(self, model: cp_model.CpModel, var_manager: CPSATVariableManager):
        for s1, s2, source_users, target_users in var_manager.instance.ada:
            source_vars = []
            target_vars = []
            
            for user in source_users:
                if s1 in var_manager.user_step_variables[user]:
                    source_vars.append(var_manager.user_step_variables[user][s1])
                    
            for user in target_users:
                if s2 in var_manager.user_step_variables[user]:
                    target_vars.append(var_manager.user_step_variables[user][s2])

            if source_vars and target_vars:
                source_used = model.NewBoolVar(f'ada_source_{s1}_{s2}')
                model.Add(sum(source_vars) >= 1).OnlyEnforceIf(source_used)
                model.Add(sum(source_vars) == 0).OnlyEnforceIf(source_used.Not())
                
                # If source assigned, must use target
                model.Add(sum(target_vars) >= 1).OnlyEnforceIf(source_used)

    def _add_to_z3(self, solver: z3.Solver, var_manager: Z3VariableManager):
        for s1, s2, source_users, target_users in var_manager.instance.ada:
            source_vars = []
            target_vars = []
            
            for user in source_users:
                if s1 in var_manager.user_step_variables[user]:
                    source_vars.append(var_manager.user_step_variables[user][s1])
                    
            for user in target_users:
                if s2 in var_manager.user_step_variables[user]:
                    target_vars.append(var_manager.user_step_variables[user][s2])

            if source_vars and target_vars:
                source_used = z3.Bool(f'ada_source_{s1}_{s2}')
                
                # Encode source usage
                source_count = z3.Sum([z3.If(v, 1, 0) for v in source_vars])
                solver.add(z3.Implies(source_used, source_count >= 1))
                solver.add(z3.Implies(z3.Not(source_used), source_count == 0))
                
                # If source used, must use target
                target_count = z3.Sum([z3.If(v, 1, 0) for v in target_vars])
                solver.add(z3.Implies(source_used, target_count >= 1))

