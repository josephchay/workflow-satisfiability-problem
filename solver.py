import re
from dataclasses import dataclass
from typing import List, Tuple
from ortools.sat.python import cp_model


@dataclass
class Instance:
    """Class to store WSP instance data"""
    number_of_steps: int = 0
    number_of_users: int = 0
    number_of_constraints: int = 0
    auth: List[List[int]] = None  # List of lists: auth[user] = list of authorized steps
    SOD: List[Tuple[int, int]] = None  # List of tuples: (step1, step2)
    BOD: List[Tuple[int, int]] = None  # List of tuples: (step1, step2)
    at_most_k: List[Tuple[int, List[int]]] = None  # List of tuples: (k, [steps])
    one_team: List[
        Tuple[List[int], List[List[int]]]] = None  # List of tuples: ([steps], [[team1_users], [team2_users], ...])

    def __post_init__(self):
        if self.auth is None:
            self.auth = []
        if self.SOD is None:
            self.SOD = []
        if self.BOD is None:
            self.BOD = []
        if self.at_most_k is None:
            self.at_most_k = []
        if self.one_team is None:
            self.one_team = []


def read_file(filename: str) -> Instance:
    """Read and parse WSP instance from file"""

    def read_attribute(name, f):
        line = f.readline()
        match = re.match(f'{name}:\\s*(\\d+)$', line)
        if match:
            return int(match.group(1))
        else:
            raise Exception(f"Could not parse line {line}; expected the {name} attribute")

    instance = Instance()

    with open(filename) as f:
        instance.number_of_steps = read_attribute("#Steps", f)
        instance.number_of_users = read_attribute("#Users", f)
        instance.number_of_constraints = read_attribute("#Constraints", f)
        instance.auth = [[] for _ in range(instance.number_of_users)]

        for _ in range(instance.number_of_constraints):
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
                steps = []
                for step_match in re.finditer(r's(\d+)', m.group(1)):
                    steps.append(int(step_match.group(1)) - 1)

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


def solve_instance(instance: Instance) -> dict:
    """Solve a WSP instance using OR-Tools CP-SAT solver"""
    model = cp_model.CpModel()

    # Create variables
    user_assignment = {}
    for s in range(instance.number_of_steps):
        for u in range(instance.number_of_users):
            user_assignment[s, u] = model.NewBoolVar(f's{s + 1}_u{u + 1}')

    # Each step must be assigned exactly one user
    for s in range(instance.number_of_steps):
        model.Add(sum(user_assignment[s, u] for u in range(instance.number_of_users)) == 1)

    # Authorization constraints
    for u in range(instance.number_of_users):
        if instance.auth[u]:  # Only apply if specific authorizations exist
            for s in range(instance.number_of_steps):
                if s not in instance.auth[u]:
                    other_users_available = any(s in instance.auth[other_u]
                                                for other_u in range(instance.number_of_users)
                                                if other_u != u)
                    if other_users_available:
                        model.Add(user_assignment[s, u] == 0)

    # Separation of duty
    for (s1, s2) in instance.SOD:
        for u in range(instance.number_of_users):
            can_separate = any(s1 in instance.auth[u1] and s2 in instance.auth[u2]
                               for u1 in range(instance.number_of_users)
                               for u2 in range(instance.number_of_users)
                               if u1 != u2)
            if can_separate:
                model.Add(user_assignment[s1, u] + user_assignment[s2, u] <= 1)

    # Binding of duty
    for (s1, s2) in instance.BOD:
        for u in range(instance.number_of_users):
            if (not instance.auth[u] or
                    (s1 in instance.auth[u] and s2 in instance.auth[u])):
                model.Add(user_assignment[s1, u] == user_assignment[s2, u])

    # At-most-k constraints
    for (k, steps) in instance.at_most_k:
        for u in range(instance.number_of_users):
            step_sum = sum(user_assignment[s, u] for s in steps)
            model.Add(step_sum <= k)

    # One-team constraints
    for (steps, teams) in instance.one_team:
        team_vars = [model.NewBoolVar(f'team_{t}') for t in range(len(teams))]
        model.Add(sum(team_vars) == 1)

        for s in steps:
            for t, team in enumerate(teams):
                for u in range(instance.number_of_users):
                    if u not in team:
                        model.Add(user_assignment[s, u] == 0).OnlyEnforceIf(team_vars[t])

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 8
    solver.parameters.optimize_with_core = True
    solver.parameters.linearization_level = 0
    status = solver.Solve(model)

    # Process results
    result = {'status': status}

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        assignments = []
        for s in range(instance.number_of_steps):
            for u in range(instance.number_of_users):
                if solver.Value(user_assignment[s, u]):
                    assignments.append((s + 1, u + 1))  # Convert to 1-based indexing
        result['assignments'] = assignments

    return result
