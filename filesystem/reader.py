
import re
from instance import WSPInstance


def parse_instance_file(filename: str) -> WSPInstance:
    """Parse a WSP instance file and return a WSPInstance object"""
    instance = WSPInstance()
    
    with open(filename, 'r') as f:
        # Read header
        header_lines = [next(f) for _ in range(3)]
        instance.number_of_steps = int(re.search(r'\d+', header_lines[0]).group())
        instance.number_of_users = int(re.search(r'\d+', header_lines[1]).group())
        instance.number_of_constraints = int(re.search(r'\d+', header_lines[2]).group())
        
        # Initialize authorization list
        instance.auth = [[] for _ in range(instance.number_of_users)]
        
        # Read constraints
        for line in f:
            line = line.strip()
            
            # Parse Authorisations
            if line.startswith('Authorisations'):
                parts = line.split()
                user_id = int(parts[1][1:]) - 1  # Convert u1 to 0-based index
                steps = [int(s[1:]) - 1 for s in parts[2:]]  # Convert s1 to 0-based index
                instance.auth[user_id].extend(steps)
            
            # Parse Separation-of-duty
            elif line.startswith('Separation-of-duty'):
                parts = line.split()
                step1 = int(parts[1][1:]) - 1
                step2 = int(parts[2][1:]) - 1
                instance.SOD.append((step1, step2))
            
            # Parse Binding-of-duty
            elif line.startswith('Binding-of-duty'):
                parts = line.split()
                step1 = int(parts[1][1:]) - 1
                step2 = int(parts[2][1:]) - 1
                instance.BOD.append((step1, step2))
            
            # Parse At-most-k
            elif line.startswith('At-most-k'):
                parts = line.split()
                k = int(parts[1])
                steps = [int(s[1:]) - 1 for s in parts[2:]]
                instance.at_most_k.append((k, steps))
            
            # Parse One-team
            elif line.startswith('One-team'):
                # Extract steps before teams
                step_part = line.split('(')[0].strip()
                step_matches = re.findall(r's(\d+)', step_part)
                steps = [int(s) - 1 for s in step_matches]
                
                # Extract teams
                team_matches = re.findall(r'\(((?:u\d+\s*)+)\)', line)
                teams = []
                for team_str in team_matches:
                    user_matches = re.findall(r'u(\d+)', team_str)
                    team = [int(u) - 1 for u in user_matches]
                    teams.append(team)
                
                instance.one_team.append((steps, teams))
    
    return instance