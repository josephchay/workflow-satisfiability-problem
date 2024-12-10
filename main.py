from ortools.sat.python import cp_model
import re
import time
import multiprocessing
import time
import os
import numpy


# Define the Instance class to store the parsed data
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


# Efficiently reads an instance file and parses constraints
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


# Function to transform the output
def transform_output(result):
    if result['sat'] == 'sat':
        solution = "\n".join(result['sol'])
    else:
        solution = "No solution found."

    output = {
        "satisfiability": result['sat'],
        "solution": solution,
        "execution_time_ms": result['exe_time']
    }
    return output


# Returns the current time in seconds since the epoch
def currenttime():
    return time.time()


def Solver(instance, filename, results):
    print(f"Solving instance: {filename}")
    model = cp_model.CpModel()
    user_assignment = [[model.NewBoolVar(f's{s + 1}: u{u + 1}') for u in range(instance.number_of_users)] for s in range(instance.number_of_steps)]

    for step in range(instance.number_of_steps):
        model.AddExactlyOne(user_assignment[step][user] for user in range(instance.number_of_users))

    for user in range(instance.number_of_users):
        if instance.auth[user]:
            for step in range(instance.number_of_steps):
                if step not in instance.auth[user]:
                    model.Add(user_assignment[step][user] == 0)

    for (separated_step1, separated_step2) in instance.SOD:
        for user in range(instance.number_of_users):
            model.Add(user_assignment[separated_step2][user] == 0).OnlyEnforceIf(user_assignment[separated_step1][user])

    for (bound_step1, bound_step2) in instance.BOD:
        for user in range(instance.number_of_users):
            model.Add(user_assignment[bound_step2][user] == 1).OnlyEnforceIf(user_assignment[bound_step1][user])

    for (k, steps) in instance.at_most_k:
        user_assignment_flag = [model.NewBoolVar(f'at-most-k_u{u}') for u in range(instance.number_of_users)]
        for user in range(instance.number_of_users):
            for step in steps:
                model.Add(user_assignment_flag[user] == 1).OnlyEnforceIf(user_assignment[step][user])
            model.Add(sum(user_assignment[step][user] for step in steps) >= user_assignment_flag[user])
        model.Add(sum(user_assignment_flag) <= k)

    for (steps, teams) in instance.one_team:
        team_flag = [model.NewBoolVar(f'team{t}') for t in range(len(teams))]
        model.AddExactlyOne(team_flag)
        for team_index in range(len(teams)):
            for step in steps:
                for user in teams[team_index]:
                    model.Add(user_assignment[step][user] == 0).OnlyEnforceIf(team_flag[team_index].Not())
        users_in_teams = list(numpy.concatenate(teams).flat)
        for step in steps:
            for user in range(instance.number_of_users):
                if user not in users_in_teams:
                    model.Add(user_assignment[step][user] == 0)

    # Solve the model
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = False  # Find only one solution
    solver.parameters.num_search_workers = 4          # Multi-threading

    # Timing the solver process
    start_time = time.time()
    status = solver.Solve(model)
    end_time = time.time()

    # Extract results
    result = {'filename': filename, 'sat': 'unsat', 'exe_time': f"{(end_time - start_time) * 1000:.2f}ms"}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result['sat'] = 'sat'
        result['sol'] = [
            f's{s + 1}: u{u + 1}' for s in range(instance.number_of_steps)
            for u in range(instance.number_of_users) if solver.Value(user_assignment[s][u])
        ]
        print("Solution found:")
        for assignment in result['sol']:
            print(assignment)
    else:
        result['sol'] = []

    print(f"Execution Time: {result['exe_time']}")

    # Store the result for later display
    results.append(result)
    return result


def print_results_table(results):
    # Print a table header
    print("\nResults Table:")
    print("{:<15} {:<10} {:<20} {:<15}".format("Instance", "Status", "Assignments", "Exec Time"))
    print("-" * 60)

    # Print each result in the table
    for result in results:
        # assignments = ', '.join(result['sol']) if result['sol'] else "unsat"
        assignments = "sat" if result['sol'] else "unsat"
        print("{:<15} {:<10} {:<20} {:<15}".format(result['filename'], result['sat'], assignments, result['exe_time']))


# Main usage
if __name__ == "__main__":
    limit = 19  # Define the number of instances you want to solve
    results = []  # Store results for all instances

    for i in range(1, limit + 1):
        filename = f"instances/example{i}.txt"  # Adjust the file path accordingly
        
        # Try to read the file and solve the instance
        try:
            instance = read_file(filename)
            # In your main execution block
            # result = Solver(instance, filename)
            result = Solver(instance, filename, results)
            print(f"\n--- Finished solving {filename} ---\n")
            print_results_table(results)  # Print the updated table after each solve
        except ValueError as ve:
            print(f"Error reading file {filename}: {ve}")
            continue  # Skip this file and proceed with the next one


# # Call the main function
# if _name_ == "_main_":
#     main()
