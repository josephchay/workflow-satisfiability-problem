import re
from typing import List, Dict, Any
from typings import Authorisations, NotEquals, AtMost, OneTeam


class Instance:
    def __init__(self, filename):
        """
        Initialize an Instance by parsing a WSP file.
        
        Args:
            filename (str): Path to the WSP instance file
        """
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
                self._parse_authorisations(line)
            elif line.startswith('Separation-of-duty'):
                self._add_constraint(NotEquals(), line)
            elif line.startswith('Binding-of-duty'):
                self._add_bod_constraint(line)
            elif line.startswith('At-most-k'):
                self._add_constraint(AtMost(), line)
            elif line.startswith('One-team'):
                self._add_constraint(OneTeam(), line)

        f.close()

    def _parse_authorisations(self, line: str):
        """
        Parse and set authorizations for a user.
        
        Args:
            line (str): Authorization constraint line
        """
        parts = line.split()
        user = int(parts[1][1:]) - 1  # Convert u1 to 0-based
        steps = [int(s[1:]) - 1 for s in parts[2:]]  # Convert s1 to 0-based
        
        # Set authorized steps for this user
        self.auths[user].u = user
        for step in steps:
            self.auths[user].collection[step] = True

    def _add_constraint(self, constraint, line: str):
        """
        Add a constraint after testing its feasibility.
        
        Args:
            constraint: Constraint object to add
            line (str): Constraint line
        """
        constraint.read(line)
        if constraint.test_feasibility(self):
            self.cons.append(constraint)

    def _add_bod_constraint(self, line: str):
        """
        Add a binding of duty constraint.
        
        Args:
            line (str): Binding of duty constraint line
        """
        c = NotEquals()  # Reuse NotEquals class but invert in test_satisfiability
        c.read_bod(line)  # Special reader for BoD
        if c.test_feasibility(self):
            self.cons.append(c)

    def get_constraint_summary(self) -> Dict[str, int]:
        """
        Get a summary of constraint types.
        
        Returns:
            Dict[str, int]: Count of each constraint type
        """
        constraint_types = {
            'Separation of Duty': sum(1 for c in self.cons if isinstance(c, NotEquals) and not getattr(c, 'is_bod', False)),
            'Binding of Duty': sum(1 for c in self.cons if isinstance(c, NotEquals) and getattr(c, 'is_bod', False)),
            'At-most-k': sum(1 for c in self.cons if isinstance(c, AtMost)),
            'One-team': sum(1 for c in self.cons if isinstance(c, OneTeam))
        }
        return constraint_types

    def get_authorization_stats(self) -> Dict[str, Any]:
        """
        Compute authorization statistics.
        
        Returns:
            Dict[str, Any]: Authorization statistics
        """
        total_steps = self.k
        total_users = self.n
        
        # Users with at least one authorization
        users_with_auth = sum(1 for auth in self.auths if any(auth.collection))
        
        # Steps with at least one authorized user
        steps_with_auth = [
            sum(1 for auth in self.auths if auth.collection[step])
            for step in range(total_steps)
        ]
        
        return {
            'total_steps': total_steps,
            'total_users': total_users,
            'users_with_authorization': users_with_auth,
            'users_with_auth_percentage': users_with_auth / total_users * 100,
            'max_users_per_step': max(steps_with_auth) if steps_with_auth else 0,
            'min_users_per_step': min(steps_with_auth) if steps_with_auth else 0,
            'avg_users_per_step': sum(steps_with_auth) / total_steps if steps_with_auth else 0
        }

    def get_constraint_coverage(self) -> Dict[str, float]:
        """
        Compute the coverage of different constraint types.
        
        Returns:
            Dict[str, float]: Constraint coverage percentages
        """
        total_constraints = len(self.cons)
        if total_constraints == 0:
            return {}
        
        constraint_summary = self.get_constraint_summary()
        return {
            constraint: count / total_constraints * 100
            for constraint, count in constraint_summary.items()
        }

    def validate(self) -> bool:
        """
        Validate the entire instance configuration.
        
        Returns:
            bool: True if the instance is valid, False otherwise
        """
        # Check if number of constraints matches
        if len(self.cons) != self.m:
            return False
        
        # Check authorizations
        if len(self.auths) != self.n:
            return False
        
        # Verify each authorization
        for auth in self.auths:
            if len(auth.collection) != self.k:
                return False
        
        return True

    def __str__(self):
        """
        String representation for debugging.
        
        Returns:
            str: Detailed instance description
        """
        constraint_summary = self.get_constraint_summary()
        auth_stats = self.get_authorization_stats()
        
        return (
            f"WSP Instance:\n"
            f"  Steps: {self.k}\n"
            f"  Users: {self.n}\n"
            f"  Constraints: {self.m}\n"
            f"  Constraint Breakdown:\n"
            f"    - Separation of Duty: {constraint_summary['Separation of Duty']}\n"
            f"    - Binding of Duty: {constraint_summary['Binding of Duty']}\n"
            f"    - At-most-k: {constraint_summary['At-most-k']}\n"
            f"    - One-team: {constraint_summary['One-team']}\n"
            f"  Authorization Stats:\n"
            f"    - Users with Authorization: {auth_stats['users_with_authorization']} "
            f"({auth_stats['users_with_auth_percentage']:.2f}%)\n"
            f"    - Max Users per Step: {auth_stats['max_users_per_step']}\n"
            f"    - Min Users per Step: {auth_stats['min_users_per_step']}\n"
            f"    - Avg Users per Step: {auth_stats['avg_users_per_step']:.2f}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert instance to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary with instance details
        """
        return {
            'steps': self.k,
            'users': self.n,
            'constraints': self.m,
            'constraint_summary': self.get_constraint_summary(),
            'authorization_stats': self.get_authorization_stats(),
            'constraint_coverage': self.get_constraint_coverage()
        }
