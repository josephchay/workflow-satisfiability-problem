import re
from typings import Authorisations, NotEquals, AtMost, OneTeam


class Instance:
    def __init__(self, filename):
        f = open(filename, 'r')
        
        # Parse header
        self.k = int(re.match(r'#Steps:\s+(\d+)', f.readline(), re.IGNORECASE).group(1))
        self.n = int(re.match(r'#Users:\s+(\d+)', f.readline(), re.IGNORECASE).group(1))
        self.m = int(re.match(r'#Constraints:\s+(\d+)', f.readline(), re.IGNORECASE).group(1))

        # Initialize authorizations
        self.auths = []
        for _ in range(self.n):
            auth = Authorisations()
            auth.collection = [False] * self.k  # Initialize all steps as unauthorized
            self.auths.append(auth)

        # Read all constraints
        self.cons = []
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith('Authorisations'):
                # Format: Authorisations u1 s1 s2
                parts = line.split()
                user = int(parts[1][1:]) - 1  # Convert u1 to 0-based
                steps = [int(s[1:]) - 1 for s in parts[2:]]  # Convert s1 to 0-based
                
                # Set authorized steps for this user
                self.auths[user].u = user
                for step in steps:
                    self.auths[user].collection[step] = True

            elif line.startswith('Separation-of-duty'):
                c = NotEquals()
                c.read(line)
                if c.test_feasibility(self):
                    self.cons.append(c)
                
            elif line.startswith('Binding-of-duty'):
                c = NotEquals()  # Reuse NotEquals class but invert in test_satisfiability
                c.read_bod(line)  # Special reader for BoD
                if c.test_feasibility(self):
                    self.cons.append(c)

            elif line.startswith('At-most-k'):
                c = AtMost()
                c.read(line)
                if c.test_feasibility(self):
                    self.cons.append(c)

            elif line.startswith('One-team'):
                c = OneTeam()
                c.read(line)
                if c.test_feasibility(self):
                    self.cons.append(c)

        f.close()
        
    def __str__(self):
        """String representation for debugging"""
        return f"WSP Instance: {self.k} steps, {self.n} users, {self.m} constraints"
