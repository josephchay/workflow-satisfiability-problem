import time
from ortools.sat.python import cp_model
import re

class Instance:
    def __init__(self):
        self.number_of_steps = 0
        self.number_of_users = 0
        self.number_of_constraints = 0
        self.auth = []            # List of lists: auth[user] = list of authorized steps
        self.SOD = []             # List of tuples: (step1, step2)
        self.BOD = []             # List of tuples: (step1, step2)
        self.at_most_k = []       # List of tuples: (k, tuple of steps)
        self.one_team = []        # List of tuples: (tuple of steps, tuple of teams)


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
        else:
            raise Exception(f"Could not parse line {line}; expected the {name} attribute")

    instance = Instance()

    with open(filename) as f:
        instance.number_of_steps = read_attribute("#Steps")
        instance.number_of_users = read_attribute("#Users")
        instance.number_of_constraints = read_attribute("#Constraints")
        instance.auth = [[] for u in range(instance.number_of_users)]

        for i in range(instance.number_of_constraints):
            l = f.readline()
            
            # Parse Authorisations
            m = re.match(r"Authorisations u(\d+)(?: s\d+)*", l)
            if m:
                user_id = int(m.group(1))
                steps = []
                for m in re.finditer(r's(\d+)', l):
                    steps.append(int(m.group(1)) - 1)
                instance.auth[user_id - 1].extend(steps)
                continue

            # Parse Separation-of-duty
            m = re.match(r'Separation-of-duty s(\d+) s(\d+)', l)
            if m:
                steps = (int(m.group(1)) - 1, int(m.group(2)) - 1)
                instance.SOD.append(steps)
                continue

            # Parse Binding-of-duty
            m = re.match(r'Binding-of-duty s(\d+) s(\d+)', l)
            if m:
                steps = (int(m.group(1)) - 1, int(m.group(2)) - 1)
                instance.BOD.append(steps)
                continue

            # Parse At-most-k
            m = re.match(r'At-most-k (\d+)(?: s\d+)+', l)
            if m:
                k = int(m.group(1))
                steps = tuple(int(m.group(1)) - 1 for m in re.finditer(r's(\d+)', l))
                instance.at_most_k.append((k, steps))
                continue

            # Parse One-team
            m = re.match(r'One-team\s+((?:s\d+\s*)+)\(((?:u\d+\s*)+)\)((?:\s*\((?:u\d+\s*)+\))*)', l)
            if m:
                # Parse steps
                steps = tuple(int(step_match.group(1)) - 1 for step_match in re.finditer(r's(\d+)', m.group(1)))
                
                # Parse teams
                teams = []
                team_pattern = r'\(((?:u\d+\s*)+)\)'
                for team_match in re.finditer(team_pattern, l):
                    team = tuple(int(user_match.group(1)) - 1 for user_match in re.finditer(r'u(\d+)', team_match.group(1)))
                    teams.append(team)
                
                instance.one_team.append((steps, tuple(teams)))
                continue

            raise Exception(f'Failed to parse this line: {l}')
    return instance

class AdvancedCpSolver:
    def __init__(self, instance):
        self.instance = instance
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.user_assignment = None
        
        # Performance tuning parameters
        # self.solver.parameters.max_time_in_seconds = 300.0  # 5-minute timeout
        self.solver.parameters.num_search_workers = 4  # Use multiple workers
        self.solver.parameters.log_search_progress = False

    def preprocess_constraints(self):
        """Analyze and potentially reduce constraint complexity"""
        # Remove duplicates
        self.instance.SOD = list(set(self.instance.SOD))
        self.instance.BOD = list(set(self.instance.BOD))
        self.instance.at_most_k = list(set(self.instance.at_most_k))

        # Sort constraints by complexity
        self.instance.SOD.sort(key=lambda x: abs(x[0] - x[1]))
        
    def create_variables(self):
        """More efficient variable creation with preprocessing"""
        self.user_assignment = [
            [
                self.model.NewBoolVar(f's{s + 1}_u{u + 1}') 
                for u in range(self.instance.number_of_users)
            ] 
            for s in range(self.instance.number_of_steps)
        ]

    def add_basic_constraints(self):
        """Add fundamental constraints with early pruning"""
        for step in range(self.instance.number_of_steps):
            # Ensure exactly one user per step
            self.model.AddAtMostOne(self.user_assignment[step])
            
            # Find users with authorization for this step
            users_for_step = [
                user for user, steps in enumerate(self.instance.auth) 
                if not steps or step in steps
            ]
            
            if users_for_step:
                self.model.AddAtLeastOne(
                    self.user_assignment[step][u] for u in users_for_step
                )

    def add_authorization_constraints(self):
        """Efficient authorization constraints"""
        for user, authorized_steps in enumerate(self.instance.auth):
            # Only add constraint if user has specific authorizations
            if authorized_steps:
                for step in range(self.instance.number_of_steps):
                    if step not in authorized_steps:
                        self.model.Add(
                            self.user_assignment[step][user] == 0
                        )

    def add_separation_of_duty_constraints(self):
        """Optimized separation of duty handling"""
        for (step1, step2) in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                self.model.Add(
                    self.user_assignment[step1][user] + 
                    self.user_assignment[step2][user] <= 1
                )

    def add_binding_of_duty_constraints(self):
        """Efficient binding of duty constraints"""
        for (step1, step2) in self.instance.BOD:
            for user in range(self.instance.number_of_users):
                # If step1 is assigned, step2 must be assigned to same user
                self.model.Add(
                    self.user_assignment[step1][user] == 
                    self.user_assignment[step2][user]
                )

    def add_at_most_k_constraints(self):
        """Smart at-most-k constraint handling"""
        for k, steps in self.instance.at_most_k:
            # Use indicator variables for efficiency
            user_involved = [
                self.model.NewBoolVar(f'k_involved_u{u}') 
                for u in range(self.instance.number_of_users)
            ]
            
            for user in range(self.instance.number_of_users):
                step_involvements = [
                    self.user_assignment[step][user] for step in steps
                ]
                self.model.AddMaxEquality(user_involved[user], step_involvements)
            
            self.model.Add(sum(user_involved) <= k)

    def add_one_team_constraints(self):
        """Enhanced one-team constraint handling"""
        for steps, teams in self.instance.one_team:
            team_vars = [self.model.NewBoolVar(f'team_{i}') for i in range(len(teams))]
            
            # Exactly one team selected
            self.model.AddExactlyOne(team_vars)
            
            for team_idx, team in enumerate(teams):
                for step in steps:
                    # Only team members can be assigned
                    for user in range(self.instance.number_of_users):
                        if user not in team:
                            self.model.Add(
                                self.user_assignment[step][user] == 0
                            ).OnlyEnforceIf(team_vars[team_idx])

    def solve(self):
        """Comprehensive solving process"""
        start_time = time.time()
        
        # Preprocessing
        self.preprocess_constraints()
        
        # Model construction
        self.create_variables()
        self.add_basic_constraints()
        self.add_authorization_constraints()
        self.add_separation_of_duty_constraints()
        self.add_binding_of_duty_constraints()
        self.add_at_most_k_constraints()
        self.add_one_team_constraints()
        
        # Solving
        status = self.solver.Solve(self.model)
        
        end_time = time.time()
        
        # Result processing
        result = {
            'sat': 'unsat',
            'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
            'sol': []
        }
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            result['sat'] = 'sat'
            result['sol'] = [
                (s + 1, u + 1)
                for s in range(self.instance.number_of_steps)
                for u in range(self.instance.number_of_users)
                if self.solver.Value(self.user_assignment[s][u])
            ]
        
        return result

def Solver(instance, filename, results):
    print(f"\nSolving instance: {filename}")
    
    advanced_solver = AdvancedCpSolver(instance)
    result = advanced_solver.solve()
    result['filename'] = filename
    
    # Add metadata from INSTANCE_METADATA
    metadata = INSTANCE_METADATA.get(filename.split('/')[-1], {})
    result['expected_sat'] = metadata.get('sat', 'Unknown')
    result['unique_solution'] = metadata.get('unique', 'Unknown')
    
    results.append(result)
    
    # Detailed output for SAT instances
    if result['sat'] == 'sat':
        print(f"Status: SAT (Expected: {result['expected_sat']})")
        print(f"Execution Time: {result['exe_time']}")
        print("Solution:")
        step_assignments = {}
        for step, user in result['sol']:
            step_assignments[step] = user
        
        sorted_steps = sorted(step_assignments.keys())
        for step in sorted_steps:
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
