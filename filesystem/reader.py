from typings import Instance


def parse_instance_file(filename):
    """Parse our WSP instance format into the solver's Instance class format"""
    instance = Instance()  # Using original Instance class
    
    with open(filename, 'r') as f:
        # Parse header
        instance.number_of_steps = int(f.readline().strip().split(':')[1])
        instance.number_of_users = int(f.readline().strip().split(':')[1]) 
        instance.number_of_constraints = int(f.readline().strip().split(':')[1])
        
        # Initialize auth lists
        instance.auth = [[] for _ in range(instance.number_of_users)]
        
        # Parse constraints
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Authorisations'):
                # Format: Authorisations u1 s1 s2
                parts = line.split()
                user = int(parts[1][1:]) - 1  # Convert u1 to 0-based
                steps = [int(s[1:]) - 1 for s in parts[2:]]  # Convert s1,s2 to 0-based
                instance.auth[user] = steps
                
            elif line.startswith('Separation-of-duty'):
                # Format: Separation-of-duty s1 s2
                parts = line.split()
                s1 = int(parts[1][1:]) - 1
                s2 = int(parts[2][1:]) - 1
                instance.SOD.append((s1, s2))
                
            elif line.startswith('Binding-of-duty'):
                # Format: Binding-of-duty s1 s2
                parts = line.split()
                s1 = int(parts[1][1:]) - 1
                s2 = int(parts[2][1:]) - 1
                instance.BOD.append((s1, s2))
                
            elif line.startswith('At-most-k'):
                # Format: At-most-k 2 s1 s2 s3
                parts = line.split()
                k = int(parts[1])
                steps = [int(s[1:]) - 1 for s in parts[2:]]
                instance.at_most_k.append((k, steps))
                
            elif line.startswith('One-team'):
                # Format: One-team s1 s2 s3 (u1 u2) (u3 u4 u5)
                parts = line.split()
                # Parse steps until first parenthesis
                steps = []
                i = 1
                while i < len(parts) and not parts[i].startswith('('):
                    steps.append(int(parts[i][1:]) - 1)
                    i += 1
                
                # Parse teams
                teams = []
                current_team = []
                for part in parts[i:]:
                    if part.startswith('('):
                        if current_team:
                            teams.append(current_team)
                        current_team = []
                        # Handle single-user team case
                        if part.endswith(')'):
                            user = int(part[2:-1]) - 1
                            current_team.append(user)
                        else:
                            user = int(part[2:]) - 1
                            current_team.append(user)
                    elif part.endswith(')'):
                        user = int(part[1:-1]) - 1
                        current_team.append(user)
                        teams.append(current_team)
                        current_team = []
                    else:
                        user = int(part[1:]) - 1
                        current_team.append(user)
                
                if current_team:
                    teams.append(current_team)
                
                instance.one_team.append((steps, teams))
    
    return instance
