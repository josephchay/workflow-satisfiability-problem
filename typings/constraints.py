from collections import defaultdict


class VariableManager:
    """Manages CP-SAT variables for the WSP problem"""
    def __init__(self, model, instance):
        self.model = model
        self.instance = instance
        self.step_variables = {}
        self.user_step_variables = defaultdict(dict)
        
    def create_variables(self):
        """Create boolean variables for user-step assignments"""
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


class ConstraintManager:
    """Manages constraints for the WSP problem"""
    def __init__(self, model, instance, var_manager):
        self.model = model
        self.instance = instance
        self.var_manager = var_manager
        
    def add_all_constraints(self):
        """Add all problem constraints to the model"""
        self.add_authorization_constraints()
        self.add_separation_of_duty()
        if not self.add_binding_of_duty():
            return False
        self.add_at_most_k()
        self.add_one_team()
        return True
        
    def add_authorization_constraints(self):
        """Add authorization constraints"""
        for step, user_vars in self.var_manager.step_variables.items():
            self.model.AddExactlyOne(var for _, var in user_vars)
    
    def add_binding_of_duty(self):
        """Add binding of duty constraints"""
        # Check feasibility first
        infeasible_constraints = []
        for s1, s2 in self.instance.BOD:
            common_users = set()
            for user in range(self.instance.number_of_users):
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2]):
                    common_users.add(user)
            
            if not common_users:
                infeasible_constraints.append((s1+1, s2+1))
        
        if infeasible_constraints:
            return False
        
        # Add BOD constraints
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
        
    def add_separation_of_duty(self):
        """Add separation of duty constraints"""
        for s1, s2 in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                if (s1 in self.var_manager.user_step_variables[user] and 
                    s2 in self.var_manager.user_step_variables[user]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    self.model.Add(var1 + var2 <= 1)
                    
    def add_at_most_k(self):
        """Add at-most-k constraints"""
        for k, steps in self.instance.at_most_k:
            for user in range(self.instance.number_of_users):
                user_step_vars = []
                for step in steps:
                    if step in self.var_manager.user_step_variables[user]:
                        user_step_vars.append(self.var_manager.user_step_variables[user][step])
                
                if user_step_vars:
                    self.model.Add(sum(user_step_vars) <= k)
        
        if self.instance.at_most_k:
            min_k = min(k for k, _ in self.instance.at_most_k)
            for user in range(self.instance.number_of_users):
                user_vars = []
                for step in range(self.instance.number_of_steps):
                    if step in self.var_manager.user_step_variables[user]:
                        user_vars.append(self.var_manager.user_step_variables[user][step])
                if user_vars:
                    self.model.Add(sum(user_vars) <= min_k)
                    
    def add_one_team(self):
        """Add one-team constraints"""
        for steps, teams in self.instance.one_team:
            team_vars = [self.model.NewBoolVar(f'team_{i}') for i in range(len(teams))]
            self.model.AddExactlyOne(team_vars)
            
            for step in steps:
                for team_idx, team in enumerate(teams):
                    team_var = team_vars[team_idx]
                    for user, var in self.var_manager.step_variables[step]:
                        if user not in team:
                            self.model.Add(var == 0).OnlyEnforceIf(team_var)
