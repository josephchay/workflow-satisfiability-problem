from typing import Dict, List, Set, Tuple
import random
from abc import ABC, abstractmethod
import numpy as np
from deap import base, creator, tools, algorithms
import numpy as np
from collections import defaultdict


class DEAPVariableManager:
    """Manages DEAP variables for the WSP problem using genetic algorithm approach"""
    def __init__(self, instance):
        self.instance = instance
        self._initialized = False
        self.toolbox = base.Toolbox()
        
        # Create fitness class that minimizes constraint violations
        creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMin)
        
        # Initialize statistics for tracking
        self.stats = tools.Statistics(lambda ind: ind.fitness.values)
        self.stats.register("avg", np.mean)
        self.stats.register("std", np.std)
        self.stats.register("min", np.min)
        self.stats.register("max", np.max)
        
    def create_variables(self) -> bool:
        """Set up DEAP genetic algorithm variables and operators"""
        try:
            # Clear any existing setup
            self.toolbox.unregister("individual")
            self.toolbox.unregister("population")
            self.toolbox.unregister("mate")
            self.toolbox.unregister("mutate")
            self.toolbox.unregister("select")
            
            # Define individual creation
            def create_individual():
                # Create a list of step -> user assignments
                # Each position represents a step, value represents assigned user
                individual = []
                for step in range(self.instance.number_of_steps):
                    authorized = self.get_authorized_users(step)
                    if not authorized:
                        return None  # Infeasible if no authorized users
                    individual.append(random.choice(list(authorized)))
                return individual

            # Register creation functions
            self.toolbox.register("individual_creator", tools.initIterate, 
                                creator.Individual, create_individual)
            self.toolbox.register("population_creator", tools.initRepeat, 
                                list, self.toolbox.individual_creator)
                                
            # Define genetic operators
            self.toolbox.register("mate", self._crossover)
            self.toolbox.register("mutate", self._mutation)
            self.toolbox.register("select", tools.selTournament, tournsize=3)
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Error creating DEAP variables: {str(e)}")
            return False
            
    def _crossover(self, ind1, ind2):
        """Custom crossover operator that preserves authorization constraints"""
        size = len(ind1)
        cxpoint1 = random.randint(1, size)
        cxpoint2 = random.randint(1, size - 1)
        if cxpoint2 >= cxpoint1:
            cxpoint2 += 1
        else: # Swap the two cx points
            cxpoint1, cxpoint2 = cxpoint2, cxpoint1

        # Create new individuals
        new_ind1 = creator.Individual(ind1)
        new_ind2 = creator.Individual(ind2)
        
        # Cross between points while maintaining authorization
        for i in range(cxpoint1, cxpoint2):
            if (self.instance.user_step_matrix[ind2[i]][i] and 
                self.instance.user_step_matrix[ind1[i]][i]):
                new_ind1[i], new_ind2[i] = ind2[i], ind1[i]
                
        return new_ind1, new_ind2
        
    def _mutation(self, individual):
        """Custom mutation operator that maintains authorization constraints"""
        for step in range(len(individual)):
            if random.random() < 0.1:  # 10% mutation rate
                authorized = self.get_authorized_users(step)
                if authorized:
                    individual[step] = random.choice(list(authorized))
        return individual,

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

    def get_assignment_from_solution(self, best_individual) -> Dict[int, int]:
        """Convert best individual to step -> user assignment dictionary"""
        return {step + 1: user + 1 for step, user in enumerate(best_individual)}


class DEAPConstraint(ABC):
    """Base class for DEAP constraints used in fitness evaluation"""
    def __init__(self, instance, var_manager: DEAPVariableManager):
        self.instance = instance
        self.var_manager = var_manager

    @abstractmethod
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        """Check if constraint can potentially be satisfied"""
        pass
        
    @abstractmethod
    def evaluate_violations(self, individual) -> int:
        """Evaluate number of constraint violations for an individual"""
        pass


class DEAPConstraintManager:
    """Manages DEAP constraints and fitness evaluation"""
    def __init__(self, instance, var_manager: DEAPVariableManager):
        self.instance = instance
        self.var_manager = var_manager
        
        # Initialize all constraints
        self.constraints = {
            'authorization': DEAPAuthorizationConstraint(instance, var_manager),
            'binding_of_duty': DEAPBindingOfDutyConstraint(instance, var_manager),
            'separation_of_duty': DEAPSeparationOfDutyConstraint(instance, var_manager),
            'at_most_k': DEAPAtMostKConstraint(instance, var_manager),
            'one_team': DEAPOneTeamConstraint(instance, var_manager),
            'super_user_at_least': DEAPSUALConstraint(instance, var_manager),
            'wang_li': DEAPWangLiConstraint(instance, var_manager),
            'assignment_dependent': DEAPAssignmentDependentConstraint(instance, var_manager)
        }
        
        # Active constraints to use in evaluation
        self.active_constraints = {}
        
    def check_all_feasibility(self) -> Tuple[bool, List[str]]:
        """Check if all active constraints are potentially feasible"""
        errors = []
        for name, constraint in self.constraints.items():
            if self.active_constraints.get(name, True):
                is_feasible, constraint_errors = constraint.check_feasibility()
                if not is_feasible:
                    errors.extend(constraint_errors)
        return len(errors) == 0, errors
        
    def evaluate_fitness(self, individual):
        """Evaluate total constraint violations for an individual"""
        total_violations = 0
        for name, constraint in self.constraints.items():
            if self.active_constraints.get(name, True):
                violations = constraint.evaluate_violations(individual)
                total_violations += violations
        return total_violations,

    def setup_evolution(self, active_constraints: dict):
        """Set up evolutionary algorithm with active constraints"""
        self.active_constraints = active_constraints
        
        # Register evaluation function
        self.var_manager.toolbox.register("evaluate", self.evaluate_fitness)
        
        return self.check_all_feasibility()


class DEAPAuthorizationConstraint(DEAPConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        infeasible_steps = []
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                infeasible_steps.append(step + 1)
                
        return (len(infeasible_steps) == 0, 
                [f"No authorized users for step {step}" for step in infeasible_steps])
                
    def evaluate_violations(self, individual) -> int:
        violations = 0
        for step, user in enumerate(individual):
            if not self.instance.user_step_matrix[user][step]:
                violations += 1
        return violations
        
        
class DEAPBindingOfDutyConstraint(DEAPConstraint):
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
                
    def evaluate_violations(self, individual) -> int:
        violations = 0
        for s1, s2 in self.instance.BOD:
            if individual[s1] != individual[s2]:
                violations += 1
        return violations


class DEAPSeparationOfDutyConstraint(DEAPConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []
        
    def evaluate_violations(self, individual) -> int:
        violations = 0
        for s1, s2 in self.instance.SOD:
            if individual[s1] == individual[s2]:
                violations += 1
        return violations


class DEAPAtMostKConstraint(DEAPConstraint):
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
                
    def evaluate_violations(self, individual) -> int:
        violations = 0
        for k, steps in self.instance.at_most_k:
            # Count assignments per user for these steps
            user_counts = defaultdict(int)
            for s in steps:
                user_counts[individual[s]] += 1
                
            # Check for violations
            for count in user_counts.values():
                if count > k:
                    violations += (count - k)
        return violations


class DEAPOneTeamConstraint(DEAPConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []
        
    def evaluate_violations(self, individual) -> int:
        violations = 0
        for steps, teams in self.instance.one_team:
            # Get users assigned to these steps
            assigned_users = {individual[s] for s in steps}
            
            # Check if all users are from same team
            valid_team = False
            for team in teams:
                if assigned_users.issubset(team):
                    valid_team = True
                    break
                    
            if not valid_team:
                violations += 1
                
        return violations


class DEAPSUALConstraint(DEAPConstraint):
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
        
    def evaluate_violations(self, individual) -> int:
        violations = 0
        for scope, h, super_users in self.instance.sual:
            # Count unique users assigned to scope
            assigned_users = {individual[s] for s in scope}
            
            # If using h or fewer users, must include super user
            if len(assigned_users) <= h:
                super_user_used = any(u in super_users for u in assigned_users)
                if not super_user_used:
                    violations += 1
                    
        return violations


class DEAPWangLiConstraint(DEAPConstraint):
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
        
        
    def evaluate_violations(self, individual) -> int:
        violations = 0
        for scope, departments in self.instance.wang_li:
            # Get users assigned to scope
            assigned_users = {individual[s] for s in scope}
            
            # Check if all users are from same department
            valid_dept = False
            for dept in departments:
                if assigned_users.issubset(dept):
                    valid_dept = True
                    break
            
            if not valid_dept:
                violations += 1
                    
        return violations


class DEAPAssignmentDependentConstraint(DEAPConstraint):
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
        
    def evaluate_violations(self, individual) -> int:
        violations = 0
        for s1, s2, source_users, target_users in self.instance.ada:
            # Check if s1 is assigned to a source user
            if individual[s1] in source_users:
                # If so, s2 must be assigned to a target user
                if individual[s2] not in target_users:
                    violations += 1
                    
        return violations
