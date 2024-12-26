from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from jpype import JClass, JInt, java
from abc import ABC, abstractmethod


class SAT4JVariableManager:
    """Manages SAT4J variables for the WSP problem"""
    def __init__(self, solver, instance):
        self.solver = solver
        self.instance = instance
        self._initialized = False
        
        # Maps to track variables
        self.step_variables: Dict[int, List[Tuple[int, int]]] = {}  # Maps step to list of (user, var_id)
        self.user_step_variables: Dict[int, Dict[int, int]] = defaultdict(dict)  # Maps user,step to var_id
        self.next_var_id = 1  # SAT4J uses 1-based variable indexing
        
        # Track clauses for uniqueness checking
        self.original_clauses = []
        
    def create_variables(self) -> bool:
        """Create boolean variables for user-step assignments"""
        try:
            self.step_variables.clear()
            self.user_step_variables.clear()
            self.next_var_id = 1
            
            # Create variables only for authorized user-step pairs
            for step in range(self.instance.number_of_steps):
                self.step_variables[step] = []
                for user in range(self.instance.number_of_users):
                    if self.instance.user_step_matrix[user][step]:
                        var_id = self.next_var_id
                        self.next_var_id += 1
                        self.step_variables[step].append((user, var_id))
                        self.user_step_variables[user][step] = var_id
                        
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Error creating SAT4J variables: {str(e)}")
            return False

    def get_step_variables(self, step: int) -> List[Tuple[int, int]]:
        """Get list of (user, var_id) pairs for a step"""
        self._check_initialized()
        return self.step_variables.get(step, [])

    def get_user_variables(self, user: int) -> Dict[int, int]:
        """Get dictionary of {step: var_id} for a user"""
        self._check_initialized()
        return self.user_step_variables[user]

    def get_user_step_variable(self, user: int, step: int) -> int:
        """Get variable ID for specific user-step pair"""
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

    def _check_initialized(self):
        """Ensure variables have been created"""
        if not self._initialized:
            raise RuntimeError("Variables not initialized. Call create_variables() first.")

    def save_original_clauses(self):
        """Save current clauses for uniqueness checking"""
        self.original_clauses = [clause for clause in self.solver.get_clauses()]

    def get_assignment_from_model(self, model) -> Dict[int, int]:
        """Extract step -> user assignment from solver model"""
        self._check_initialized()
        
        assignment = {}
        for step in range(self.instance.number_of_steps):
            for user, var_id in self.step_variables[step]:
                if model[var_id - 1]:  # Convert to 0-based for model indexing
                    assignment[step + 1] = user + 1
                    break
        return assignment


class SAT4JConstraint(ABC):
    """Base class for SAT4J constraints"""
    def __init__(self, solver, instance, var_manager: SAT4JVariableManager):
        self.solver = solver
        self.instance = instance
        self.var_manager = var_manager

    @abstractmethod
    def add_clauses(self) -> bool:
        """Add clauses to the solver. Returns False if infeasible."""
        pass

    @abstractmethod
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        """Check if constraint can potentially be satisfied."""
        pass


class SAT4JAuthorizationConstraint(SAT4JConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        infeasible_steps = []
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                infeasible_steps.append(step + 1)
                
        return (len(infeasible_steps) == 0, 
                [f"No authorized users for step {step}" for step in infeasible_steps])

    def add_clauses(self) -> bool:
        """Add authorization clauses to SAT4J solver"""
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        # For each step, at least one authorized user must be assigned
        for step, user_vars in self.var_manager.step_variables.items():
            # Add clause: v1 ∨ v2 ∨ ... ∨ vn
            self.solver.add_clause([var_id for _, var_id in user_vars])
            
            # Add clauses to ensure at most one user per step
            for i, (_, var1) in enumerate(user_vars):
                for _, var2 in user_vars[i+1:]:
                    # Add clause: ¬v1 ∨ ¬v2
                    self.solver.add_clause([-var1, -var2])
                    
        return True


class SAT4JBindingOfDutyConstraint(SAT4JConstraint):
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

    def add_clauses(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for s1, s2 in self.instance.BOD:
            for user in range(self.instance.number_of_users):
                if (s1 in self.var_manager.user_step_variables[user] and 
                    s2 in self.var_manager.user_step_variables[user]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    # Add clauses: (v1 → v2) ∧ (v2 → v1)
                    self.solver.add_clause([-var1, var2])
                    self.solver.add_clause([var1, -var2])
                    
        return True


class SAT4JSeparationOfDutyConstraint(SAT4JConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []

    def add_clauses(self) -> bool:
        for s1, s2 in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                if (s1 in self.var_manager.user_step_variables[user] and 
                    s2 in self.var_manager.user_step_variables[user]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    # Add clause: ¬v1 ∨ ¬v2
                    self.solver.add_clause([-var1, -var2])
        return True


class SAT4JAtMostKConstraint(SAT4JConstraint):
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

    def add_clauses(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        # For each at-most-k constraint
        for k, steps in self.instance.at_most_k:
            # For each user
            for user in range(self.instance.number_of_users):
                step_vars = []
                for step in steps:
                    if step in self.var_manager.user_step_variables[user]:
                        step_vars.append(self.var_manager.user_step_variables[user][step])
                
                if len(step_vars) > k:
                    # Add clauses to ensure at most k variables can be true
                    # We use the sequential counter encoding for this
                    self._add_at_most_k_clauses(step_vars, k)
                    
        return True

    def _add_at_most_k_clauses(self, variables: List[int], k: int):
        """Add clauses to enforce at-most-k using sequential counter encoding"""
        n = len(variables)
        if n <= k:
            return  # No constraint needed
            
        # Create auxiliary variables for counter bits
        aux_vars = []
        for i in range(n-1):
            for j in range(k):
                aux_vars.append(self.var_manager.next_var_id)
                self.var_manager.next_var_id += 1
                
        def s(i, j):
            if i < 0 or j < 0:
                return 0
            if i == 0:
                return variables[0]
            return aux_vars[i * k + j]
            
        # Add clauses for sequential counter
        for i in range(n-1):
            for j in range(k):
                if j == 0:
                    self.solver.add_clause([-variables[i+1], s(i,0)])
                else:
                    self.solver.add_clause([-variables[i+1], -s(i,j-1), s(i,j)])
                    
                if i > 0:
                    self.solver.add_clause([-s(i-1,j), s(i,j)])
                    if j > 0:
                        self.solver.add_clause([-variables[i+1], -s(i-1,j-1), s(i,j)])
                        
        # Final clause to prevent k+1 true variables
        self.solver.add_clause([-variables[n-1], -s(n-2,k-1)])


class SAT4JOneTeamConstraint(SAT4JConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []  # Always potentially feasible if teams not empty

    def add_clauses(self) -> bool:
        for steps, teams in self.instance.one_team:
            # Create auxiliary variables for each team
            team_vars = []
            for i in range(len(teams)):
                team_vars.append(self.var_manager.next_var_id)
                self.var_manager.next_var_id += 1

            # Exactly one team must be chosen
            # Add clause: team1 ∨ team2 ∨ ... ∨ teamN
            self.solver.add_clause(team_vars)
            
            # No two teams can be chosen
            for i in range(len(team_vars)):
                for j in range(i + 1, len(team_vars)):
                    # Add clause: ¬teami ∨ ¬teamj
                    self.solver.add_clause([-team_vars[i], -team_vars[j]])

            # For each step in scope
            for step in steps:
                for user, var_id in self.var_manager.get_step_variables(step):
                    # Find which teams this user belongs to
                    user_teams = []
                    for team_idx, team in enumerate(teams):
                        if user in team:
                            user_teams.append(team_vars[team_idx])
                    
                    if user_teams:
                        # User can only be assigned if their team is chosen
                        # Add clauses: var_id → (team1 ∨ team2 ∨ ...)
                        team_clause = user_teams + [-var_id]
                        self.solver.add_clause(team_clause)
                    else:
                        # User cannot be assigned if not in any team
                        self.solver.add_clause([-var_id])

        return True


class SAT4JSUALConstraint(SAT4JConstraint):
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

    def add_clauses(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for scope, h, super_users in self.instance.sual:
            for step in scope:
                # Get variables for all users assigned to this step
                step_vars = [var_id for _, var_id in self.var_manager.get_step_variables(step)]
                
                # Get variables for super users
                super_vars = [var_id for user, var_id in self.var_manager.get_step_variables(step)
                            if user in super_users]
                
                if step_vars:
                    # Create auxiliary variables for counting assignments
                    count_vars = []
                    n = len(step_vars)
                    for i in range(h + 1):
                        count_vars.append(self.var_manager.next_var_id)
                        self.var_manager.next_var_id += 1

                    # Add sequential counter clauses
                    self._add_counting_network(step_vars, count_vars)
                    
                    # If count ≤ h, must use a super user
                    if super_vars:
                        # count_vars[h] is true when count ≤ h
                        # Add clause: count_vars[h] → (super1 ∨ super2 ∨ ...)
                        self.solver.add_clause([-count_vars[h]] + super_vars)

        return True
        
    def _add_counting_network(self, input_vars: List[int], count_vars: List[int]):
        """Add clauses for sequential counter network"""
        n = len(input_vars)
        h = len(count_vars) - 1  # max count
        
        # Create auxiliary variables for each layer
        aux = {}
        for i in range(n):
            for j in range(min(i + 1, h + 1)):
                aux[i,j] = self.var_manager.next_var_id
                self.var_manager.next_var_id += 1

        # First variable
        if h > 0:
            self.solver.add_clause([-input_vars[0], aux[0,0]])
            
        # Propagation clauses
        for i in range(1, n):
            # Current input can activate first counter
            self.solver.add_clause([-input_vars[i], aux[i,0]])
            
            for j in range(1, min(i + 1, h + 1)):
                # Counter j can be activated by:
                # 1. Counter j from previous level
                # 2. Counter j-1 from previous level AND current input
                self.solver.add_clause([-aux[i-1,j], aux[i,j]])
                self.solver.add_clause([-aux[i-1,j-1], -input_vars[i], aux[i,j]])

        # Link final auxiliary variables to count_vars
        for j in range(h + 1):
            self.solver.add_clause([-aux[n-1,j], count_vars[j]])
            self.solver.add_clause([aux[n-1,j], -count_vars[j]])


class SAT4JWangLiConstraint(SAT4JConstraint):
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

    def add_clauses(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for scope, departments in self.instance.wang_li:
            # Create department choice variables
            dept_vars = []
            for _ in departments:
                dept_vars.append(self.var_manager.next_var_id)
                self.var_manager.next_var_id += 1
            
            # Exactly one department must be chosen
            self.solver.add_clause(dept_vars)
            for i in range(len(dept_vars)):
                for j in range(i + 1, len(dept_vars)):
                    self.solver.add_clause([-dept_vars[i], -dept_vars[j]])
            
            # For each step in scope
            for step in scope:
                for user, var_id in self.var_manager.get_step_variables(step):
                    # Find which departments this user belongs to
                    user_depts = []
                    for dept_idx, dept in enumerate(departments):
                        if user in dept:
                            user_depts.append(dept_vars[dept_idx])
                    
                    if user_depts:
                        # User can only be assigned if their department is chosen
                        self.solver.add_clause(user_depts + [-var_id])
                    else:
                        # User cannot be assigned if not in any department
                        self.solver.add_clause([-var_id])

        return True


class SAT4JAssignmentDependentConstraint(SAT4JConstraint):
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

    def add_clauses(self) -> bool:
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for s1, s2, source_users, target_users in self.instance.ada:
            # Create indicator variable for source user assignment
            source_used = self.var_manager.next_var_id
            self.var_manager.next_var_id += 1
            
            # Get source step variables
            source_vars = [var_id for user, var_id in self.var_manager.get_step_variables(s1)
                         if user in source_users]
                         
            # Get target step variables
            target_vars = [var_id for user, var_id in self.var_manager.get_step_variables(s2)
                         if user in target_users]
            
            if source_vars and target_vars:
                # source_used ↔ (source1 ∨ source2 ∨ ...)
                self.solver.add_clause([-source_used] + source_vars)
                for var_id in source_vars:
                    self.solver.add_clause([-var_id, source_used])
                
                # If source_used, then some target user must be assigned
                self.solver.add_clause([-source_used] + target_vars)
                
                # If source_used, non-target users cannot be assigned to s2
                for user, var_id in self.var_manager.get_step_variables(s2):
                    if user not in target_users:
                        self.solver.add_clause([-source_used, -var_id])
                        
        return True
    