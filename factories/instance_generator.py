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
        """Generate random authorizations with given density"""
        self.authorizations.clear()
        
        for step in range(self.k):
            num_users = max(1, int(density * self.n))  # Ensure at least one user
            authorized = set(random.sample(range(self.n), num_users))
            self.authorizations[step] = authorized
            
    def add_sod_constraints(self, num_constraints: int):
        """Add random separation of duty constraints"""
        possible_pairs = [(i, j) for i in range(self.k) 
                         for j in range(i+1, self.k)]
        if num_constraints > len(possible_pairs):
            num_constraints = len(possible_pairs)
            
        selected = random.sample(possible_pairs, num_constraints)
        for s1, s2 in selected:
            self.constraints.append(('SOD', (s1, s2)))
            
    def add_bod_constraints(self, num_constraints: int):
        """Add random binding of duty constraints"""
        # Only add BOD where there are common authorized users
        valid_pairs = []
        for s1 in range(self.k):
            for s2 in range(s1+1, self.k):
                common = self.authorizations[s1] & self.authorizations[s2]
                if common:
                    valid_pairs.append((s1, s2))
                    
        if num_constraints > len(valid_pairs):
            num_constraints = len(valid_pairs)
            
        selected = random.sample(valid_pairs, num_constraints)
        for s1, s2 in selected:
            self.constraints.append(('BOD', (s1, s2)))
            
    def add_at_most_k_constraints(self, num_constraints: int, k_range: Tuple[int, int] = (2, 4)):
        """Add random at-most-k constraints"""
        for _ in range(num_constraints):
            k_val = random.randint(*k_range)
            scope_size = random.randint(k_val+1, min(self.k, k_val+3))
            scope = set(random.sample(range(self.k), scope_size))
            self.constraints.append(('AT-MOST-K', (k_val, scope)))
            
    def add_sual_constraints(self, num_constraints: int, num_super_users: int, h_range: Tuple[int, int] = (2, 4)):
        """Add random super-user at-least constraints"""
        # Select super users
        super_users = set(random.sample(range(self.n), num_super_users))
        
        for _ in range(num_constraints):
            h = random.randint(*h_range)
            scope_size = random.randint(2, min(5, self.k))
            scope = set(random.sample(range(self.k), scope_size))
            self.constraints.append(('SUAL', (scope, super_users, h)))
            
    def add_wang_li_constraints(self, num_constraints: int, num_departments: int):
        """Add random Wang-Li constraints"""
        # Create departments (non-overlapping for simplicity)
        dept_size = self.n // num_departments
        users = list(range(self.n))
        random.shuffle(users)
        departments = []
        for i in range(num_departments):
            start = i * dept_size
            end = start + dept_size if i < num_departments-1 else self.n
            departments.append(set(users[start:end]))
            
        for _ in range(num_constraints):
            scope_size = random.randint(2, min(5, self.k))
            scope = set(random.sample(range(self.k), scope_size))
            self.constraints.append(('WANG-LI', (scope, departments)))
            
    def add_assignment_dependent_constraints(self, num_constraints: int):
        """Add random assignment-dependent constraints"""
        for _ in range(num_constraints):
            s1 = random.randint(0, self.k-1)
            s2 = random.randint(0, self.k-1)
            if s1 == s2:
                continue
                
            # Select random subsets of users for source and target
            source_size = random.randint(1, self.n//4)
            target_size = random.randint(1, self.n//4)
            source_users = set(random.sample(range(self.n), source_size))
            target_users = set(random.sample(range(self.n), target_size))
            
            self.constraints.append(('ADA', (s1, s2, source_users, target_users)))
            
    def generate_instance(self, 
                         auth_density: float = 0.2,
                         num_sod: int = 0,
                         num_bod: int = 0,
                         num_atmost: int = 0,
                         num_sual: int = 0,
                         num_wangli: int = 0,
                         num_ada: int = 0) -> Dict:
        """Generate complete WSP instance with specified constraints"""
        # Generate fresh authorizations
        self.generate_authorizations(auth_density)
        
        # Clear existing constraints
        self.constraints.clear()
        
        # Add requested constraints
        self.add_sod_constraints(num_sod)
        self.add_bod_constraints(num_bod)
        self.add_at_most_k_constraints(num_atmost)
        self.add_sual_constraints(num_sual, num_super_users=self.n//10)
        self.add_wang_li_constraints(num_wangli, num_departments=4)
        self.add_assignment_dependent_constraints(num_ada)
        
        return {
            'k': self.k,
            'n': self.n,
            'authorizations': dict(self.authorizations),
            'constraints': self.constraints
        }
        
    def write_instance(self, filename: str, instance: Dict = None):
        """Write instance to file in standard format"""
        if instance is None:
            instance = self.generate_instance()
            
        with open(filename, 'w') as f:
            # Write header
            f.write(f"#Steps: {instance['k']}\n")
            f.write(f"#Users: {instance['n']}\n")
            f.write(f"#Constraints: {len(instance['constraints'])}\n")
            
            # Write authorizations
            for step, users in instance['authorizations'].items():
                if users:  # Only write non-empty authorizations
                    users_str = ' '.join(f's{u+1}' for u in sorted(users))
                    f.write(f"Authorisations u{step+1} {users_str}\n")
            
            # Write constraints
            for ctype, data in instance['constraints']:
                if ctype == 'SOD':
                    s1, s2 = data
                    f.write(f"Separation-of-duty s{s1+1} s{s2+1}\n")
                elif ctype == 'BOD':
                    s1, s2 = data
                    f.write(f"Binding-of-duty s{s1+1} s{s2+1}\n")
                elif ctype == 'AT-MOST-K':
                    k_val, scope = data
                    steps_str = ' '.join(f's{s+1}' for s in sorted(scope))
                    f.write(f"At-most-k {k_val} {steps_str}\n")
                elif ctype == 'SUAL':
                    scope, super_users, h = data
                    steps_str = ' '.join(f's{s+1}' for s in sorted(scope))
                    users_str = ' '.join(f'u{u+1}' for u in sorted(super_users))
                    f.write(f"Super-user-at-least {h} {steps_str} {users_str}\n")
                elif ctype == 'WANG-LI':
                    scope, departments = data
                    steps_str = ' '.join(f's{s+1}' for s in sorted(scope))
                    depts_str = ' '.join(
                        f"({' '.join(f'u{u+1}' for u in sorted(dept))})" 
                        for dept in departments
                    )
                    f.write(f"Wang-li {steps_str} {depts_str}\n")
                elif ctype == 'ADA':
                    s1, s2, source_users, target_users = data
                    source_str = ' '.join(f'u{u+1}' for u in sorted(source_users))
                    target_str = ' '.join(f'u{u+1}' for u in sorted(target_users))
                    f.write(f"Assignment-dependent s{s1+1} s{s2+1} ({source_str}) ({target_str})\n")
                    
    @staticmethod
    def generate_phase_transition_set(
            k: int, n: int, num_instances: int = 100,
            base_density: float = 0.2,
            constraint_step: int = 1) -> List[Dict]:
        """
        Generate a set of instances around the phase transition point
        Returns list of (instance, is_satisfiable) tuples
        """
        instances = []
        gen = InstanceGenerator(k, n)
        
        # Start with few constraints and increase
        num_constraints = k  # Start with k constraints
        while len(instances) < num_instances:
            instance = gen.generate_instance(
                auth_density=base_density,
                num_sod=num_constraints // 2,
                num_bod=num_constraints // 4,
                num_atmost=num_constraints // 4
            )
            
            # Solve instance to determine satisfiability
            # TODO: Implement or connect to solver
            is_satisfiable = True  # Placeholder
            
            instances.append((instance, is_satisfiable))
            num_constraints += constraint_step
            
        return instances
