import time
from ortools.sat.python import cp_model
import re
import numpy


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
    print(f"Solving instance: {filename}")
    model = cp_model.CpModel()

    # Create variables: user_assignment[s][u] means step s is assigned to user u
    user_assignment = [[model.NewBoolVar(f's{s + 1}: u{u + 1}') 
                       for u in range(instance.number_of_users)] 
                       for s in range(instance.number_of_steps)]

    # Constraint: each step must be assigned to exactly one user
    for step in range(instance.number_of_steps):
        model.AddExactlyOne(user_assignment[step][user] for user in range(instance.number_of_users))

    # Constraint: authorizations
    for user in range(instance.number_of_users):
        if instance.auth[user]:  # If user has specific authorizations
            for step in range(instance.number_of_steps):
                if step not in instance.auth[user]:
                    model.Add(user_assignment[step][user] == 0)

    # Constraint: separation of duty
    for (separated_step1, separated_step2) in instance.SOD:
        for user in range(instance.number_of_users):
            # If user is assigned to step1, they cannot be assigned to step2
            model.Add(user_assignment[separated_step2][user] == 0).OnlyEnforceIf(user_assignment[separated_step1][user])
            model.Add(user_assignment[separated_step1][user] == 0).OnlyEnforceIf(user_assignment[separated_step2][user])

    # Constraint: binding of duty
    for (bound_step1, bound_step2) in instance.BOD:
        for user in range(instance.number_of_users):
            # If user is assigned to step1, they must be assigned to step2 and vice versa
            model.Add(user_assignment[bound_step2][user] == 1).OnlyEnforceIf(user_assignment[bound_step1][user])
            model.Add(user_assignment[bound_step1][user] == 1).OnlyEnforceIf(user_assignment[bound_step2][user])

    # Constraint: at-most-k
    for (k, steps) in instance.at_most_k:
        # Create indicator variables for users involved in the steps
        user_involved = [model.NewBoolVar(f'at-most-k_u{u}') for u in range(instance.number_of_users)]
        for user in range(instance.number_of_users):
            # User is involved if they're assigned to any of the steps
            step_assignments = [user_assignment[step][user] for step in steps]
            model.AddMaxEquality(user_involved[user], step_assignments)
        
        # Ensure at most k users are involved
        model.Add(sum(user_involved) <= k)

    # Constraint: one-team
    for (steps, teams) in instance.one_team:
        # Create variables for team selection
        team_selected = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
        
        # Exactly one team must be selected
        model.AddExactlyOne(team_selected)
        
        # For each team
        for team_idx, team in enumerate(teams):
            # For each step in the constraint
            for step in steps:
                # If this team is selected
                # Only users from this team can be assigned to the steps
                for user in range(instance.number_of_users):
                    if user not in team:
                        model.Add(user_assignment[step][user] == 0).OnlyEnforceIf(team_selected[team_idx])

    # Solve the model
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0  # Set timeout to 60 seconds
    
    # Timing the solver process
    start_time = time.time()
    status = solver.Solve(model)
    end_time = time.time()

    # Process results
    result = {
        'filename': filename,
        'sat': 'unsat',
        'exe_time': f"{(end_time - start_time) * 1000:.2f}ms",
        'sol': []
    }

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result['sat'] = 'sat'
        # Extract solution
        result['sol'] = [
            f's{s + 1}: u{u + 1}'
            for s in range(instance.number_of_steps)
            for u in range(instance.number_of_users)
            if solver.Value(user_assignment[s][u])
        ]
        print("Solution found:")
        for assignment in result['sol']:
            print(assignment)
    
    print(f"Execution Time: {result['exe_time']}")
    results.append(result)
    return result


def print_results_table(results):
    print("\nResults Table:")
    print("{:<15} {:<10} {:<20} {:<15}".format(
        "Instance", "Status", "Assignments", "Exec Time"))
    print("-" * 60)

    for result in results:
        assignments = "sat" if result['sol'] else "unsat"
        print("{:<15} {:<10} {:<20} {:<15}".format(
            result['filename'], result['sat'], assignments, result['exe_time']))


if __name__ == "__main__":
    results = []
    limit = 19  # Number of examples to test
    
    # First solve all instances
    for i in range(1, limit + 1):
        filename = f"instances/example{i}.txt"
        try:
            instance = read_file(filename)
            result = Solver(instance, filename, results)
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Print final results table once at the end
    print("\nFinal Results Table:")
    print("{:<15} {:<10} {:<20} {:<15}".format(
        "Instance", "Status", "Assignments", "Exec Time"))
    print("-" * 60)
    
    for result in results:
        assignments = "sat" if result['sol'] else "unsat"
        print("{:<15} {:<10} {:<20} {:<15}".format(
            result['filename'], result['sat'], assignments, result['exe_time']))