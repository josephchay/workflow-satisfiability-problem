import re

from typings import Instance


class InstanceParser:
    """Parses WSP instance files"""
    @staticmethod
    def parse_file(filename):
        """Parse a WSP instance file and return an Instance object"""
        instance = Instance()
        
        with open(filename) as f:
            # Parse header
            instance.number_of_steps = InstanceParser._read_attribute(f, "#Steps")
            instance.number_of_users = InstanceParser._read_attribute(f, "#Users")
            instance.number_of_constraints = InstanceParser._read_attribute(f, "#Constraints")
            
            # Initialize authorization matrix
            instance.auth = [[] for _ in range(instance.number_of_users)]
            instance.user_step_matrix = [[False] * instance.number_of_steps 
                                       for _ in range(instance.number_of_users)]
            
            # Parse constraints
            for _ in range(instance.number_of_constraints):
                line = f.readline().strip()
                if not line:
                    continue
                    
                InstanceParser._parse_constraint(line, instance)

        # Compute derived data
        instance.compute_step_domains()
        return instance

    @staticmethod
    def _read_attribute(f, name):
        """Read a numeric attribute from the file"""
        line = f.readline()
        match = re.match(f'{name}:\\s*(\\d+)$', line)
        if match:
            return int(match.group(1))
        raise Exception(f"Could not parse line {line}")

    @staticmethod
    def _parse_constraint(line, instance):
        """Parse a single constraint line"""
        parsers = [
            InstanceParser._parse_auth,
            InstanceParser._parse_sod,
            InstanceParser._parse_bod,
            InstanceParser._parse_at_most_k,
            InstanceParser._parse_one_team
        ]
        
        for parser in parsers:
            if parser(line, instance):
                return
        
        raise Exception(f'Failed to parse line: {line}')

    @staticmethod
    def _parse_auth(line, instance):
        """Parse authorization constraint"""
        m = re.match(r"Authorisations u(\d+)(?: s\d+)*", line)
        if not m:
            return False
            
        user_id = int(m.group(1)) - 1
        for m in re.finditer(r's(\d+)', line):
            step = int(m.group(1)) - 1
            instance.auth[user_id].append(step)
            instance.user_step_matrix[user_id][step] = True
        return True

    @staticmethod
    def _parse_sod(line, instance):
        """Parse separation of duty constraint"""
        m = re.match(r'Separation-of-duty s(\d+) s(\d+)', line)
        if not m:
            return False
            
        s1, s2 = int(m.group(1)) - 1, int(m.group(2)) - 1
        instance.SOD.append((s1, s2))
        instance.constraint_graph[s1].add(s2)
        instance.constraint_graph[s2].add(s1)
        return True

    @staticmethod
    def _parse_bod(line, instance):
        """Parse binding of duty constraint"""
        m = re.match(r'Binding-of-duty s(\d+) s(\d+)', line)
        if not m:
            return False
            
        s1, s2 = int(m.group(1)) - 1, int(m.group(2)) - 1
        instance.BOD.append((s1, s2))
        instance.constraint_graph[s1].add(s2)
        instance.constraint_graph[s2].add(s1)
        return True

    @staticmethod
    def _parse_at_most_k(line, instance):
        """Parse at-most-k constraint"""
        m = re.match(r'At-most-k (\d+)(?: s\d+)+', line)
        if not m:
            return False
            
        k = int(m.group(1))
        steps = tuple(int(m.group(1)) - 1 for m in re.finditer(r's(\d+)', line))
        instance.at_most_k.append((k, steps))
        
        for s1 in steps:
            for s2 in steps:
                if s1 != s2:
                    instance.constraint_graph[s1].add(s2)
        return True

    @staticmethod
    def _parse_one_team(line, instance):
        """Parse one-team constraint"""
        m = re.match(r'One-team\s+((?:s\d+\s*)+)\(((?:u\d+\s*)+)\)((?:\s*\((?:u\d+\s*)+\))*)', line)
        if not m:
            return False
            
        steps = tuple(int(step_match.group(1)) - 1 
                     for step_match in re.finditer(r's(\d+)', m.group(1)))
                     
        teams = []
        team_pattern = r'\(((?:u\d+\s*)+)\)'
        for team_match in re.finditer(team_pattern, line):
            team = tuple(int(user_match.group(1)) - 1 
                        for user_match in re.finditer(r'u(\d+)', team_match.group(1)))
            teams.append(team)
            
        instance.one_team.append((steps, tuple(teams)))
        
        for s1 in steps:
            for s2 in steps:
                if s1 != s2:
                    instance.constraint_graph[s1].add(s2)
        return True
