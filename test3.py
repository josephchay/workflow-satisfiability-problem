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
        self.user_assignment = {}
        self.step_variables = {}  # New: Track variables by step
        self.user_step_variables = {}  # New: Track variables by user and step
        
        # Enhanced solver parameters
        self.solver.parameters.num_search_workers = 8
        self.solver.parameters.log_search_progress = False

    def create_variables(self):
        """Create variables with improved tracking"""
        self.step_variables = {}  # Clear any existing variables
        self.user_step_variables = defaultdict(dict)
        
        for step in range(self.instance.number_of_steps):
            self.step_variables[step] = []
            for user in range(self.instance.number_of_users):
                if self.instance.user_step_matrix[user][step]:
                    var = self.model.NewBoolVar(f's{step + 1}_u{user + 1}')
                    self.step_variables[step].append((user, var))
                    self.user_step_variables[user][step] = var

    def add_authorization_constraints(self):
        """Basic authorization constraints"""
        for step, user_vars in self.step_variables.items():
            self.model.AddExactlyOne(var for _, var in user_vars)

    def add_binding_of_duty(self):
        """Revised BOD constraints with better early infeasibility detection"""
        # First check all BOD constraints for possible infeasibility
        infeasible_constraints = []
        for s1, s2 in self.instance.BOD:
            common_users = set()
            for user in range(self.instance.number_of_users):
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2]):
                    common_users.add(user)
            
            if not common_users:
                infeasible_constraints.append((s1+1, s2+1))  # Store 1-based indices
        
        if infeasible_constraints:
            print("\nBOD Constraint Analysis:")
            print("The following BOD constraints cannot be satisfied due to no users being authorized for both steps:")
            for s1, s2 in infeasible_constraints:
                print(f"  Steps {s1} and {s2} must be performed by the same user, but no user is authorized for both")
            # Make model infeasible
            self.model.Add(1 == 0)
            return False
        
        # If we reach here, all BOD constraints have at least one possible user
        for s1, s2 in self.instance.BOD:
            # Create sum variables for each step
            s1_vars = []
            s2_vars = []
            
            # For each user that can do both steps
            common_users = []
            for user in range(self.instance.number_of_users):
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2]):
                    var1 = self.user_step_variables[user][s1]
                    var2 = self.user_step_variables[user][s2]
                    self.model.Add(var1 == var2)
                    common_users.append(user)
                    s1_vars.append(var1)
                    s2_vars.append(var2)
            
            # Ensure one of the common users must be chosen
            self.model.Add(sum(s1_vars) == 1)
            self.model.Add(sum(s2_vars) == 1)
        
        return True

    def add_at_most_k(self):
        """Completely reworked at-most-k constraints"""
        # Handle each at-most-k constraint separately
        for k, steps in self.instance.at_most_k:
            # For each user
            for user in range(self.instance.number_of_users):
                # Get variables for steps this user can perform
                user_step_vars = []
                for step in steps:
                    if self.instance.user_step_matrix[user][step]:
                        var = self.user_step_variables[user][step]
                        user_step_vars.append(var)
                
                if user_step_vars:  # Only add constraint if user can perform any steps
                    # Sum of assignments must be <= k
                    self.model.Add(sum(user_step_vars) <= k)
        
        # Additional global constraints
        if self.instance.at_most_k:
            min_k = min(k for k, _ in self.instance.at_most_k)
            # For each user, limit total assignments across all steps
            for user in range(self.instance.number_of_users):
                user_vars = []
                for step in range(self.instance.number_of_steps):
                    if step in self.user_step_variables[user]:
                        user_vars.append(self.user_step_variables[user][step])
                if user_vars:
                    self.model.Add(sum(user_vars) <= min_k)

    def add_separation_of_duty(self):
        """Optimized SOD constraints"""
        for s1, s2 in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                # Only add constraint if user can do both steps
                if (s1 in self.user_step_variables[user] and 
                    s2 in self.user_step_variables[user]):
                    var1 = self.user_step_variables[user][s1]
                    var2 = self.user_step_variables[user][s2]
                    self.model.Add(var1 + var2 <= 1)

    def add_one_team(self):
        """Optimized one-team constraints"""
        for steps, teams in self.instance.one_team:
            # Create team selection variables
            team_vars = [self.model.NewBoolVar(f'team_{i}') for i in range(len(teams))]
            self.model.AddExactlyOne(team_vars)  # Exactly one team must be selected
            
            # For each step
            for step in steps:
                # For each team
                for team_idx, team in enumerate(teams):
                    # When this team is selected
                    team_var = team_vars[team_idx]
                    
                    # Users not in team cannot be assigned
                    for user, var in self.step_variables[step]:
                        if user not in team:
                            self.model.Add(var == 0).OnlyEnforceIf(team_var)

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
        print("\nVerifying authorization constraints...")
        for step, user in solution_dict.items():
            print(f"Checking authorization for Step {step}, User {user}")
            if not self.instance.user_step_matrix[user-1][step-1]:
                violations.append(f"Authorization Violation: User {user} not authorized for Step {step}")

        # Verify SOD constraints
        print("\nVerifying separation-of-duty constraints...")
        for s1, s2 in self.instance.SOD:
            s1, s2 = s1+1, s2+1  # Convert to 1-based indexing
            print(f"Checking SOD constraint between steps {s1} and {s2}")
            if solution_dict.get(s1) == solution_dict.get(s2):
                violations.append(
                    f"Separation of Duty Violation: Steps {s1} and {s2} both assigned to user {solution_dict[s1]}"
                )

        # Verify BOD constraints
        print("\nVerifying binding-of-duty constraints...")
        for s1, s2 in self.instance.BOD:
            s1, s2 = s1+1, s2+1  # Convert to 1-based indexing
            print(f"Checking BOD constraint between steps {s1} and {s2}")
            if solution_dict.get(s1) != solution_dict.get(s2):
                violations.append(
                    f"Binding of Duty Violation: Step {s1} assigned to user {solution_dict.get(s1)} "
                    f"but step {s2} assigned to user {solution_dict.get(s2)}"
                )

        # Verify at-most-k constraints
        print("\nVerifying at-most-k constraints...")
        for k, steps in self.instance.at_most_k:
            steps_base1 = [s+1 for s in steps]  # Convert to 1-based indexing for display
            print(f"Checking at-most-{k} constraint for steps {steps_base1}")
            
            # Track assignments for this constraint
            user_counts = defaultdict(list)
            for step in steps:
                step_1based = step + 1  # Convert to 1-based
                if step_1based in solution_dict:
                    user = solution_dict[step_1based]
                    user_counts[user].append(step_1based)
            
            # Check violations
            for user, assigned_steps in user_counts.items():
                if len(assigned_steps) > k:
                    violations.append(
                        f"At-most-{k} Violation: User {user} assigned to {len(assigned_steps)} steps "
                        f"{sorted(assigned_steps)} in constraint group {steps_base1}"
                    )

        # Verify one-team constraints
        print("\nVerifying one-team constraints...")
        for steps, teams in self.instance.one_team:
            steps_base1 = [s+1 for s in steps]
            print(f"Checking one-team constraint for steps {steps_base1}")
            
            # Get assigned users for these steps
            assigned_users = set()
            for step in steps:
                step_1based = step + 1
                if step_1based in solution_dict:
                    assigned_users.add(solution_dict[step_1based] - 1)  # Convert to 0-based for team checking
            
            # Check if assigned users form a valid team
            valid_team_found = False
            for team in teams:
                if all(user in team for user in assigned_users):
                    valid_team_found = True
                    break
            
            if not valid_team_found:
                violations.append(
                    f"One-team Violation: Assigned users {sorted(u+1 for u in assigned_users)} "
                    f"for steps {steps_base1} do not form a valid team"
                )

        return violations

    def solve(self):
        """Main solving method with comprehensive error checking"""
        try:
            print("\nAnalyzing instance constraints...")
            infeasibility_reason = self.analyze_instance_constraints()
            if infeasibility_reason:
                return {
                    'sat': 'unsat',
                    'exe_time': '0ms',
                    'sol': [],
                    'reason': infeasibility_reason
                }

            start_time = time.time()
            
            print("\nBuilding and verifying constraints...")
            if not self.build_model():  # New method to encapsulate model building
                end_time = time.time()
                return {
                    'sat': 'unsat',
                    'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
                    'sol': [],
                    'reason': 'Failed to build valid model'
                }
            
            print("Solving model...")
            status = self.solver.Solve(self.model)
            end_time = time.time()
            
            result = {
                'sat': 'unsat',
                'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
                'sol': []
            }
            
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                print("\nSolution found. Verifying constraints...")
                result.update(self.process_solution(status))
            else:
                self.report_infeasibility(status)
            
            return result
            
        except Exception as e:
            self.handle_error(e)
            raise

    def build_model(self):
        """Encapsulates all model building steps"""
        try:
            self.create_variables()
            self.add_authorization_constraints()
            self.add_separation_of_duty()
            if not self.add_binding_of_duty():
                return False
            self.add_at_most_k()
            self.add_one_team()
            return True
        except Exception as e:
            print(f"Error building model: {str(e)}")
            return False

    def process_solution(self, status):
        """Process and verify solution"""
        result = {
            'sat': 'sat',
            'sol': []
        }
        
        solution_dict = {}
        for step in range(self.instance.number_of_steps):
            for user, var in self.step_variables[step]:
                if self.solver.Value(var):
                    result['sol'].append((step + 1, user + 1))
                    solution_dict[step + 1] = user + 1
                    break
        
        violations = self.verify_solution(solution_dict)
        if violations:
            self.report_violations(violations)
        else:
            print("\nAll constraints satisfied")
            print("\nSolution verified with no violations")
        
        return result

    def report_violations(self, violations):
        """Report violations in a structured way"""
        print("\nConstraint Violations Found:")
        violation_types = {
            'Authorization': [],
            'Separation of Duty': [],
            'Binding of Duty': [],
            'At-most-k': [],
            'One-team': []
        }
        
        problematic_steps = set()
        for v in violations:
            for vtype in violation_types:
                if vtype in v:
                    violation_types[vtype].append(v)
                    break
            
            steps = [int(s) for s in re.findall(r'Step (\d+)', v)]
            problematic_steps.update(steps)
        
        print("\nAffected Steps and Their Constraints:")
        for step in sorted(problematic_steps):
            self.print_step_constraints(step)
        
        for vtype, vlist in violation_types.items():
            if vlist:
                print(f"\n{vtype} Violations:")
                for v in vlist:
                    print(v)

    def report_infeasibility(self, status):
        """Report why the model is infeasible"""
        print(f"\nNo solution found. Status: {status}")
        if status == cp_model.INFEASIBLE:
            print("Problem is infeasible - The constraints cannot all be satisfied simultaneously")
        elif status == cp_model.MODEL_INVALID:
            print("Model is invalid - There may be contradictory constraints")
        elif status == cp_model.UNKNOWN:
            print("Solver encountered unknown error - Try adjusting solver parameters")

    def analyze_instance_constraints(self):
        """Analyze and print all constraints in the instance"""
        print("\nInstance Analysis:")
        print(f"Number of steps: {self.instance.number_of_steps}")
        print(f"Number of users: {self.instance.number_of_users}")
        print(f"Total constraints: {self.instance.number_of_constraints}")
        
        print("\nConstraint Breakdown:")
        # Authorization matrix analysis
        authorized_counts = [sum(row) for row in self.instance.user_step_matrix]
        print(f"Authorization constraints: {sum(authorized_counts)} total authorizations")
        
        # BOD analysis - Do this first to identify infeasibility early
        if self.instance.BOD:
            print(f"\nBinding of Duty constraints ({len(self.instance.BOD)}):")
            infeasible_found = False
            for s1, s2 in self.instance.BOD:
                print(f"  Steps {s1+1} and {s2+1} must be performed by the same user")
                # Check if there are users authorized for both steps
                common_users = set()
                for user in range(self.instance.number_of_users):
                    if (self.instance.user_step_matrix[user][s1] and 
                        self.instance.user_step_matrix[user][s2]):
                        common_users.add(user + 1)
                if common_users:
                    print(f"    Users authorized for both steps: {sorted(common_users)}")
                else:
                    infeasible_found = True
                    print(f"    Infeasibility detected: No users are authorized for both steps {s1+1} and {s2+1}")
                    print(f"    This makes the instance UNSAT as it's impossible to satisfy this BOD constraint")

            if infeasible_found:
                print("\nInstance is UNSAT due to impossible Binding of Duty constraints")
        
        # SOD analysis
        if self.instance.SOD:
            print(f"\nSeparation of Duty constraints ({len(self.instance.SOD)}):")
            for s1, s2 in self.instance.SOD:
                print(f"  Steps {s1+1} and {s2+1} must be performed by different users")
        
        # At-most-k analysis
        if self.instance.at_most_k:
            print(f"\nAt-most-k constraints ({len(self.instance.at_most_k)}):")
            for k, steps in self.instance.at_most_k:
                print(f"  At most {k} steps from {[s+1 for s in steps]} can be assigned to same user")
        
        # One-team analysis
        if self.instance.one_team:
            print(f"\nOne-team constraints ({len(self.instance.one_team)}):")
            for steps, teams in self.instance.one_team:
                print(f"  Steps {[s+1 for s in steps]} must be assigned to one team:")
                for i, team in enumerate(teams, 1):
                    print(f"    Team {i}: Users {[u+1 for u in team]}")

def Solver(instance, filename, results):
    print("\n" + "=" * 120)
    print(f"\nSolving instance: {filename}")
    
    try:
        solver = OptimizedCpSolver(instance)
        result = solver.solve()
        
        # Add metadata
        result['filename'] = filename
        metadata = INSTANCE_METADATA.get(filename.split('/')[-1], {})
        result['expected_sat'] = metadata.get('sat', 'Unknown')
        result['unique_solution'] = metadata.get('unique', 'Unknown')
        
        results.append(result)
        
        # Output results
        if result['sat'] == 'sat':
            print(f"\nStatus: SAT (Expected: {result['expected_sat']})")
            print(f"Execution Time: {result['exe_time']}")
            print("Solution:")
            
            step_assignments = {}
            for step, user in result['sol']:
                step_assignments[step] = user
                
            for step in sorted(step_assignments.keys()):
                print(f"Step {step}: User {step_assignments[step]}")
        else:
            print(f"\nStatus: UNSAT (Expected: {result['expected_sat']})")
            print(f"Execution Time: {result['exe_time']}")
        
        return result
        
    except Exception as e:
        print(f"\nError processing {filename}:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()
        
        # Create an error result to maintain consistency
        error_result = {
            'filename': filename,
            'sat': 'error',
            'exe_time': '0ms',
            'sol': [],
            'expected_sat': INSTANCE_METADATA.get(filename.split('/')[-1], {}).get('sat', 'Unknown'),
            'unique_solution': INSTANCE_METADATA.get(filename.split('/')[-1], {}).get('unique', 'Unknown')
        }
        results.append(error_result)
        return error_result


if __name__ == "__main__":
    results = []
    
    # Specify the full path to the instances folder
    instance_folder = "assets/instances/"
    
    # Sort instances to ensure consistent order
    import os
    instance_files = sorted([f for f in os.listdir(instance_folder) if f.startswith('example') and f.endswith('.txt')])
    
    for filename in sorted(instance_files, key=lambda x: int(''.join(filter(str.isdigit, x)))):
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
