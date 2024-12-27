from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from abc import ABC, abstractmethod
import numpy as np
import networkx as nx
from pgmpy.models import BayesianNetwork
from pgmpy.factors.discrete import TabularCPD


class PGMPYVariableManager:
    """Manages Bayesian Network variables for WSP problem"""
    def __init__(self, model: BayesianNetwork, instance):
        self.model = model
        self.instance = instance
        self.step_variables = {}  # Step nodes
        self.user_step_pairs = defaultdict(dict)  # User-step pair nodes
        self._initialized = False
        
    def create_variables(self) -> bool:
        """Create BN variables for user-step assignments"""
        try:
            self.step_variables.clear()
            self.user_step_pairs.clear()
            
            # Create step assignment nodes (one per step)
            for step in range(self.instance.number_of_steps):
                node_name = f"S_{step+1}"
                self.step_variables[step] = node_name
                
                # Get authorized users for this step
                authorized_users = [u+1 for u in range(self.instance.number_of_users) 
                                  if self.instance.user_step_matrix[u][step]]
                
                # Create CPD for step node (uniform over authorized users)
                n_users = len(authorized_users)
                if n_users > 0:
                    cpd = TabularCPD(
                        variable=node_name,
                        variable_card=n_users,
                        values=[[1/n_users] * n_users],
                        state_names={node_name: authorized_users}
                    )
                    self.model.add_cpds(cpd)
                
            # Add nodes for user-step pairs where needed for constraints
            for step in range(self.instance.number_of_steps):
                for user in range(self.instance.number_of_users):
                    if self.instance.user_step_matrix[user][step]:
                        node_name = f"US_{user+1}_{step+1}"
                        self.user_step_pairs[user][step] = node_name
                
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Error creating BN variables: {str(e)}")
            return False
            
    def get_step_node(self, step: int) -> str:
        """Get node name for a step"""
        self._check_initialized()
        return self.step_variables.get(step)
        
    def get_user_step_node(self, user: int, step: int) -> str:
        """Get node name for user-step pair"""
        self._check_initialized()
        return self.user_step_pairs[user].get(step)
        
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
            
    def get_assignment_from_beliefs(self, beliefs: Dict[str, Dict[Any, float]]) -> Dict[int, int]:
        """Extract step -> user assignment from network beliefs"""
        assignment = {}
        
        # For each step node, get most likely user assignment
        for step, node in self.step_variables.items():
            if node in beliefs:
                probs = beliefs[node]
                if probs:
                    assignment[step + 1] = max(probs.items(), key=lambda x: x[1])[0]
                    
        return assignment


class PGMPYConstraint(ABC):
    """Base class for Bayesian Network constraints"""
    def __init__(self, model: BayesianNetwork, instance, var_manager: PGMPYVariableManager):
        self.model = model
        self.instance = instance
        self.var_manager = var_manager
        
    @abstractmethod
    def add_to_network(self) -> bool:
        """Add constraint to Bayesian Network. Returns False if infeasible."""
        pass
        
    @abstractmethod
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        """Check if constraint can potentially be satisfied."""
        pass
        
    @abstractmethod
    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        """Verify if an assignment satisfies the constraint."""
        pass


class PGMPYAuthorizationConstraint(PGMPYConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        infeasible_steps = []
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                infeasible_steps.append(step + 1)
                
        return (len(infeasible_steps) == 0, 
                [f"No authorized users for step {step}" for step in infeasible_steps])
                
    def add_to_network(self) -> bool:
        """Authorization is handled through node state spaces"""
        return True
        
    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        violations = []
        for step, user in assignment.items():
            if not self.instance.user_step_matrix[user-1][step-1]:
                violations.append(
                    f"Authorization violation: User {user} not authorized for step {step}"
                )
        return violations


class PGMPYBindingOfDutyConstraint(PGMPYConstraint):
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
                
    def add_to_network(self) -> bool:
        """Add BOD constraints to network"""
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for s1, s2 in self.instance.BOD:
            node1 = self.var_manager.get_step_node(s1)
            node2 = self.var_manager.get_step_node(s2)
            
            if node1 and node2:
                # Add edge between steps
                self.model.add_edge(node1, node2)
                
                # Create CPD that forces same user assignment
                auth_users1 = list(self.var_manager.get_authorized_users(s1))
                auth_users2 = list(self.var_manager.get_authorized_users(s2))
                
                # Create probability table: 1 when same user, 0 otherwise
                cpd_values = []
                for u1 in auth_users1:
                    row = []
                    for u2 in auth_users2:
                        row.append(1.0 if u1 == u2 else 0.0)
                    cpd_values.append(row)
                
                cpd = TabularCPD(
                    variable=node2,
                    variable_card=len(auth_users2),
                    values=cpd_values,
                    evidence=[node1],
                    evidence_card=[len(auth_users1)],
                    state_names={
                        node1: [u+1 for u in auth_users1],
                        node2: [u+1 for u in auth_users2]
                    }
                )
                self.model.add_cpds(cpd)
                
        return True
        
    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        violations = []
        for s1, s2 in self.instance.BOD:
            if (s1+1 in assignment and s2+1 in assignment and 
                assignment[s1+1] != assignment[s2+1]):
                violations.append(
                    f"Binding of duty violation: Steps {s1+1} and {s2+1} "
                    f"assigned to different users"
                )
        return violations
    

class PGMPYSeparationOfDutyConstraint(PGMPYConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []  # Always potentially feasible if steps have multiple users

    def add_to_network(self) -> bool:
        """Add SOD constraints to network"""
        for s1, s2 in self.instance.SOD:
            node1 = self.var_manager.get_step_node(s1)
            node2 = self.var_manager.get_step_node(s2)
            
            if node1 and node2:
                # Add edge between steps
                self.model.add_edge(node1, node2)
                
                # Create CPD that forces different user assignments
                auth_users1 = list(self.var_manager.get_authorized_users(s1))
                auth_users2 = list(self.var_manager.get_authorized_users(s2))
                
                # Create probability table: 0 when same user, uniform otherwise
                cpd_values = []
                for u1 in auth_users1:
                    row = []
                    valid_count = sum(1 for u2 in auth_users2 if u1 != u2)
                    prob = 1.0 / valid_count if valid_count > 0 else 0.0
                    for u2 in auth_users2:
                        row.append(0.0 if u1 == u2 else prob)
                    cpd_values.append(row)
                
                cpd = TabularCPD(
                    variable=node2,
                    variable_card=len(auth_users2),
                    values=cpd_values,
                    evidence=[node1],
                    evidence_card=[len(auth_users1)],
                    state_names={
                        node1: [u+1 for u in auth_users1],
                        node2: [u+1 for u in auth_users2]
                    }
                )
                self.model.add_cpds(cpd)
                
        return True

    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        violations = []
        for s1, s2 in self.instance.SOD:
            if (s1+1 in assignment and s2+1 in assignment and 
                assignment[s1+1] == assignment[s2+1]):
                violations.append(
                    f"Separation of duty violation: Steps {s1+1} and {s2+1} "
                    f"assigned to same user"
                )
        return violations


class PGMPYAtMostKConstraint(PGMPYConstraint):
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

    def add_to_network(self) -> bool:
        """Add at-most-k constraints to network"""
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for k, steps in self.instance.at_most_k:
            # Create auxiliary node to track user count
            aux_node = f"AtMostK_{len(self.model.nodes())}"
            
            # Connect all steps in scope to auxiliary node
            step_nodes = [self.var_manager.get_step_node(s) for s in steps]
            step_nodes = [n for n in step_nodes if n]
            
            for node in step_nodes:
                self.model.add_edge(node, aux_node)
            
            # Create CPD for auxiliary node that enforces at-most-k
            auth_users = set()
            for step in steps:
                auth_users.update(self.var_manager.get_authorized_users(step))
            
            # Complex CPD creation that enforces cardinality constraint
            # [Implementation details for CPD creation...]
            
        return True

    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        violations = []
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
        return violations


class PGMPYOneTeamConstraint(PGMPYConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        return True, []  # Always potentially feasible if teams not empty

    def add_to_network(self) -> bool:
        """Add one-team constraints to network"""
        for scope_idx, (steps, teams) in enumerate(self.instance.one_team):
            # Create team selection node
            team_node = f"Team_{scope_idx}"
            
            # Connect team node to all steps in scope
            step_nodes = [self.var_manager.get_step_node(s) for s in steps]
            step_nodes = [n for n in step_nodes if n]
            
            for node in step_nodes:
                self.model.add_edge(team_node, node)
            
            # Create CPD for team selection (uniform over teams)
            team_cpd = TabularCPD(
                variable=team_node,
                variable_card=len(teams),
                values=[[1/len(teams)] * len(teams)]
            )
            self.model.add_cpds(team_cpd)
            
            # Create CPDs for steps conditioned on team selection
            for node in step_nodes:
                step = int(node.split('_')[1]) - 1
                step_users = self.var_manager.get_authorized_users(step)
                
                # Create probability table
                cpd_values = []
                for team_idx, team in enumerate(teams):
                    team_users = team & step_users
                    probs = []
                    for user in step_users:
                        probs.append(1/len(team_users) if user in team_users else 0)
                    cpd_values.append(probs)
                    
                step_cpd = TabularCPD(
                    variable=node,
                    variable_card=len(step_users),
                    values=cpd_values,
                    evidence=[team_node],
                    evidence_card=[len(teams)],
                    state_names={node: [u+1 for u in step_users]}
                )
                self.model.add_cpds(step_cpd)
                
        return True

    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        violations = []
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
        return violations


class PGMPYSUALConstraint(PGMPYConstraint):
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

    def add_to_network(self) -> bool:
        """Add SUAL constraints to network"""
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for scope_idx, (scope, h, super_users) in enumerate(self.instance.sual):
            # Create counting node for scope
            count_node = f"SUAL_Count_{scope_idx}"
            
            # Connect steps to counting node
            step_nodes = [self.var_manager.get_step_node(s) for s in scope]
            step_nodes = [n for n in step_nodes if n]
            
            for node in step_nodes:
                self.model.add_edge(node, count_node)
                
            # Create CPDs that enforce SUAL constraint
            # Complex CPD creation that ensures super user when count ≤ h
            # [Implementation details for CPD creation...]
                
        return True

    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        violations = []
        for scope, h, super_users in self.instance.sual:
            assigned_users = {assignment[s+1] for s in scope if s+1 in assignment}
            if len(assigned_users) <= h:
                if not any(user in super_users for user in assigned_users):
                    violations.append(
                        f"SUAL violation: No super user assigned when {len(assigned_users)} "
                        f"users assigned to scope"
                    )
        return violations


class PGMPYWangLiConstraint(PGMPYConstraint):
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

    def add_to_network(self) -> bool:
        """Add Wang-Li constraints to network"""
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for scope_idx, (scope, departments) in enumerate(self.instance.wang_li):
            # Create department selection node
            dept_node = f"Dept_{scope_idx}"
            
            # Connect to steps in scope
            step_nodes = [self.var_manager.get_step_node(s) for s in scope]
            step_nodes = [n for n in step_nodes if n]
            
            for node in step_nodes:
                self.model.add_edge(dept_node, node)
                
            # Create CPDs that enforce department constraints
            # Similar to one-team constraint implementation
            # [Implementation details for CPD creation...]
                
        return True

    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        violations = []
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
        return violations


class PGMPYAssignmentDependentConstraint(PGMPYConstraint):
    def check_feasibility(self) -> Tuple[bool, List[str]]:
        errors = []
        
        for s1, s2, source_users, target_users in self.instance.ada:
            auth_source = self.var_manager.get_authorized_users(s1)
            if not auth_source.intersection(source_users):
                errors.append(
                    f"No authorized users from source set for step {s1+1}"
                )
                continue
                
            auth_target = self.var_manager.get_authorized_users(s2)
            if not auth_target.intersection(target_users):
                errors.append(
                    f"No authorized users from target set for step {s2+1}"
                )
                
        return len(errors) == 0, errors

    def add_to_network(self) -> bool:
        """Add ADA constraints to network"""
        is_feasible, errors = self.check_feasibility()
        if not is_feasible:
            return False
            
        for ada_idx, (s1, s2, source_users, target_users) in enumerate(self.instance.ada):
            node1 = self.var_manager.get_step_node(s1)
            node2 = self.var_manager.get_step_node(s2)
            
            if node1 and node2:
                self.model.add_edge(node1, node2)
                
                # Create CPD that enforces the ADA constraint
                auth_users1 = list(self.var_manager.get_authorized_users(s1))
                auth_users2 = list(self.var_manager.get_authorized_users(s2))
                
                # Create probability table
                cpd_values = []
                for u1 in auth_users1:
                    row = []
                    if u1 in source_users:
                        # Must use target user
                        valid_users = [u for u in auth_users2 if u in target_users]
                        prob = 1.0/len(valid_users) if valid_users else 0.0
                        for u2 in auth_users2:
                            row.append(prob if u2 in target_users else 0.0)
                    else:
                        # Can use any authorized user
                        prob = 1.0/len(auth_users2)
                        row = [prob] * len(auth_users2)
                    cpd_values.append(row)
                    
                cpd = TabularCPD(
                    variable=node2,
                    variable_card=len(auth_users2),
                    values=cpd_values,
                    evidence=[node1],
                    evidence_card=[len(auth_users1)],
                    state_names={
                        node1: [u+1 for u in auth_users1],
                        node2: [u+1 for u in auth_users2]
                    }
                )
                self.model.add_cpds(cpd)
                
        return True

    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        violations = []
        for s1, s2, source_users, target_users in self.instance.ada:
            if (s1+1 in assignment and s2+1 in assignment and 
                assignment[s1+1] in source_users):
                if assignment[s2+1] not in target_users:
                    violations.append(
                        f"ADA violation: Step {s2+1} not assigned to target user when "
                        f"step {s1+1} assigned to source user"
                    )
        return violations
    

class PGMPYConstraintManager:
    """Manages PGMPY WSP constraints"""
    def __init__(self, model: BayesianNetwork, instance, var_manager: PGMPYVariableManager):
        self.model = model
        self.instance = instance
        self.var_manager = var_manager
        
        # Initialize all constraints
        self.constraints = {
            'authorization': PGMPYAuthorizationConstraint(model, instance, var_manager),
            'binding_of_duty': PGMPYBindingOfDutyConstraint(model, instance, var_manager),
            'separation_of_duty': PGMPYSeparationOfDutyConstraint(model, instance, var_manager),
            'at_most_k': PGMPYAtMostKConstraint(model, instance, var_manager),
            'one_team': PGMPYOneTeamConstraint(model, instance, var_manager),
            'super_user_at_least': PGMPYSUALConstraint(model, instance, var_manager),
            'wang_li': PGMPYWangLiConstraint(model, instance, var_manager),
            'assignment_dependent': PGMPYAssignmentDependentConstraint(model, instance, var_manager)
        }
        
        self.active_constraints = {}

    def add_constraints(self, active_constraints: dict) -> Tuple[bool, List[str]]:
        """Add active constraints to the Bayesian Network"""
        errors = []
        self.active_constraints = active_constraints
        
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
                        
                    if not constraint.add_to_network():
                        errors.append(f"Failed to add {name} constraints to Bayesian Network")
                    
        return len(errors) == 0, errors

    def verify_assignment(self, assignment: Dict[int, int]) -> List[str]:
        """Verify all constraints for an assignment"""
        all_violations = []
        
        for name, constraint in self.constraints.items():
            if self.active_constraints.get(name, True):
                violations = constraint.verify_assignment(assignment)
                all_violations.extend(violations)
                
        return all_violations
        
    
    def check_all_feasibility(self) -> Tuple[bool, List[str]]:
        """Check if all active constraints are potentially feasible"""
        errors = []
        for name, constraint in self.constraints.items():
            if self.active_constraints.get(name, True):
                is_feasible, constraint_errors = constraint.check_feasibility()
                if not is_feasible:
                    errors.extend(constraint_errors)
        return len(errors) == 0, errors

    def get_probability_distribution(self, step: int) -> Dict[int, float]:
        """Get probability distribution over users for a step"""
        step_node = self.var_manager.get_step_node(step)
        if not step_node:
            return {}
            
        cpd = self.model.get_cpds(step_node)
        if not cpd:
            return {}
            
        return {
            state: prob 
            for state, prob in zip(cpd.state_names[step_node], cpd.values.flatten())
        }

    def update_network_evidence(self, evidence: Dict[int, int]):
        """Update network with observed assignments"""
        evidence_nodes = {}
        for step, user in evidence.items():
            node = self.var_manager.get_step_node(step - 1)
            if node:
                evidence_nodes[node] = user
                
        # Update model with evidence
        self.model.do(evidence_nodes)

    def get_most_likely_assignment(self) -> Dict[int, int]:
        """Get most likely assignment based on current network state"""
        assignment = {}
        for step in range(self.instance.number_of_steps):
            node = self.var_manager.get_step_node(step)
            if node:
                cpd = self.model.get_cpds(node)
                if cpd:
                    # Get most likely user
                    probs = cpd.values.flatten()
                    max_idx = np.argmax(probs)
                    user = cpd.state_names[node][max_idx]
                    assignment[step + 1] = user
                    
        return assignment

    def get_constraint_violation_probabilities(self) -> Dict[str, float]:
        """Calculate probability of constraint violations"""
        violation_probs = {}
        
        # For each constraint type
        for name, constraint in self.constraints.items():
            if self.active_constraints.get(name, True):
                prob = 0.0
                
                if name == 'binding_of_duty':
                    # Calculate probability of BOD violations
                    for s1, s2 in self.instance.BOD:
                        node1 = self.var_manager.get_step_node(s1)
                        node2 = self.var_manager.get_step_node(s2)
                        if node1 and node2:
                            # Get joint probability of different users
                            cpd = self.model.get_cpds(node2)
                            if cpd:
                                values = cpd.values
                                # Sum probabilities where users differ
                                prob += 1 - np.trace(values)

                elif name == 'separation_of_duty':
                    # Calculate probability of SOD violations
                    for s1, s2 in self.instance.SOD:
                        node1 = self.var_manager.get_step_node(s1)
                        node2 = self.var_manager.get_step_node(s2)
                        if node1 and node2:
                            # Get joint probability of same user
                            cpd = self.model.get_cpds(node2)
                            if cpd:
                                values = cpd.values
                                # Sum probabilities where users are same
                                prob += np.trace(values)

                # Similar calculations for other constraints...
                violation_probs[name] = prob
                
        return violation_probs

    def calculate_entropy(self, step: int) -> float:
        """Calculate entropy of assignment distribution for a step"""
        probs = self.get_probability_distribution(step)
        if not probs:
            return 0.0
            
        entropy = 0.0
        for p in probs.values():
            if p > 0:
                entropy -= p * np.log2(p)
        return entropy

    def find_most_constrained_steps(self) -> List[Tuple[int, float]]:
        """Find steps with lowest entropy (most constrained)"""
        entropies = []
        for step in range(self.instance.number_of_steps):
            entropy = self.calculate_entropy(step)
            entropies.append((step + 1, entropy))
            
        # Sort by entropy (ascending)
        return sorted(entropies, key=lambda x: x[1])

    def get_marginal_probabilities(self) -> Dict[str, Dict[int, float]]:
        """Get marginal probabilities for all steps"""
        marginals = {}
        
        for step in range(self.instance.number_of_steps):
            node = self.var_manager.get_step_node(step)
            if node:
                probs = self.get_probability_distribution(step)
                if probs:
                    marginals[node] = probs
                    
        return marginals

    def check_network_consistency(self) -> Tuple[bool, List[str]]:
        """Check if Bayesian Network is consistent"""
        errors = []
        
        try:
            # Check if network is DAG
            if not nx.is_directed_acyclic_graph(self.model):
                errors.append("Network contains cycles")
                
            # Check CPD consistency
            if not self.model.check_model():
                errors.append("CPDs are inconsistent")
                
            # Check if all variables have CPDs
            for node in self.model.nodes():
                if not self.model.get_cpds(node):
                    errors.append(f"Missing CPD for node {node}")
                    
        except Exception as e:
            errors.append(f"Error checking network: {str(e)}")
            
        return len(errors) == 0, errors

    def suggest_relaxation(self, violations: List[str]) -> List[str]:
        """Suggest constraints to relax based on violation patterns"""
        suggestions = []
        
        # Count violations by type
        violation_counts = defaultdict(int)
        for violation in violations:
            for name in self.constraints:
                if name.lower() in violation.lower():
                    violation_counts[name] += 1
                    
        # Sort constraints by violation count
        sorted_constraints = sorted(
            violation_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Generate suggestions
        for constraint, count in sorted_constraints:
            if count > 0:
                suggestions.append(
                    f"Consider relaxing {constraint} constraint "
                    f"({count} violations)"
                )
                
        return suggestions