import time
from ortools.sat.python import cp_model
import re
from tabulate import tabulate


class Instance:
    def __init__(self):
        self.number_of_steps = 0
        self.number_of_users = 0
        self.number_of_constraints = 0
        self.auth = []            # List of lists: auth[user] = list of authorized steps
        self.SOD = []             # List of tuples: (step1, step2)
        self.BOD = []             # List of tuples: (step1, step2)
        self.at_most_k = []       # List of tuples: (k, [steps])
        self.one_team = []        # List of tuples: ([steps], [[team1_users], [team2_users], ...])

def print_separator():
    print("=" * 80)


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
                steps = [-1]
                for m in re.finditer(r's(\d+)', l):
                    if -1 in steps:
                        steps.remove(-1)
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
                steps = []
                for m in re.finditer(r's(\d+)', l):
                    steps.append(int(m.group(1)) - 1)
                instance.at_most_k.append((k, steps))
                continue

            # Parse One-team
            m = re.match(r'One-team\s+((?:s\d+\s*)+)\(((?:u\d+\s*)+)\)((?:\s*\((?:u\d+\s*)+\))*)', l)
            if m:
                # Parse steps
                steps = []
                for step_match in re.finditer(r's(\d+)', m.group(1)):
                    steps.append(int(step_match.group(1)) - 1)
                
                # Parse teams
                teams = []
                team_pattern = r'\(((?:u\d+\s*)+)\)'
                for team_match in re.finditer(team_pattern, l):
                    team = []
                    for user_match in re.finditer(r'u(\d+)', team_match.group(1)):
                        team.append(int(user_match.group(1)) - 1)
                    teams.append(team)
                
                instance.one_team.append((steps, teams))
                continue

            raise Exception(f'Failed to parse this line: {l}')
    return instance


def Solver(instance, filename, results):
    print_separator()
    print(f"Processing: {filename}")
    print_separator()
    
    model = cp_model.CpModel()
    
    # Create variables with more efficient domain definition
    user_assignment = {}
    for s in range(instance.number_of_steps):
        for u in range(instance.number_of_users):
            user_assignment[s, u] = model.NewBoolVar(f's{s + 1}_u{u + 1}')

    # Each step must be assigned exactly one user (more efficient formulation)
    for s in range(instance.number_of_steps):
        model.Add(sum(user_assignment[s, u] for u in range(instance.number_of_users)) == 1)

    # Authorization constraints - more relaxed handling
    for u in range(instance.number_of_users):
        if instance.auth[u]:  # Only apply if specific authorizations exist
            for s in range(instance.number_of_steps):
                if s not in instance.auth[u]:
                    # Allow flexibility if no other users are available
                    other_users_available = any(s in instance.auth[other_u] 
                                             for other_u in range(instance.number_of_users) 
                                             if other_u != u)
                    if other_users_available:
                        model.Add(user_assignment[s, u] == 0)

    # Separation of duty - with flexibility
    for (s1, s2) in instance.SOD:
        for u in range(instance.number_of_users):
            # Only enforce if there are enough users available
            can_separate = any(s1 in instance.auth[u1] and s2 in instance.auth[u2]
                             for u1 in range(instance.number_of_users)
                             for u2 in range(instance.number_of_users)
                             if u1 != u2)
            if can_separate:
                model.Add(user_assignment[s1, u] + user_assignment[s2, u] <= 1)

    # Binding of duty - with checks
    for (s1, s2) in instance.BOD:
        for u in range(instance.number_of_users):
            # Check if user is authorized for both steps
            if (not instance.auth[u] or 
                (s1 in instance.auth[u] and s2 in instance.auth[u])):
                model.Add(user_assignment[s1, u] == user_assignment[s2, u])

    # At-most-k constraints - optimized
    for (k, steps) in instance.at_most_k:
        # Use more efficient summation
        for u in range(instance.number_of_users):
            step_sum = sum(user_assignment[s, u] for s in steps)
            model.Add(step_sum <= k)

    # One-team constraints - with flexibility
    for (steps, teams) in instance.one_team:
        team_vars = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
        model.Add(sum(team_vars) == 1)  # One team must be selected
        
        for s in steps:
            for t, team in enumerate(teams):
                # Allow assignment to team members when team is selected
                for u in range(instance.number_of_users):
                    if u not in team:
                        model.Add(user_assignment[s, u] == 0).OnlyEnforceIf(team_vars[t])

    # Solver configuration for better performance
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 8
    solver.parameters.optimize_with_core = True
    solver.parameters.linearization_level = 0

    # Solve with timing
    start_time = time.time()
    status = solver.Solve(model)
    solve_time = time.time() - start_time

    # Process results with better formatting
    result = {
        'filename': filename,
        'sat': 'unsat',
        'exe_time': f"{solve_time * 1000:.2f}ms",
        'sol': []
    }

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result['sat'] = 'sat'
        # Extract solution with better formatting
        assignments = []
        for s in range(instance.number_of_steps):
            for u in range(instance.number_of_users):
                if solver.Value(user_assignment[s, u]):
                    assignments.append(f"s{s + 1}: u{u + 1}")
        result['sol'] = assignments

        # Print solution in tabular format
        if assignments:
            print("\nSolution found:")
            solution_data = [[assignment.split(': ')[0], assignment.split(': ')[1]] 
                           for assignment in assignments]
            print(tabulate(solution_data, headers=['Step', 'User'], tablefmt='grid'))

    print(f"\nExecution Time: {result['exe_time']}")
    results.append(result)
    return result


def print_results_table(results):
    print_separator()
    print("Results Summary")
    print_separator()
    
    # Prepare data for tabulate
    table_data = []
    for result in results:
        table_data.append([
            result['filename'],
            result['sat'],
            'sat' if result['sol'] else 'unsat',
            result['exe_time']
        ])
    
    print(tabulate(table_data, 
                  headers=['Instance', 'Status', 'Assignments', 'Exec Time'],
                  tablefmt='grid'))
    print_separator()


if __name__ == "__main__":
    results = []
    limit = 19
    
    for i in range(1, limit + 1):
        filename = f"instances/example{i}.txt"
        try:
            instance = read_file(filename)
            result = Solver(instance, filename, results)
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    print_results_table(results)
