import random
from typing import List, Dict, Tuple
from collections import defaultdict


class InstanceGenerator:
    def __init__(self, k: int, n: int, seed: int = None):
        """
        Initialize WSP instance generator
        k: number of steps
        n: number of users
        seed: random seed for reproducibility
        """
        self.k = k
        self.n = n
        if seed is not None:
            random.seed(seed)
            
        # Instance data
        self.authorizations = defaultdict(set)  # step -> set of authorized users
        self.constraints = []  # List of constraint tuples
        
    def generate_authorizations(self, density: float = 0.2):
        """Generate random authorizations with given density
        
        density: probability of a user being authorized for a step
        """
        self.authorizations.clear()
        
        # Initialize empty authorization sets for each step
        for step in range(self.k):
            self.authorizations[step] = set()
            
        # For each user, randomly decide step authorizations
        for user in range(self.n):
            # Decide if this user will have any authorizations
            if random.random() < 0.8:  # 80% chance user will have authorizations
                # For each step, randomly decide if user is authorized
                assigned_steps = []
                for step in range(self.k):
                    if random.random() < density:
                        self.authorizations[step].add(user)
                        assigned_steps.append(step)
                
                # Ensure each user with authorizations has at least one
                if not assigned_steps and random.random() < 0.8:  # 80% chance to give at least one auth
                    step = random.randint(0, self.k - 1)
                    self.authorizations[step].add(user)
        
        # Ensure each step has at least one authorized user
        for step in range(self.k):
            if not self.authorizations[step]:
                user = random.randint(0, self.n - 1)
                self.authorizations[step].add(user)
            
    def _add_binding_of_duty(self, num_constraints: int, used_steps: set):
        """Add binding of duty constraints with exact format"""
        if num_constraints <= 0:
            return
        
        possible_pairs = []
        for s1 in range(self.k):
            if s1 in used_steps:
                continue
            for s2 in range(s1 + 1, self.k):
                if s2 in used_steps:
                    continue
                # Check common authorized users
                common_users = [u for u in range(self.n) 
                            if u in self.authorizations[s1] and 
                                u in self.authorizations[s2]]
                if len(common_users) >= 2:
                    possible_pairs.append((s1, s2))
        
        if possible_pairs:
            selected = random.sample(possible_pairs, min(num_constraints, len(possible_pairs)))
            for s1, s2 in selected:
                self.constraints.append(('BOD', (s1, s2)))
                used_steps.update([s1, s2])

    def _add_separation_of_duty(self, num_constraints: int, used_steps: set):
        """Add separation of duty constraints with exact format"""
        if num_constraints <= 0:
            return
        
        possible_pairs = []
        for s1 in range(self.k):
            if s1 in used_steps:
                continue
            for s2 in range(s1 + 1, self.k):
                if s2 in used_steps:
                    continue
                # Check there are enough different authorized users
                auth_s1 = set(self.authorizations[s1])
                auth_s2 = set(self.authorizations[s2])
                if len(auth_s1) >= 2 and len(auth_s2) >= 2 and auth_s1 != auth_s2:
                    possible_pairs.append((s1, s2))
        
        if possible_pairs:
            selected = random.sample(possible_pairs, min(num_constraints, len(possible_pairs)))
            for s1, s2 in selected:
                self.constraints.append(('SOD', (s1, s2)))
                used_steps.update([s1, s2])

    def _add_at_most_k_constraints(self, num_constraints: int, used_steps: set):
        """Add at-most-k constraints"""
        if num_constraints <= 0:
            return
            
        max_steps_per_constraint = 5  # Based on example files
        min_steps_per_constraint = 3
        
        # Generate constraints
        for _ in range(num_constraints):
            # Select scope
            available_steps = [s for s in range(self.k) if s not in used_steps]
            if len(available_steps) < min_steps_per_constraint:
                break
                
            scope_size = random.randint(min_steps_per_constraint, 
                                    min(max_steps_per_constraint, len(available_steps)))
            scope = sorted(random.sample(available_steps, scope_size))
            
            # Calculate reasonable k value
            min_users = float('inf')
            for step in scope:
                auth_users = len(self.authorizations[step])
                min_users = min(min_users, auth_users)
                
            k = min(3, min_users - 1)  # Based on example files using k=3
            if k < 2:  # Ensure k is at least 2
                continue
                
            self.constraints.append(('AT-MOST-K', (k, tuple(scope))))
            used_steps.update(scope)
            
    def _add_sual_constraints(self, num_constraints: int):
        """Add Super-User-At-Least constraints"""
        if num_constraints <= 0:
            return
            
        # Select super users (about 20% of total users)
        num_super_users = max(2, self.n // 5)
        super_users = set(random.sample(range(self.n), num_super_users))
        
        # Find steps where at least some super users are authorized
        valid_steps = []
        for step in range(self.k):
            if any(u in self.authorizations[step] for u in super_users):
                valid_steps.append(step)
                
        if len(valid_steps) < 2:
            return
            
        for _ in range(num_constraints):
            # Select scope size between 2-5 steps
            scope_size = random.randint(2, min(5, len(valid_steps)))
            scope = sorted(random.sample(valid_steps, scope_size))
            
            # Calculate reasonable h value based on authorized users
            min_auth = min(len(self.authorizations[s]) for s in scope)
            h = random.randint(2, min(min_auth - 1, 4))
            
            # Format: Super-user-at-least h s1 s2 s3 u1 u2 u3
            steps_str = ' '.join(f's{s+1}' for s in scope)
            users_str = ' '.join(f'u{u+1}' for u in sorted(super_users))
            self.constraints.append(('SUAL', (h, scope, super_users)))

    def _add_wang_li_constraints(self, num_constraints: int, users_per_dept: int):
        """Add Wang-Li constraints"""
        if num_constraints <= 0:
            return
            
        if not users_per_dept:
            users_per_dept = self.n // 4  # Default to 4 departments
            
        # Create balanced departments
        all_users = list(range(self.n))
        random.shuffle(all_users)
        departments = []
        
        # Ensure each department has users with sufficient authorizations
        pos = 0
        while pos < len(all_users) and len(departments) < (self.n // users_per_dept):
            dept = []
            while len(dept) < users_per_dept and pos < len(all_users):
                user = all_users[pos]
                auth_steps = sum(1 for s in range(self.k) if user in self.authorizations[s])
                if auth_steps >= 2:  # User must be authorized for at least 2 steps
                    dept.append(user)
                pos += 1
            if dept:
                departments.append(tuple(sorted(dept)))
                
        if len(departments) < 2:
            return
            
        for _ in range(num_constraints):
            # Find steps that can be satisfied by at least one department
            valid_steps = []
            for step in range(self.k):
                for dept in departments:
                    if any(user in self.authorizations[step] for user in dept):
                        valid_steps.append(step)
                        break
                        
            if len(valid_steps) < 2:
                continue
                
            # Select scope
            scope_size = random.randint(2, min(5, len(valid_steps)))
            scope = sorted(random.sample(valid_steps, scope_size))
            
            # Format: Wang-li s1 s2 s3 (u1 u2) (u3 u4 u5)
            self.constraints.append(('WANG-LI', (scope, departments)))

    def _add_ada_constraints(self, num_constraints: int):
        """Add Assignment-Dependent Authorization constraints"""
        if num_constraints <= 0:
            return
            
        # Find steps with sufficient authorized users
        valid_steps = []
        for step in range(self.k):
            if len(self.authorizations[step]) >= 3:
                valid_steps.append(step)
                
        if len(valid_steps) < 2:
            return
            
        for _ in range(num_constraints):
            s1 = random.choice(valid_steps)
            s2 = random.choice([s for s in valid_steps if s != s1])
            
            # Select source users from those authorized for s1
            auth_s1 = list(self.authorizations[s1])
            source_size = random.randint(1, min(len(auth_s1), self.n // 4))
            source_users = tuple(sorted(random.sample(auth_s1, source_size)))
            
            # Select target users ensuring some are authorized for s2
            auth_s2 = list(self.authorizations[s2])
            target_size = random.randint(1, min(len(auth_s2), self.n // 4))
            target_users = tuple(sorted(random.sample(auth_s2, target_size)))
            
            # Format: Assignment-dependent s1 s2 (u1 u2) (u3 u4 u5)
            self.constraints.append(('ADA', (s1, s2, source_users, target_users)))
            
    def add_constraints(self, 
                    auth_density: float = 0.2,
                    num_sod: int = 0,
                    num_bod: int = 0,
                    num_atmost: int = 0,
                    num_sual: int = 0,
                    num_wangli: int = 0,
                    num_ada: int = 0,
                    users_per_dept: int = None) -> Dict:
        """Generate complete WSP instance with specified constraints"""
        # Generate fresh authorizations with validation
        self.generate_authorizations(auth_density)
        
        # Clear existing constraints
        self.constraints = []
        
        # Track assigned steps to avoid conflicts
        used_steps = set()
        
        # Add core constraints first
        self._add_binding_of_duty(num_bod, used_steps)
        self._add_separation_of_duty(num_sod, used_steps)
        self._add_at_most_k_constraints(num_atmost, used_steps)
        
        # Add new constraint types
        # self._add_sual_constraints(num_sual)
        # self._add_wang_li_constraints(num_wangli, users_per_dept)
        # self._add_ada_constraints(num_ada)
        
        return {
            'k': self.k,
            'n': self.n,
            'authorizations': dict(self.authorizations),
            'constraints': self.constraints
        }
        
    def write_instance(self, filename: str, instance: Dict = None):
        if instance is None:
            instance = self.add_constraints()
        
        # Collect all authorization lines
        auth_lines = []
        for user in range(instance['n']):
            auth_steps = [s for s in range(instance['k']) 
                        if user in instance['authorizations'][s]]
            if auth_steps:  # Only write if user has any authorizations
                steps_str = ' '.join(f's{s+1}' for s in sorted(auth_steps))
                auth_lines.append(f"Authorisations u{user+1} {steps_str}")
        
        # Collect all constraint lines
        constraint_lines = []
        # 1. Binding-of-duty constraints
        for ctype, data in instance['constraints']:
            if ctype == 'BOD':
                s1, s2 = data
                constraint_lines.append(f"Binding-of-duty s{s1+1} s{s2+1}")
        
        # 2. Separation-of-duty constraints
        for ctype, data in instance['constraints']:
            if ctype == 'SOD':
                s1, s2 = data
                constraint_lines.append(f"Separation-of-duty s{s1+1} s{s2+1}")
        
        # Calculate total number of lines (auth lines + constraint lines)
        total_lines = len(auth_lines) + len(constraint_lines)
        
        # Write to file
        with open(filename, 'w') as f:
            # Write header with correct number of total lines
            f.write(f"#Steps: {instance['k']}\n")
            f.write(f"#Users: {instance['n']}\n")
            f.write(f"#Constraints: {total_lines}\n")
            
            # Write authorization lines
            for line in auth_lines:
                f.write(line + "\n")
            
            # Write constraint lines
            for line in constraint_lines:
                f.write(line + "\n")
