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
            InstanceParser._parse_one_team,
            InstanceParser._parse_sual,
            InstanceParser._parse_wang_li,
            InstanceParser._parse_ada,
        ]
        
        for parser in parsers:
            if parser(line, instance):
                print(parser.__name__)
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

    @staticmethod
    def _parse_sual(line, instance):
        """Parse super-user at-least constraint"""
        m = re.match(r'^Super-user-at-least\s+(\d+)\s+((?:s\d+\s*)+)([u\d\s]+)$', line)
        if not m:
            return False
            
        try:
            h = int(m.group(1))
            # Parse steps
            scope = tuple(int(step_match.group(1)) - 1 
                    for step_match in re.finditer(r's(\d+)', m.group(2)))
            # Parse super users
            super_users = set(int(user_match.group(1)) - 1 
                        for user_match in re.finditer(r'u(\d+)', m.group(3)))
            
            if not hasattr(instance, 'sual'):
                instance.sual = []
                
            instance.sual.append((scope, h, super_users))
            
            # Update constraint graph
            for s1 in scope:
                for s2 in scope:
                    if s1 != s2:
                        instance.constraint_graph[s1].add(s2)
                        instance.constraint_graph[s2].add(s1)
            print("Parsed SUAL constraint successfully")
            return True
            
        except Exception as e:
            print(f"Error parsing SUAL: {str(e)}\nLine: {line}")
            return False

    @staticmethod
    def _parse_wang_li(line, instance):
        """Parse Wang-Li constraint"""
        m = re.match(r'^Wang-li\s+((?:s\d+\s*)+)((?:\s*\([u\d\s]+\))+)$', line)
        if not m:
            return False
            
        try:
            scope = tuple(int(step_match.group(1)) - 1 
                    for step_match in re.finditer(r's(\d+)', m.group(1)))
            
            departments = []
            dept_pattern = r'\(((?:u\d+\s*)+)\)'
            for dept_match in re.finditer(dept_pattern, m.group(2)):
                dept = set(int(user_match.group(1)) - 1 
                        for user_match in re.finditer(r'u(\d+)', dept_match.group(1)))
                departments.append(dept)
                
            if not hasattr(instance, 'wang_li'):
                instance.wang_li = []
                
            instance.wang_li.append((scope, departments))
            print("Parsed Wang-Li constraint successfully")
            return True
            
        except Exception as e:
            print(f"Error parsing Wang-Li: {str(e)}\nLine: {line}")
            return False

    @staticmethod
    def _parse_ada(line, instance):
        """Parse assignment-dependent authorization constraint"""
        m = re.match(r'^Assignment-dependent\s+s(\d+)\s+s(\d+)\s+\(((?:u\d+\s*)+)\)\s+\(((?:u\d+\s*)+)\)$', line)
        if not m:
            return False
            
        try:
            s1 = int(m.group(1)) - 1
            s2 = int(m.group(2)) - 1
            source_users = set(int(user_match.group(1)) - 1 
                        for user_match in re.finditer(r'u(\d+)', m.group(3)))
            target_users = set(int(user_match.group(1)) - 1 
                        for user_match in re.finditer(r'u(\d+)', m.group(4)))
            
            if not hasattr(instance, 'ada'):
                instance.ada = []
                
            instance.ada.append((s1, s2, source_users, target_users))
            
            instance.constraint_graph[s1].add(s2)
            instance.constraint_graph[s2].add(s1)
            print("Parsed ADA constraint successfully")
            return True
            
        except Exception as e:
            print(f"Error parsing ADA: {str(e)}\nLine: {line}")
            return False
    