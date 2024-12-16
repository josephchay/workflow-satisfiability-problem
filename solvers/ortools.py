from ortools.sat.python import cp_model
import time
import numpy

from filesystem import FileReader
from components import Instance


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


class ORToolsSolver:
    def __init__(self, instance: Instance):
        self.instance = instance
        self.model = cp_model.CpModel()

    def solve(self):
        user_assignment = [[self.model.NewBoolVar(f's{s + 1}: u{u + 1}') for u in range(self.instance.number_of_users)] for s in range(self.instance.number_of_steps)]

        for step in range(self.instance.number_of_steps):
            self.model.AddExactlyOne(user_assignment[step][user] for user in range(self.instance.number_of_users))

        for user in range(self.instance.number_of_users):
            if self.instance.auth[user]:
                for step in range(self.instance.number_of_steps):
                    if step not in self.instance.auth[user]:
                        self.model.Add(user_assignment[step][user] == 0)

        for (separated_step1, separated_step2) in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                self.model.Add(user_assignment[separated_step2][user] == 0).OnlyEnforceIf(user_assignment[separated_step1][user])

        for (bound_step1, bound_step2) in self.instance.BOD:
            for user in range(self.instance.number_of_users):
                self.model.Add(user_assignment[bound_step2][user] == 1).OnlyEnforceIf(user_assignment[bound_step1][user])

        for (k, steps) in self.instance.at_most_k:
            user_assignment_flag = [self.model.NewBoolVar(f'at-most-k_u{u}') for u in range(self.instance.number_of_users)]
            for user in range(self.instance.number_of_users):
                for step in steps:
                    self.model.Add(user_assignment_flag[user] == 1).OnlyEnforceIf(user_assignment[step][user])
                self.model.Add(sum(user_assignment[step][user] for step in steps) >= user_assignment_flag[user])
            self.model.Add(sum(user_assignment_flag) <= k)

        for (steps, teams) in self.instance.one_team:
            team_flag = [self.model.NewBoolVar(f'team{t}') for t in range(len(teams))]
            self.model.AddExactlyOne(team_flag)
            for team_index in range(len(teams)):
                for step in steps:
                    for user in teams[team_index]:
                        self.model.Add(user_assignment[step][user] == 0).OnlyEnforceIf(team_flag[team_index].Not())
            users_in_teams = list(numpy.concatenate(teams).flat)
            for step in steps:
                for user in range(self.instance.number_of_users):
                    if user not in users_in_teams:
                        self.model.Add(user_assignment[step][user] == 0)

        # Solve the self.model
        solver = self.model.CpSolver()
        solver.parameters.enumerate_all_solutions = False  # Find only one solution
        solver.parameters.num_search_workers = 4          # Multi-threading

        # Timing the solver process
        start_time = time.time()
        status = solver.Solve(self.model)
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
if __name__ == "_main_":
    limit = 19  # Define the number of instances you want to solve
    results = []  # Store results for all instances

    for i in range(1, limit + 1):
        filename = f"instances/example{i}.txt"  # Adjust the file path accordingly
        
        # Try to read the file and solve the instance
        try:
            instance = FileReader.read_file(filename)
            # In your main execution block
            # result = Solver(instance, filename)
            result = Solver(instance, filename, results)
            print(f"\n--- Finished solving {filename} ---\n")
            print_results_table(results)  # Print the updated table after each solve
        except ValueError as ve:
            print(f"Error reading file {filename}: {ve}")
            continue  # Skip this file and proceed with the next one
