class Authorisations:
    def __init__(self):
        self.u = -1
        self.collection = []
        
    def test_feasibility(self, instance):
        return 0 <= self.u < instance.n


class NotEquals:
    def __init__(self):
        self.s1 = -1
        self.s2 = -1
        self.is_bod = False  # Flag to indicate if this is actually a BoD constraint
        
    def read(self, line):
        # For SoD: "Separation-of-duty s1 s2"
        parts = line.split()
        self.s1 = int(parts[1][1:]) - 1
        self.s2 = int(parts[2][1:]) - 1
        
    def read_bod(self, line):
        # For BoD: "Binding-of-duty s1 s2"
        parts = line.split()
        self.s1 = int(parts[1][1:]) - 1
        self.s2 = int(parts[2][1:]) - 1
        self.is_bod = True
        
    def test_feasibility(self, instance):
        return 0 <= self.s1 < instance.k and 0 <= self.s2 < instance.k

    def test_satisfiability(self, solution):
        if self.is_bod:
            return solution.assignment[self.s1] == solution.assignment[self.s2]
        else:
            return solution.assignment[self.s1] != solution.assignment[self.s2]


class AtMost:
    def __init__(self):
        self.limit = -1
        self.scope = []
        
    def read(self, line):
        # Format: At-most-k 2 s1 s2 s3
        parts = line.split()
        self.limit = int(parts[1])
        self.scope = [int(s[1:]) - 1 for s in parts[2:]]
        
    def test_feasibility(self, instance):
        return (0 < self.limit <= instance.k and
                all(0 <= s < instance.k for s in self.scope) and
                len(self.scope) > 0)
                
    def test_satisfiability(self, solution):
        users = set(solution.assignment[s] for s in self.scope)
        return len(users) <= self.limit


class OneTeam:
    def __init__(self):
        self.steps = []  # List of steps that must be assigned to same team
        self.teams = []  # List of lists, each inner list containing user indices
        
    def read(self, line):
        # Format: One-team s1 s2 s3 (u1 u2) (u3 u4 u5)
        parts = line.split()
        
        # Read steps until first parenthesis
        i = 1
        while i < len(parts) and not parts[i].startswith('('):
            self.steps.append(int(parts[i][1:]) - 1)  # Convert to 0-based
            i += 1
            
        # Read teams
        current_team = []
        for part in parts[i:]:
            if part.startswith('('):
                if current_team:  # If we have a previous team
                    self.teams.append(current_team)
                current_team = []
                if part.endswith(')'):  # Single user team
                    user = int(part[2:-1]) - 1
                    current_team.append(user)
                else:  # Multi-user team
                    user = int(part[2:]) - 1
                    current_team.append(user)
            elif part.endswith(')'):
                user = int(part[1:-1]) - 1
                current_team.append(user)
                self.teams.append(current_team)
                current_team = []
            else:
                user = int(part[1:]) - 1
                current_team.append(user)
                
        if current_team:  # Add last team if exists
            self.teams.append(current_team)
            
    def test_feasibility(self, instance):
        return (all(0 <= s < instance.k for s in self.steps) and
                all(all(0 <= u < instance.n for u in team) for team in self.teams) and
                len(self.teams) > 0 and
                all(len(team) > 0 for team in self.teams))
                
    def test_satisfiability(self, solution):
        # Get users assigned to these steps
        assigned_users = set(solution.assignment[s] for s in self.steps)
        # Check if all users come from one team
        return any(assigned_users.issubset(set(team)) for team in self.teams)
