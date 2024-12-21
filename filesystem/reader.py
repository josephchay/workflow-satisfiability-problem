from typing import List

from typings import Instance


class InstanceParser:
    """
    A robust parser for Workflow Satisfiability Problem (WSP) instance files.
    
    Handles parsing of complex instance files with multiple constraint types,
    providing a clean and extensible approach to loading WSP instances.
    """

    def __init__(self, filename: str):
        """
        Initialize the parser with the given filename.
        
        Args:
            filename (str): Path to the WSP instance file
        """
        self.filename = filename
        self.instance = Instance()
        self._parse_file()

    def _parse_file(self):
        """
        Parse the entire instance file.
        """
        with open(self.filename, 'r') as f:
            # Parse header
            header_lines = [f.readline(), f.readline(), f.readline()]
            self._parse_header(header_lines)
            
            # Parse constraints
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    if line.startswith('Authorisations'):
                        self._parse_authorisations(line)
                    elif line.startswith('Separation-of-duty'):
                        self._parse_sod(line)
                    elif line.startswith('Binding-of-duty'):
                        self._parse_bod(line)
                    elif line.startswith('At-most-k'):
                        self._parse_at_most_k(line)
                    elif line.startswith('One-team'):
                        self._parse_one_team(line)
                except Exception as e:
                    raise ValueError(f"Error parsing line: {line}. {str(e)}")

    def _parse_header(self, header_lines: List[str]):
        """
        Parse the header of the instance file.
        
        Args:
            header_lines (List[str]): Lines containing header information
        """
        try:
            self.instance.number_of_steps = int(header_lines[0].strip().split(':')[1])
            self.instance.number_of_users = int(header_lines[1].strip().split(':')[1])
            self.instance.number_of_constraints = int(header_lines[2].strip().split(':')[1])
            
            # Initialize auth lists
            self.instance.auth = [[] for _ in range(self.instance.number_of_users)]
        except (IndexError, ValueError) as e:
            raise ValueError(f"Invalid header format: {e}")

    def _parse_authorisations(self, line: str):
        """
        Parse authorization constraints.
        
        Args:
            line (str): Authorization constraint line
        """
        parts = line.split()
        user = int(parts[1][1:]) - 1  # Convert u1 to 0-based
        steps = [int(s[1:]) - 1 for s in parts[2:]]  # Convert s1,s2 to 0-based
        self.instance.auth[user] = steps

    def _parse_sod(self, line: str):
        """
        Parse separation of duty constraints.
        
        Args:
            line (str): Separation of duty constraint line
        """
        parts = line.split()
        s1 = int(parts[1][1:]) - 1
        s2 = int(parts[2][1:]) - 1
        self.instance.SOD.append((s1, s2))

    def _parse_bod(self, line: str):
        """
        Parse binding of duty constraints.
        
        Args:
            line (str): Binding of duty constraint line
        """
        parts = line.split()
        s1 = int(parts[1][1:]) - 1
        s2 = int(parts[2][1:]) - 1
        self.instance.BOD.append((s1, s2))

    def _parse_at_most_k(self, line: str):
        """
        Parse at-most-k constraints.
        
        Args:
            line (str): At-most-k constraint line
        """
        parts = line.split()
        k = int(parts[1])
        steps = [int(s[1:]) - 1 for s in parts[2:]]
        self.instance.at_most_k.append((k, steps))

    def _parse_one_team(self, line: str):
        """
        Parse one-team constraints.
        
        Args:
            line (str): One-team constraint line
        """
        parts = line.split()
        
        # Parse steps
        steps = []
        i = 1
        while i < len(parts) and not parts[i].startswith('('):
            steps.append(int(parts[i][1:]) - 1)
            i += 1
        
        # Parse teams
        teams = self._extract_teams(parts[i:])
        
        self.instance.one_team.append((steps, teams))

    def _extract_teams(self, team_parts: List[str]) -> List[List[int]]:
        """
        Extract teams from constraint line parts.
        
        Args:
            team_parts (List[str]): Parts of the line containing team information
        
        Returns:
            List[List[int]]: List of teams, each team being a list of user indices
        """
        teams = []
        current_team = []
        
        for part in team_parts:
            if part.startswith('('):
                if current_team:
                    teams.append(current_team)
                current_team = []
                
                # Handle single and multi-user team cases
                user = int(part[2:-1] if part.endswith(')') else part[2:]) - 1
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
        
        return teams

    def get_instance(self) -> Instance:
        """
        Get the parsed Instance object.
        
        Returns:
            Instance: The parsed WSP instance
        """
        return self.instance


def parse_instance_file(filename: str) -> Instance:
    """
    Convenience function to parse an instance file.
    
    Args:
        filename (str): Path to the WSP instance file
    
    Returns:
        Instance: The parsed WSP instance
    """
    parser = InstanceParser(filename)
    return parser.get_instance()
