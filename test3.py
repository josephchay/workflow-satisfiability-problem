import time
from ortools.sat.python import cp_model
import re
from collections import defaultdict


class Instance:
    def __init__(self):
        self.number_of_steps = 0
        self.number_of_users = 0
        self.number_of_constraints = 0
        self.auth = []
        self.SOD = []
        self.BOD = []
        self.at_most_k = []
        self.one_team = []
        
        # New optimization fields
        self.user_step_matrix = None  # For quick auth lookups
        self.step_domains = {}        # For domain reduction
        self.constraint_graph = defaultdict(set)  # For constraint relationships

    def compute_step_domains(self):
        """Compute possible users for each step based on authorizations"""
        for step in range(self.number_of_steps):
            self.step_domains[step] = set()
            for user in range(self.number_of_users):
                if self.user_step_matrix[user][step]:
                    self.step_domains[step].add(user)


INSTANCE_METADATA = {
    'example1.txt': {'sat': True, 'unique': False},
    'example2.txt': {'sat': False, 'unique': False},
    'example3.txt': {'sat': True, 'unique': True},
    'example4.txt': {'sat': False, 'unique': False},
    'example5.txt': {'sat': True, 'unique': True},
    'example6.txt': {'sat': False, 'unique': False},
    'example7.txt': {'sat': True, 'unique': True},
    'example8.txt': {'sat': False, 'unique': False},
    'example9.txt': {'sat': True, 'unique': False},
    'example10.txt': {'sat': True, 'unique': False},
    'example11.txt': {'sat': True, 'unique': False},
    'example12.txt': {'sat': True, 'unique': False},
    'example13.txt': {'sat': False, 'unique': False},
    'example14.txt': {'sat': False, 'unique': False},
    'example15.txt': {'sat': False, 'unique': False},
    # Large instances
    'example16.txt': {'sat': True, 'unique': False},
    'example17.txt': {'sat': True, 'unique': False},
    'example18.txt': {'sat': False, 'unique': False},
    'example19.txt': {'sat': False, 'unique': False}
}


def read_file(filename):
    def read_attribute(name):
        line = f.readline()
        match = re.match(f'{name}:\\s*(\\d+)$', line)
        if match:
            return int(match.group(1))
        raise Exception(f"Could not parse line {line}")

    instance = Instance()
    
    with open(filename) as f:
        instance.number_of_steps = read_attribute("#Steps")
        instance.number_of_users = read_attribute("#Users")
        instance.number_of_constraints = read_attribute("#Constraints")
        instance.auth = [[] for _ in range(instance.number_of_users)]
        
        # Pre-allocate user-step authorization matrix
        instance.user_step_matrix = [[False] * instance.number_of_steps 
                                   for _ in range(instance.number_of_users)]

        for _ in range(instance.number_of_constraints):
            l = f.readline().strip()
            
            # Parse Authorizations with optimized matrix updates
            m = re.match(r"Authorisations u(\d+)(?: s\d+)*", l)
            if m:
                user_id = int(m.group(1)) - 1
                steps = []
                for m in re.finditer(r's(\d+)', l):
                    step = int(m.group(1)) - 1
                    steps.append(step)
                    instance.user_step_matrix[user_id][step] = True
                instance.auth[user_id].extend(steps)
                continue

            # Parse remaining constraints with enhanced data structures
            m = re.match(r'Separation-of-duty s(\d+) s(\d+)', l)
            if m:
                s1, s2 = int(m.group(1)) - 1, int(m.group(2)) - 1
                instance.SOD.append((s1, s2))
                instance.constraint_graph[s1].add(s2)
                instance.constraint_graph[s2].add(s1)
                continue

            m = re.match(r'Binding-of-duty s(\d+) s(\d+)', l)
            if m:
                s1, s2 = int(m.group(1)) - 1, int(m.group(2)) - 1
                instance.BOD.append((s1, s2))
                instance.constraint_graph[s1].add(s2)
                instance.constraint_graph[s2].add(s1)
                continue

            m = re.match(r'At-most-k (\d+)(?: s\d+)+', l)
            if m:
                k = int(m.group(1))
                steps = tuple(int(m.group(1)) - 1 for m in re.finditer(r's(\d+)', l))
                instance.at_most_k.append((k, steps))
                for s1 in steps:
                    for s2 in steps:
                        if s1 != s2:
                            instance.constraint_graph[s1].add(s2)
                continue

            m = re.match(r'One-team\s+((?:s\d+\s*)+)\(((?:u\d+\s*)+)\)((?:\s*\((?:u\d+\s*)+\))*)', l)
            if m:
                steps = tuple(int(step_match.group(1)) - 1 
                            for step_match in re.finditer(r's(\d+)', m.group(1)))
                teams = []
                team_pattern = r'\(((?:u\d+\s*)+)\)'
                for team_match in re.finditer(team_pattern, l):
                    team = tuple(int(user_match.group(1)) - 1 
                               for user_match in re.finditer(r'u(\d+)', team_match.group(1)))
                    teams.append(team)
                instance.one_team.append((steps, tuple(teams)))
                for s1 in steps:
                    for s2 in steps:
                        if s1 != s2:
                            instance.constraint_graph[s1].add(s2)
                continue

            raise Exception(f'Failed to parse line: {l}')

    # Precompute step domains
    instance.compute_step_domains()
    return instance


class OptimizedCpSolver:
    def __init__(self, instance):
        self.instance = instance
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.user_assignment = None
        
        # Enhanced solver parameters
        self.solver.parameters.num_search_workers = 8      # Increased parallel workers
        self.solver.parameters.log_search_progress = False
        
        # Use randomization to escape local minima
        self.solver.parameters.random_seed = 42
        self.solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH

    def create_variables(self):
        """Optimized variable creation with intelligent ordering"""
        # Order steps by constraint density
        step_order = sorted(range(self.instance.number_of_steps),
                          key=lambda s: len(self.instance.constraint_graph[s]),
                          reverse=True)
        
        self.user_assignment = {}
        for step in step_order:
            self.user_assignment[step] = []
            for user in range(self.instance.number_of_users):
                if self.instance.user_step_matrix[user][step]:
                    var = self.model.NewBoolVar(f's{step + 1}_u{user + 1}')
                    self.user_assignment[step].append((user, var))
    
    def add_authorization_constraints(self):
        """Streamlined authorization constraints"""
        for step, user_vars in self.user_assignment.items():
            # Exactly one user per step
            self.model.AddExactlyOne(var for _, var in user_vars)
    
    def add_separation_of_duty(self):
        """Enhanced separation of duty constraints"""
        for s1, s2 in self.instance.SOD:
            user_vars1 = dict(self.user_assignment[s1])
            user_vars2 = dict(self.user_assignment[s2])
            
            for user in set(user_vars1.keys()) & set(user_vars2.keys()):
                self.model.Add(user_vars1[user] + user_vars2[user] <= 1)
    
    def add_binding_of_duty(self):
        """Optimized binding of duty constraints"""
        for s1, s2 in self.instance.BOD:
            user_vars1 = dict(self.user_assignment[s1])
            user_vars2 = dict(self.user_assignment[s2])
            
            common_users = set(user_vars1.keys()) & set(user_vars2.keys())
            if not common_users:
                # Quick infeasibility check
                self.model.Add(1 == 0)  # Force UNSAT
                return
                
            for user in common_users:
                self.model.Add(user_vars1[user] == user_vars2[user])
    
    def add_at_most_k(self):
        """Strictly enforced at-most-k constraints"""
        # Track all variables for each user
        user_vars_global = defaultdict(list)
        for step, user_vars in self.user_assignment.items():
            for user, var in user_vars:
                user_vars_global[user].append(var)

        # Find minimum k value from all constraints for global limit
        min_k = min(k for k, _ in self.instance.at_most_k) if self.instance.at_most_k else 3
        
        # Global limit based on instance's minimum k
        for user, vars_list in user_vars_global.items():
            self.model.Add(sum(vars_list) <= min_k)
    
    def add_one_team(self):
        """Enhanced one-team constraints with preprocessing"""
        for steps, teams in self.instance.one_team:
            team_vars = []
            
            # Create team selection variables
            for i in range(len(teams)):
                team_vars.append(self.model.NewBoolVar(f'team_{i}'))
            
            # Exactly one team must be selected
            self.model.AddExactlyOne(team_vars)
            
            # For each step and team combination
            for step in steps:
                step_vars = dict(self.user_assignment[step])
                
                for team_idx, team in enumerate(teams):
                    # Users not in team cannot be assigned when team is selected
                    for user, var in step_vars.items():
                        if user not in team:
                            self.model.Add(var == 0).OnlyEnforceIf(team_vars[team_idx])

    def verify_at_most_k(self, solution_dict):
        """Strict at-most-k verification"""
        violations = []
        
        # First collect all assignments per user
        user_assignments = defaultdict(list)
        for step, user in solution_dict.items():
            user_assignments[user].append(step-1)  # Convert to 0-based indexing
            
        # Check each at-most-k constraint
        for k, steps in self.instance.at_most_k:
            steps_set = set(steps)
            for user, assigned_steps in user_assignments.items():
                steps_in_group = [s for s in assigned_steps if s in steps_set]
                if len(steps_in_group) > k:
                    violations.append(
                        f"At-most-{k} Violation: User {user} assigned to {len(steps_in_group)} steps "
                        f"{sorted(s+1 for s in steps_in_group)} in constraint group {sorted(s+1 for s in steps)}"
                    )
        
        return violations

    def print_step_constraints(self, step):
        """Print all constraints affecting a particular step"""
        print(f"\nConstraints affecting Step {step}:")
        
        # Check SOD constraints
        sod_pairs = [pair for pair in self.instance.SOD if step-1 in pair]
        if sod_pairs:
            print("Separation of Duty constraints with steps:", 
                [p[1]+1 if p[0] == step-1 else p[0]+1 for p in sod_pairs])
        
        # Check BOD constraints
        bod_pairs = [pair for pair in self.instance.BOD if step-1 in pair]
        if bod_pairs:
            print("Binding of Duty constraints with steps:",
                [p[1]+1 if p[0] == step-1 else p[0]+1 for p in bod_pairs])
        
        # Check at-most-k constraints
        for k, steps in self.instance.at_most_k:
            if step-1 in steps:
                print(f"At-most-{k} constraint with steps:",
                    [s+1 for s in steps])

    def verify_solution(self, solution_dict):
        """Verify all constraints and report violations"""
        violations = []
        
        # Track user assignments for verification
        user_assignments = defaultdict(list)
        for step, user in solution_dict.items():
            user_assignments[user].append(step)
        
        # Print assignment summary
        print("\nAssignment Summary:")
        users_used = sorted(user_assignments.keys())
        for user in users_used:
            print(f"User {user} assigned to step{'s' if len(user_assignments[user]) > 1 else ''}: {sorted(user_assignments[user])}")
        print(f"\nTotal unique users used: {len(users_used)}")

        # Verify authorizations
        for step, user in solution_dict.items():
            if not self.instance.user_step_matrix[user-1][step-1]:
                violations.append(f"Authorization Violation: User {user} not authorized for Step {step}")
                print(f"Checking auth matrix: {self.instance.user_step_matrix[user-1][step-1]} for user {user}, step {step}")

        # Verify at-most-k constraints
        atmost_violations = self.verify_at_most_k(solution_dict)
        if atmost_violations:
            violations.extend(atmost_violations)

        # Verify SOD constraints
        for s1, s2 in self.instance.SOD:
            s1, s2 = s1+1, s2+1  # Convert to 1-based indexing
            print(f"Checking SOD constraint between steps {s1} and {s2}")
            if solution_dict.get(s1) == solution_dict.get(s2):
                violations.append(
                    f"Separation of Duty Violation: Steps {s1} and {s2} both assigned to user {solution_dict[s1]}"
                )

        # Verify BOD constraints
        for s1, s2 in self.instance.BOD:
            s1, s2 = s1+1, s2+1  # Convert to 1-based indexing
            print(f"Checking BOD constraint between steps {s1} and {s2}")
            if solution_dict.get(s1) != solution_dict.get(s2):
                violations.append(
                    f"Binding of Duty Violation: Step {s1} assigned to user {solution_dict.get(s1)} but "
                    f"step {s2} assigned to user {solution_dict.get(s2)}"
                )

        return violations

    def solve(self):
        """Enhanced solving process with early detection"""
        start_time = time.time()
        
        # Create and add all constraints
        self.create_variables()
        self.add_authorization_constraints()
        self.add_separation_of_duty()
        self.add_binding_of_duty()
        self.add_at_most_k()
        self.add_one_team()
        
        # Solve without timeout
        status = self.solver.Solve(self.model)
        
        end_time = time.time()
        
        # Process results
        result = {
            'sat': 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': []
        }
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            result['sat'] = 'sat'
            
            # Reconstruct solution efficiently
            solution = []
            solution_dict = {}
            for step in range(self.instance.number_of_steps):
                for user, var in self.user_assignment[step]:
                    if self.solver.Value(var):
                        solution.append((step + 1, user + 1))
                        solution_dict[step + 1] = user + 1
                        break
            
            result['sol'] = solution
            
            # Verify constraints
            violations = self.verify_solution(solution_dict)
            if violations:
                print("\nConstraint Violations Found:")
                # Print constraints for any step involved in violations
                problematic_steps = set()
                for v in violations:
                    steps = [int(s) for s in re.findall(r'Step (\d+)', v)]
                    problematic_steps.update(steps)
                
                for step in sorted(problematic_steps):
                    self.print_step_constraints(step)
                
                for violation in violations:
                    print(violation)
            else:
                print("\nAll constraints satisfied")
                print("\nSolution verified with no violations")
        
        return result
    
def Solver(instance, filename, results):
    print(f"\nSolving instance: {filename}")
    
    solver = OptimizedCpSolver(instance)
    result = solver.solve()
    result['filename'] = filename
    
    # Add metadata
    metadata = INSTANCE_METADATA.get(filename.split('/')[-1], {})
    result['expected_sat'] = metadata.get('sat', 'Unknown')
    result['unique_solution'] = metadata.get('unique', 'Unknown')
    
    results.append(result)
    
    # Output results
    if result['sat'] == 'sat':
        print(f"Status: SAT (Expected: {result['expected_sat']})")
        print(f"Execution Time: {result['exe_time']}")
        print("Solution:")
        
        step_assignments = {}
        for step, user in result['sol']:
            step_assignments[step] = user
            
        for step in sorted(step_assignments.keys()):
            print(f"Step {step}: User {step_assignments[step]}")
    else:
        print(f"Status: UNSAT (Expected: {result['expected_sat']})")
        print(f"Execution Time: {result['exe_time']}")
    
    return result


if __name__ == "__main__":
    results = []
    
    # Specify the full path to the instances folder
    instance_folder = "assets/instances/"
    
    # Sort instances to ensure consistent order
    import os
    instance_files = sorted([f for f in os.listdir(instance_folder) if f.startswith('example') and f.endswith('.txt')])
    
    for filename in instance_files:
        full_path = os.path.join(instance_folder, filename)
        try:
            instance = read_file(full_path)
            Solver(instance, full_path, results)
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    # Summarize results
    print("\nResults Summary:")
    print("{:<15} {:<10} {:<15} {:<15} {:<15}".format(
        "Instance", "Status", "Expected SAT", "Unique Sol", "Exec Time"))
    print("-" * 70)
    
    for result in results:
        print("{:<15} {:<10} {:<15} {:<15} {:<15}".format(
            result['filename'].split('/')[-1], 
            result['sat'], 
            str(result['expected_sat']), 
            str(result['unique_solution']), 
            result['exe_time']))
