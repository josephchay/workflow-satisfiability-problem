from typing import Dict
import time
import itertools
import subprocess
import tempfile
import os
import re

from initializers import init_jvm
from solvers import BaseWSPSolver


class SAT4JUDPBWSPSolver(BaseWSPSolver):
    """User-Dependent Pseudo-Boolean encoding using SAT4J"""
    def __init__(self, instance, active_constraints):
        super().__init__(instance, active_constraints)

        # Initialize JVM for SAT4J
        init_jvm()
    
    def solve(self) -> Dict:
        print("Starting UDPB solving...")
        
        # Track variables and constraints
        self.var_count = 0
        self.constraints = []
        
        # Create assignment variables and constraints
        x = self._create_assignment_variables()
        
        # Add constraints based on active flags
        if self.active_constraints['authorizations']:
            self._add_authorization_constraints(x)
            
        if self.active_constraints['separation_of_duty']:
            self._add_separation_of_duty_constraints(x)
            
        if self.active_constraints['binding_of_duty']:
            self._add_binding_of_duty_constraints(x)
            
        if self.active_constraints['at_most_k']:
            self._add_at_most_k_constraints(x)
            
        if self.active_constraints['one_team']:
            self._add_one_team_constraints(x)

        # Write constraints to temporary file
        with tempfile.NamedTemporaryFile(mode='w', prefix='pb-', delete=False) as f:
            # Write correct PB format header
            f.write(f'* #variable= {self.var_count} #constraint= {len(self.constraints)}\n')
            for constraint in self.constraints:
                self._write_constraint(f, constraint)
            temp_filename = f.name

        # Call SAT4J solver
        start_time = time.time()
        try:
            # Add timeout to prevent infinite runs
            result = subprocess.run(
                ['java', '-jar', os.path.join('assets', 'sat4j-pb.jar'), 'Default', temp_filename],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse solution
            solution = None
            for line in result.stdout.splitlines():
                if line.startswith("s SATISFIABLE"):
                    solution = []
                elif solution is not None and line.startswith("v "):
                    # Extract assignments
                    assignments = line[2:].split()
                    for assign in assignments:
                        if not assign.startswith("-"):  # Only look at positive assignments
                            var_num = int(assign.replace("x", ""))
                            # Convert variable number back to step/user assignment
                            for s in range(self.instance.number_of_steps):
                                for u in range(self.instance.number_of_users):
                                    if x[s][u] == var_num:
                                        solution.append({'step': s + 1, 'user': u + 1})

            end_time = time.time()
            
            # Clean up temp file
            os.unlink(temp_filename)

            if solution:
                return {
                    'sat': 'sat',
                    'result_exe_time': (end_time - start_time) * 1000,  # Convert to ms
                    'sol': solution,
                    'solution_count': 1,  # SAT4J returns one solution
                    'is_unique': False  # Cannot determine uniqueness
                }
            else:
                return {
                    'sat': 'unsat',
                    'result_exe_time': (end_time - start_time) * 1000,
                    'sol': [],
                    'solution_count': 0,
                    'is_unique': False
                }

        except subprocess.TimeoutExpired:
            print("SAT4J solver timed out after 5 minutes")
            return {
                'sat': 'timeout',
                'result_exe_time': 300000,  # 5 minutes in ms
                'sol': [],
                'solution_count': 0,
                'is_unique': False
            }
        except Exception as e:
            print(f"Error running SAT4J: {str(e)}")
            return {
                'sat': 'error',
                'result_exe_time': 0,
                'sol': [],
                'solution_count': 0,
                'is_unique': False
            }

    def _create_assignment_variables(self):
        """Create assignment variables x[s][u]"""
        x = []
        for s in range(self.instance.number_of_steps):
            row = []
            for u in range(self.instance.number_of_users):
                if not self.instance.auth[u] or s in self.instance.auth[u]:
                    self.var_count += 1
                    row.append(self.var_count)
                else:
                    row.append(None)
            # Each step must be assigned exactly one user
            self.constraints.append({
                'left': [v for v in row if v is not None],
                'relation': '=',
                'right': [],
                'right_const': 1
            })
            x.append(row)
        return x

    def _add_authorization_constraints(self, x):
        """Add authorization constraints"""
        for u in range(self.instance.number_of_users):
            if self.instance.auth[u]:
                for s in range(self.instance.number_of_steps):
                    if s not in self.instance.auth[u] and x[s][u] is not None:
                        self.constraints.append({
                            'left': [x[s][u]],
                            'relation': '=',
                            'right': [],
                            'right_const': 0
                        })

    def _add_separation_of_duty_constraints(self, x):
        """Add separation of duty constraints"""
        for s1, s2 in self.instance.SOD:
            for u in range(self.instance.number_of_users):
                if x[s1][u] is not None and x[s2][u] is not None:
                    self.constraints.append({
                        'left': [x[s1][u], x[s2][u]],
                        'relation': '<=',
                        'right': [],
                        'right_const': 1
                    })

    def _add_binding_of_duty_constraints(self, x):
        """Add binding of duty constraints"""
        for s1, s2 in self.instance.BOD:
            for u in range(self.instance.number_of_users):
                if x[s1][u] is not None and x[s2][u] is not None:
                    self.constraints.append({
                        'left': [x[s1][u]],
                        'relation': '=',
                        'right': [x[s2][u]],
                        'right_const': 0
                    })

    def _add_at_most_k_constraints(self, x):
        """Add at-most-k constraints"""
        for k, steps in self.instance.at_most_k:
            # Create user flag variables
            z = []
            for u in range(self.instance.number_of_users):
                self.var_count += 1
                z.append(self.var_count)
                
            for u in range(self.instance.number_of_users):
                for s in steps:
                    if x[s][u] is not None:
                        self.constraints.append({
                            'left': [z[u]],
                            'relation': '>=',
                            'right': [x[s][u]],
                            'right_const': 0
                        })

            self.constraints.append({
                'left': z,
                'relation': '<=',
                'right': [],
                'right_const': k
            })

    def _add_one_team_constraints(self, x):
        """Add one-team constraints"""
        for steps, teams in self.instance.one_team:
            # Create team selection variables
            team_vars = []
            for _ in range(len(teams)):
                self.var_count += 1
                team_vars.append(self.var_count)
            
            # Exactly one team must be selected
            self.constraints.append({
                'left': team_vars,
                'relation': '=',
                'right': [],
                'right_const': 1
            })
            
            for team_idx, team in enumerate(teams):
                for step in steps:
                    # Only allow assignments to team members when team is selected
                    for u in range(self.instance.number_of_users):
                        if x[step][u] is not None:
                            if u not in team:
                                self.constraints.append({
                                    'left': [team_vars[team_idx], x[step][u]],
                                    'relation': '<=',
                                    'right': [],
                                    'right_const': 1
                                })

    def _write_constraint(self, f, constraint):
        """Write a constraint in SAT4J PB format"""
        # Similar to PBPB but without pattern variables
        line = ""
        
        # Add left side terms
        for var in constraint["left"]:
            line += f"+1 x{var} "
            
        # Add right side terms
        for var in constraint["right"]:
            line += f"-1 x{var} "
            
        # Add relation and right constant    
        line += f"{constraint['relation']} {constraint['right_const']}"
        
        f.write(line + ";\n")

    def _parse_sat4j_output(self, output, x):
        """Parse SAT4J output and convert to solution format"""
        for line in output.splitlines():
            if line.startswith("s UNSATISFIABLE"):
                return None
            elif line.startswith("v"):
                # Extract variables set to 1
                ones = [int(match.group(1)) for match in re.finditer(r' x(\d+)', line)]
                
                # Convert to solution format
                solution = []
                for s in range(self.instance.number_of_steps):
                    for u in range(self.instance.number_of_users):
                        if x[s][u] is not None and x[s][u] in ones:
                            solution.append({'step': s + 1, 'user': u + 1})
                return solution
        return None


class SAT4JPBPBWSPSolver(BaseWSPSolver):
    """Pattern-Based Pseudo-Boolean encoding using SAT4J"""

    def __init__(self, instance, active_constraints):
        super().__init__(instance, active_constraints)

        # Initialize JVM for SAT4J
        init_jvm()
    
    def solve(self) -> Dict:
        print("Starting PBPB solving...")
        
        # Track variables and constraints
        self.var_count = 0
        self.constraints = []
        
        # Create assignment and pattern variables
        x = self._create_assignment_variables()
        M = self._create_pattern_variables()
        
        # Add pattern constraints
        self._add_pattern_constraints(x, M)
        
        # Add active constraints
        if self.active_constraints['authorizations']:
            self._add_authorization_constraints(x)
            
        if self.active_constraints['separation_of_duty']:
            self._add_separation_of_duty_constraints(M)
            
        if self.active_constraints['binding_of_duty']:
            self._add_binding_of_duty_constraints(M)
            
        if self.active_constraints['at_most_k']:
            self._add_at_most_k_constraints(M)
            
        if self.active_constraints['one_team']:
            self._add_one_team_constraints(x, M)

        # Write constraints to temporary file
        with tempfile.NamedTemporaryFile(mode='w', prefix='pb-', delete=False) as f:
            # Write correct PB format header
            f.write(f'* #variable= {self.var_count} #constraint= {len(self.constraints)}\n')
            for constraint in self.constraints:
                self._write_constraint(f, constraint)
            temp_filename = f.name

        # Call SAT4J solver
        start_time = time.time()
        try:
            # Add timeout to prevent infinite runs
            result = subprocess.run(
                ['java', '-jar', os.path.join('assets', 'sat4j-pb.jar'), 'Default', temp_filename],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Debug output
            print("SAT4J Output:")
            print(result.stdout)
            print("SAT4J Errors:")
            print(result.stderr)
            
            # Parse solution
            solution = None
            for line in result.stdout.splitlines():
                if line.startswith("s SATISFIABLE"):
                    solution = []
                elif solution is not None and line.startswith("v "):
                    # Extract assignments
                    assignments = line[2:].split()
                    for assign in assignments:
                        if not assign.startswith("-"):  # Only look at positive assignments
                            var_num = int(assign.replace("x", ""))
                            # Convert variable number back to step/user assignment
                            for s in range(self.instance.number_of_steps):
                                for u in range(self.instance.number_of_users):
                                    if x[s][u] == var_num:
                                        solution.append({'step': s + 1, 'user': u + 1})

            end_time = time.time()
            
            # Clean up temp file
            os.unlink(temp_filename)

            if solution:
                return {
                    'sat': 'sat',
                    'result_exe_time': (end_time - start_time) * 1000,  # Convert to ms
                    'sol': solution,
                    'solution_count': 1,  # SAT4J returns one solution
                    'is_unique': False  # Cannot determine uniqueness
                }
            else:
                return {
                    'sat': 'unsat',
                    'result_exe_time': (end_time - start_time) * 1000,
                    'sol': [],
                    'solution_count': 0,
                    'is_unique': False
                }

        except subprocess.TimeoutExpired:
            print("SAT4J solver timed out after 5 minutes")
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
            return {
                'sat': 'timeout',
                'result_exe_time': 300000,  # 5 minutes in ms
                'sol': [],
                'solution_count': 0,
                'is_unique': False
            }
        except Exception as e:
            print(f"Error running SAT4J: {str(e)}")
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
            return {
                'sat': 'error',
                'result_exe_time': 0,
                'sol': [],
                'solution_count': 0,
                'is_unique': False
            }

    def _create_assignment_variables(self):
        """Create assignment variables x[s][u]"""
        x = []
        for s in range(self.instance.number_of_steps):
            row = []
            for u in range(self.instance.number_of_users):
                if not self.instance.auth[u] or s in self.instance.auth[u]:
                    self.var_count += 1
                    row.append(self.var_count)
                else:
                    row.append(None)
            # Each step must be assigned exactly one user
            self.constraints.append({
                'left': [v for v in row if v is not None],
                'relation': '=',
                'right': [],
                'right_const': 1
            })
            x.append(row)
        return x

    def _create_pattern_variables(self):
        """Create pattern variables M[s1][s2]"""
        M = [[None for _ in range(self.instance.number_of_steps)] 
             for _ in range(self.instance.number_of_steps)]
        
        for s1 in range(self.instance.number_of_steps):
            for s2 in range(s1 + 1, self.instance.number_of_steps):
                self.var_count += 1
                M[s1][s2] = M[s2][s1] = self.var_count
                
        return M

    def _add_authorization_constraints(self, x):
        """Add authorization constraints"""
        for u in range(self.instance.number_of_users):
            if self.instance.auth[u]:
                for s in range(self.instance.number_of_steps):
                    if s not in self.instance.auth[u] and x[s][u] is not None:
                        self.constraints.append({
                            'left': [x[s][u]],
                            'relation': '=',
                            'right': [],
                            'right_const': 0
                        })

    def _add_pattern_constraints(self, x, M):
        """Add pattern-related constraints"""
        # Transitivity constraints with simpler encoding
        for s1, s2, s3 in itertools.combinations(range(self.instance.number_of_steps), 3):
            if s1 < s2 and s2 < s3:
                # If s1,s2 same user and s2,s3 same user then s1,s3 must be same user
                self.constraints.append({
                    'left': [M[s1][s3]],
                    'relation': '>=',
                    'right': [M[s1][s2], M[s2][s3]],
                    'right_const': -1
                })
        
        # Link M variables with x variables - simpler encoding
        for s1, s2 in itertools.combinations(range(self.instance.number_of_steps), 2):
            for u in range(self.instance.number_of_users):
                if x[s1][u] is not None and x[s2][u] is not None:
                    # If either step assigned to user, pattern must match
                    self.constraints.append({
                        'left': [x[s1][u], x[s2][u]],
                        'relation': '<=',
                        'right': [M[s1][s2]],
                        'right_const': 1
                    })

    def _add_separation_of_duty_constraints(self, M):
        """Add separation of duty constraints"""
        for s1, s2 in self.instance.SOD:
            if s1 < s2:
                # If steps s1 and s2 are separated, M[s1][s2] must be 0
                self.constraints.append({
                    'left': [M[s1][s2]],
                    'relation': '=',
                    'right': [],
                    'right_const': 0
                })

    def _add_binding_of_duty_constraints(self, M):
        """Add binding of duty constraints"""
        for s1, s2 in self.instance.BOD:
            if s1 < s2:
                # If steps s1 and s2 are bound, M[s1][s2] must be 1
                self.constraints.append({
                    'left': [M[s1][s2]],
                    'relation': '=',
                    'right': [],
                    'right_const': 1
                })

    def _add_at_most_k_constraints(self, M):
        """Add at-most-k constraints"""
        for k, steps in self.instance.at_most_k:
            for subset in itertools.combinations(steps, k + 1):
                same_user_vars = []
                # For each pair in the subset, at least one pair must be same user
                for s1, s2 in itertools.combinations(subset, 2):
                    if s1 < s2:
                        same_user_vars.append(M[s1][s2])
                    else:
                        same_user_vars.append(M[s2][s1])
                if same_user_vars:
                    # At least one pair must be assigned to same user
                    self.constraints.append({
                        'left': same_user_vars,
                        'relation': '>=',
                        'right': [],
                        'right_const': 1
                    })

    def _add_one_team_constraints(self, x, M):
        """Add one-team constraints"""
        for steps, teams in self.instance.one_team:
            # Create team selection variables
            team_vars = []
            for _ in range(len(teams)):
                self.var_count += 1
                team_vars.append(self.var_count)
            
            # Exactly one team must be selected
            self.constraints.append({
                'left': team_vars,
                'relation': '=',
                'right': [],
                'right_const': 1
            })
            
            # If a team is selected, all steps in the scope must be assigned to members of that team
            for team_idx, team in enumerate(teams):
                # Within team, steps must be assigned to same user
                for s1, s2 in itertools.combinations(steps, 2):
                    if s1 < s2:
                        self.constraints.append({
                            'left': [team_vars[team_idx], M[s1][s2]], 
                            'relation': '<=',
                            'right': [],
                            'right_const': 1
                        })
                
                # Only allow assignments to team members when team is selected
                for step in steps:
                    for u in range(self.instance.number_of_users):
                        if u not in team and x[step][u] is not None:
                            self.constraints.append({
                                'left': [team_vars[team_idx], x[step][u]],
                                'relation': '<=',
                                'right': [],
                                'right_const': 1
                            })
            
            # Ensure steps can only be assigned to users in the selected team
            users_in_teams = list(set().union(*teams))
            for step in steps:
                for u in range(self.instance.number_of_users):
                    if u not in users_in_teams and x[step][u] is not None:
                        self.constraints.append({
                            'left': [x[step][u]],
                            'relation': '=',
                            'right': [],
                            'right_const': 0
                        })

    def _write_constraint(self, f, constraint):
        """Write a constraint in SAT4J format"""
        # Write in SAT4J's PB format
        line = ""
        
        # Add left side terms
        for var in constraint["left"]:
            line += f"+1 x{var} "
            
        # Add right side terms (with negative coefficients)
        for var in constraint["right"]:
            line += f"-1 x{var} "
            
        # Add relation and right constant
        if constraint["relation"] == "=":
            line += f"= {constraint['right_const']}"
        elif constraint["relation"] == ">=":
            line += f">= {constraint['right_const']}"
        elif constraint["relation"] == "<=":
            line += f"<= {constraint['right_const']}"
        
        f.write(line + ";\n")

    def _parse_sat4j_output(self, output, x):
        """Parse SAT4J output and convert to solution format"""
        solution = None
        for line in output.splitlines():
            if line.startswith("s SATISFIABLE"):
                solution = []
            elif line.startswith("v "):
                # Extract assignments
                assignments = line[2:].split()
                for assign in assignments:
                    if not assign.startswith("-"):  # Only look at positive assignments
                        var_num = int(assign.replace("x", ""))
                        # Convert variable number back to step/user assignment
                        for s in range(self.instance.number_of_steps):
                            for u in range(self.instance.number_of_users):
                                if x[s][u] == var_num:
                                    solution.append({'step': s + 1, 'user': u + 1})
        return solution
