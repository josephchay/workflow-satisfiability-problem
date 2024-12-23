import os
import traceback
import time
from ortools.sat.python import cp_model
import re
from collections import defaultdict


INSTANCE_METADATA = {
    'example1.txt': {'sat': True, 'unique': False},
    'example2.txt': {'sat': False, 'unique': False},
    'example3.txt': {'sat': True, 'unique': True},
    'example4.txt': {'sat': False, 'unique': False},
    'example5.txt': {'sat': True, 'unique': True},
    'example6.txt': {'sat': False, 'unique': False},
    'example7.txt': {'sat': True, 'unique': True},
    'example8.txt': {'sat': False, 'unique': False},
    'example9.txt': {'sat': True, 'unique': False},
    'example10.txt': {'sat': True, 'unique': False},
    'example11.txt': {'sat': True, 'unique': False},
    'example12.txt': {'sat': True, 'unique': False},
    'example13.txt': {'sat': False, 'unique': False},
    'example14.txt': {'sat': False, 'unique': False},
    'example15.txt': {'sat': False, 'unique': False},
    # Large instances
    'example16.txt': {'sat': True, 'unique': False},
    'example17.txt': {'sat': True, 'unique': False},
    'example18.txt': {'sat': False, 'unique': False},
    'example19.txt': {'sat': False, 'unique': False}
}


class Instance:
    """Represents a WSP problem instance"""
    def __init__(self):
        self.number_of_steps = 0
        self.number_of_users = 0
        self.number_of_constraints = 0
        self.auth = []
        self.SOD = []
        self.BOD = []
        self.at_most_k = []
        self.one_team = []
        self.user_step_matrix = None
        self.step_domains = {}
        self.constraint_graph = defaultdict(set)

    def compute_step_domains(self):
        """Compute possible users for each step based on authorizations"""
        for step in range(self.number_of_steps):
            self.step_domains[step] = set()
            for user in range(self.number_of_users):
                if self.user_step_matrix[user][step]:
                    self.step_domains[step].add(user)


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


class SolverResult:
    """Represents the result of solving a WSP instance"""
    def __init__(self, is_sat=False, solve_time=0, assignment=None, violations=None, reason=None):
        self.is_sat = is_sat
        self.solve_time = solve_time
        self.assignment = assignment or {}
        self.violations = violations or []
        self.reason = reason
        
    @staticmethod
    def create_unsat(solve_time, reason=None):
        """Create an UNSAT result"""
        return SolverResult(
            is_sat=False,
            solve_time=solve_time,
            reason=reason
        )
    
    @staticmethod
    def create_sat(solve_time, assignment):
        """Create a SAT result"""
        return SolverResult(
            is_sat=True,
            solve_time=solve_time,
            assignment=assignment
        )
        
    def get_metrics(self):
        """Get solving metrics and results"""
        return {
            'sat': 'sat' if self.is_sat else 'unsat',
            'exe_time': f"{self.solve_time * 1000:.2f}ms",
            'sol': [(step, user) for step, user in self.assignment.items()],
            'violations': self.violations,
            'reason': self.reason
        }


class VariableManager:
    """Manages CP-SAT variables for the WSP problem"""
    def __init__(self, model, instance):
        self.model = model
        self.instance = instance
        self.step_variables = {}
        self.user_step_variables = defaultdict(dict)
        
    def create_variables(self):
        """Create boolean variables for user-step assignments"""
        self.step_variables.clear()
        self.user_step_variables.clear()
        
        # Create variables only for authorized user-step pairs
        for step in range(self.instance.number_of_steps):
            self.step_variables[step] = []
            for user in range(self.instance.number_of_users):
                if self.instance.user_step_matrix[user][step]:
                    var = self.model.NewBoolVar(f's{step + 1}_u{user + 1}')
                    self.step_variables[step].append((user, var))
                    self.user_step_variables[user][step] = var


class ConstraintManager:
    """Manages constraints for the WSP problem"""
    def __init__(self, model, instance, var_manager):
        self.model = model
        self.instance = instance
        self.var_manager = var_manager
        
    def add_all_constraints(self):
        """Add all problem constraints to the model"""
        self.add_authorization_constraints()
        self.add_separation_of_duty()
        if not self.add_binding_of_duty():
            return False
        self.add_at_most_k()
        self.add_one_team()
        return True
        
    def add_authorization_constraints(self):
        """Add authorization constraints"""
        for step, user_vars in self.var_manager.step_variables.items():
            self.model.AddExactlyOne(var for _, var in user_vars)
    
    def add_binding_of_duty(self):
        """Add binding of duty constraints"""
        # Check feasibility first
        infeasible_constraints = []
        for s1, s2 in self.instance.BOD:
            common_users = set()
            for user in range(self.instance.number_of_users):
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2]):
                    common_users.add(user)
            
            if not common_users:
                infeasible_constraints.append((s1+1, s2+1))
        
        if infeasible_constraints:
            return False
        
        # Add BOD constraints
        for s1, s2 in self.instance.BOD:
            s1_vars = []
            s2_vars = []
            
            for user in range(self.instance.number_of_users):
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    self.model.Add(var1 == var2)
                    s1_vars.append(var1)
                    s2_vars.append(var2)
            
            self.model.Add(sum(s1_vars) == 1)
            self.model.Add(sum(s2_vars) == 1)
        
        return True
        
    def add_separation_of_duty(self):
        """Add separation of duty constraints"""
        for s1, s2 in self.instance.SOD:
            for user in range(self.instance.number_of_users):
                if (s1 in self.var_manager.user_step_variables[user] and 
                    s2 in self.var_manager.user_step_variables[user]):
                    var1 = self.var_manager.user_step_variables[user][s1]
                    var2 = self.var_manager.user_step_variables[user][s2]
                    self.model.Add(var1 + var2 <= 1)
                    
    def add_at_most_k(self):
        """Add at-most-k constraints"""
        for k, steps in self.instance.at_most_k:
            for user in range(self.instance.number_of_users):
                user_step_vars = []
                for step in steps:
                    if step in self.var_manager.user_step_variables[user]:
                        user_step_vars.append(self.var_manager.user_step_variables[user][step])
                
                if user_step_vars:
                    self.model.Add(sum(user_step_vars) <= k)
        
        if self.instance.at_most_k:
            min_k = min(k for k, _ in self.instance.at_most_k)
            for user in range(self.instance.number_of_users):
                user_vars = []
                for step in range(self.instance.number_of_steps):
                    if step in self.var_manager.user_step_variables[user]:
                        user_vars.append(self.var_manager.user_step_variables[user][step])
                if user_vars:
                    self.model.Add(sum(user_vars) <= min_k)
                    
    def add_one_team(self):
        """Add one-team constraints"""
        for steps, teams in self.instance.one_team:
            team_vars = [self.model.NewBoolVar(f'team_{i}') for i in range(len(teams))]
            self.model.AddExactlyOne(team_vars)
            
            for step in steps:
                for team_idx, team in enumerate(teams):
                    team_var = team_vars[team_idx]
                    for user, var in self.var_manager.step_variables[step]:
                        if user not in team:
                            self.model.Add(var == 0).OnlyEnforceIf(team_var)


class SolutionVerifier:
    """Verifies and validates solutions to WSP instances"""
    def __init__(self, instance):
        self.instance = instance
        
    def verify_solution(self, solution_dict):
        """Verify all constraints and return violations"""
        violations = []
        violations.extend(self._verify_authorizations(solution_dict))
        violations.extend(self._verify_sod(solution_dict))
        violations.extend(self._verify_bod(solution_dict))
        violations.extend(self._verify_at_most_k(solution_dict))
        violations.extend(self._verify_one_team(solution_dict))
        return violations
        
    def _verify_authorizations(self, solution_dict):
        """Verify authorization constraints"""
        violations = []
        for step, user in solution_dict.items():
            if not self.instance.user_step_matrix[user-1][step-1]:
                violations.append(
                    f"Authorization Violation: User {user} not authorized for Step {step}"
                )
        return violations
        
    def _verify_sod(self, solution_dict):
        """Verify separation of duty constraints"""
        violations = []
        for s1, s2 in self.instance.SOD:
            s1, s2 = s1+1, s2+1  # Convert to 1-based indexing
            if solution_dict.get(s1) == solution_dict.get(s2):
                violations.append(
                    f"Separation of Duty Violation: Steps {s1} and {s2} "
                    f"both assigned to user {solution_dict[s1]}"
                )
        return violations
        
    def _verify_bod(self, solution_dict):
        """Verify binding of duty constraints"""
        violations = []
        for s1, s2 in self.instance.BOD:
            s1, s2 = s1+1, s2+1  # Convert to 1-based indexing
            if solution_dict.get(s1) != solution_dict.get(s2):
                violations.append(
                    f"Binding of Duty Violation: Step {s1} assigned to user "
                    f"{solution_dict.get(s1)} but step {s2} assigned to user "
                    f"{solution_dict.get(s2)}"
                )
        return violations
        
    def _verify_at_most_k(self, solution_dict):
        """Verify at-most-k constraints"""
        violations = []
        for k, steps in self.instance.at_most_k:
            user_counts = defaultdict(list)
            for step in steps:
                step_1based = step + 1
                if step_1based in solution_dict:
                    user = solution_dict[step_1based]
                    user_counts[user].append(step_1based)
            
            for user, assigned_steps in user_counts.items():
                if len(assigned_steps) > k:
                    violations.append(
                        f"At-most-{k} Violation: User {user} assigned to "
                        f"{len(assigned_steps)} steps {sorted(assigned_steps)} in "
                        f"constraint group {[s+1 for s in steps]}"
                    )
        return violations
        
    def _verify_one_team(self, solution_dict):
        """Verify one-team constraints"""
        violations = []
        for steps, teams in self.instance.one_team:
            steps_base1 = [s+1 for s in steps]
            assigned_users = set()
            
            for step in steps:
                step_1based = step + 1
                if step_1based in solution_dict:
                    assigned_users.add(solution_dict[step_1based] - 1)
            
            valid_team_found = False
            for team in teams:
                if all(user in team for user in assigned_users):
                    valid_team_found = True
                    break
            
            if not valid_team_found:
                violations.append(
                    f"One-team Violation: Assigned users {sorted(u+1 for u in assigned_users)} "
                    f"for steps {steps_base1} do not form a valid team"
                )
        return violations


class WspSolver:
    """Main solver class for WSP instances"""
    def __init__(self, instance):
        self.instance = instance
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self._setup_solver()
        
        # Initialize managers
        self.var_manager = VariableManager(self.model, instance)
        self.constraint_manager = None  # Will be initialized during solve
        self.solution_verifier = SolutionVerifier(instance)

    def _setup_solver(self):
        """Configure solver parameters for optimal performance"""
        self.solver.parameters.num_search_workers = 8
        self.solver.parameters.log_search_progress = False
        self.solver.parameters.cp_model_presolve = True
        self.solver.parameters.linearization_level = 2
        self.solver.parameters.optimize_with_core = True

    def solve(self):
        """Enhanced solving method with detailed analysis"""
        try:
            start_time = time.time()
            
            print("\nAnalyzing instance constraints...")
            self._print_constraint_analysis()
            
            # Pre-check for obvious conflicts
            conflicts = self.analyze_constraint_conflicts()
            if conflicts:
                print("\nPotential conflicts detected:")
                for conflict in conflicts:
                    print(f"  - {conflict}")
                
            print("\nBuilding and verifying constraints...")
            if not self._build_model():
                return self._handle_build_failure(start_time)

            print("\nSolving model...")
            status = self.solver.Solve(self.model)
            
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                return self._process_solution(start_time)
            else:
                return self._handle_infeasible(start_time, status)
                
        except Exception as e:
            return self._handle_error(start_time, e)

    def analyze_constraint_conflicts(self):
        """Analyze potential constraint conflicts"""
        conflicts = []
        
        # Check BOD-SOD conflicts
        for bod_s1, bod_s2 in self.instance.BOD:
            for sod_s1, sod_s2 in self.instance.SOD:
                if {bod_s1, bod_s2} & {sod_s1, sod_s2}:
                    conflicts.append(
                        f"Conflict: Steps {bod_s1+1},{bod_s2+1} must be same user (BOD) but "
                        f"steps {sod_s1+1},{sod_s2+1} must be different users (SOD)"
                    )

        # Check authorization sufficiency
        for step in range(self.instance.number_of_steps):
            authorized = sum(1 for u in range(self.instance.number_of_users)
                            if self.instance.user_step_matrix[u][step])
            if authorized == 0:
                conflicts.append(f"No user authorized for step {step+1}")
                
        # Check at-most-k feasibility
        for k, steps in self.instance.at_most_k:
            total_users = len(set(u for u in range(self.instance.number_of_users)
                                for s in steps if self.instance.user_step_matrix[u][s]))
            min_users_needed = len(steps) / k
            if total_users < min_users_needed:
                conflicts.append(
                    f"At-most-{k} constraint on steps {[s+1 for s in steps]} requires at least "
                    f"{min_users_needed:.0f} users but only {total_users} are authorized"
                )
        
        return conflicts

    def _handle_build_failure(self, start_time):
        """Handle model building failures with detailed explanation"""
        reason = "Model building failed due to:\n"
        
        # Check specific failure reasons
        if any(not common_users for s1, s2, common_users in self._get_bod_users()):
            reason += "  - Some BOD constraints cannot be satisfied (no user authorized for both steps)\n"
            
        if self._has_authorization_gaps():
            reason += "  - Some steps have no authorized users\n"
            
        if self._has_team_conflicts():
            reason += "  - One-team constraints conflict with other constraints\n"
            
        return SolverResult.create_unsat(time.time() - start_time, reason=reason)

    def _print_constraint_analysis(self):
        """Print detailed analysis of all constraints"""
        
        # Authorization analysis
        print("Authorization constraints:")
        total_auth = sum(sum(1 for x in row if x) for row in self.instance.user_step_matrix)
        print(f"Total authorizations: {total_auth}")
        
        # Per-step authorization analysis
        print("\nPer-step authorization breakdown:")
        for step in range(self.instance.number_of_steps):
            authorized_users = [u+1 for u in range(self.instance.number_of_users)
                              if self.instance.user_step_matrix[u][step]]
            print(f"  Step {step+1}: {len(authorized_users)} users authorized {authorized_users}")
            
        # Per-user authorization analysis
        print("\nPer-user authorization breakdown:")
        for user in range(self.instance.number_of_users):
            authorized_steps = [s+1 for s in range(self.instance.number_of_steps)
                              if self.instance.user_step_matrix[user][s]]
            if authorized_steps:  # Only show users with authorizations
                print(f"  User {user+1}: authorized for {len(authorized_steps)} steps {authorized_steps}")

        # BOD analysis
        if self.instance.BOD:
            print(f"\nBinding of Duty constraints ({len(self.instance.BOD)}):")
            for s1, s2 in self.instance.BOD:
                print(f"  Steps {s1+1} and {s2+1} must be performed by the same user")
                # Check if there are users authorized for both steps
                common_users = set()
                for user in range(self.instance.number_of_users):
                    if (self.instance.user_step_matrix[user][s1] and 
                        self.instance.user_step_matrix[user][s2]):
                        common_users.add(user + 1)
                if common_users:
                    print(f"    Users authorized for both steps: {sorted(common_users)}")
                else:
                    print(f"    WARNING: No users are authorized for both steps {s1+1} and {s2+1}")
                    print(f"    This makes the instance UNSAT as it's impossible to satisfy this BOD constraint")
        
        # SOD analysis
        if self.instance.SOD:
            print(f"\nSeparation of Duty constraints ({len(self.instance.SOD)}):")
            for s1, s2 in self.instance.SOD:
                print(f"  Steps {s1+1} and {s2+1} must be performed by different users")
        
        # At-most-k analysis
        if self.instance.at_most_k:
            print(f"\nAt-most-k constraints ({len(self.instance.at_most_k)}):")
            for k, steps in self.instance.at_most_k:
                print(f"  At most {k} steps from {[s+1 for s in steps]} can be assigned to same user")
        
        # One-team analysis
        if self.instance.one_team:
            print(f"\nOne-team constraints ({len(self.instance.one_team)}):")
            for steps, teams in self.instance.one_team:
                print(f"  Steps {[s+1 for s in steps]} must be assigned to one team:")
                for i, team in enumerate(teams, 1):
                    print(f"    Team {i}: Users {[u+1 for u in team]}")

    def _build_model(self):
        """Build model with detailed output"""
        try:
            print("Creating variables...")
            self.var_manager.create_variables()
            
            print("Adding authorization constraints...")
            self.constraint_manager = ConstraintManager(
                self.model,
                self.instance,
                self.var_manager
            )
            
            print("Adding constraints...")
            if not self.constraint_manager.add_all_constraints():
                print("\nModel building failed due to impossible constraints")
                return False
                
            return True
                
        except Exception as e:
            print(f"Error building model: {str(e)}")
            return False

    def _process_solution(self, start_time):
        """Process feasible solution with detailed output"""
        solution_dict = {}
        for step in range(self.instance.number_of_steps):
            for user, var in self.var_manager.step_variables[step]:
                if self.solver.Value(var):
                    solution_dict[step + 1] = user + 1
                    break

        print("\nSolution found. Verifying constraints...")
        result = SolverResult.create_sat(
            time.time() - start_time,
            solution_dict
        )
        
        # Print assignments
        print("\nAssignment Summary:")
        user_assignments = defaultdict(list)
        for step, user in solution_dict.items():
            user_assignments[user].append(step)
        
        for user in sorted(user_assignments.keys()):
            print(f"User {user} assigned to step{'s' if len(user_assignments[user]) > 1 else ''}: "
                f"{sorted(user_assignments[user])}")
        print(f"\nTotal unique users used: {len(user_assignments)}")

        # Verify and print violations
        violations = self.solution_verifier.verify_solution(solution_dict)
        result.violations = violations
        
        if violations:
            print("\nConstraint Violations Found:")
            for violation in violations:
                print(violation)
        else:
            print("\nALL CONSTRAINTS SATISFIED!")
            print("SOLUTION VERIFIED WITH NO VIOLAIONS!")
        
        return result
    
    def _analyze_infeasibility_cause(self):
        """Detailed analysis of infeasibility causes"""
        causes = []
        
        # Check authorization gaps (steps with no authorized users)
        for step in range(self.instance.number_of_steps):
            authorized_users = [u+1 for u in range(self.instance.number_of_users)
                              if self.instance.user_step_matrix[u][step]]
            if not authorized_users:
                causes.append(
                    f"Step {step+1} cannot be assigned: No users are authorized for this step"
                )

        # Check minimum required users vs available users for steps
        required_users = set()
        for s1, s2 in self.instance.SOD:
            s1_users = {u+1 for u in range(self.instance.number_of_users)
                       if self.instance.user_step_matrix[u][s1]}
            s2_users = {u+1 for u in range(self.instance.number_of_users)
                       if self.instance.user_step_matrix[u][s2]}
            
            # If both steps have only one authorized user and it's the same user
            if len(s1_users) == 1 and len(s2_users) == 1 and s1_users == s2_users:
                causes.append(
                    f"Steps {s1+1} and {s2+1} must be different users (SOD) but only user "
                    f"{list(s1_users)[0]} is authorized for both"
                )

        # Check BOD constraints
        for s1, s2 in self.instance.BOD:
            s1_users = {u+1 for u in range(self.instance.number_of_users)
                       if self.instance.user_step_matrix[u][s1]}
            s2_users = {u+1 for u in range(self.instance.number_of_users)
                       if self.instance.user_step_matrix[u][s2]}
            common_users = s1_users & s2_users
            if not common_users:
                causes.append(
                    f"Steps {s1+1} and {s2+1} must be same user (BOD) but no user is "
                    f"authorized for both steps. Step {s1+1} users: {sorted(s1_users)}, "
                    f"Step {s2+1} users: {sorted(s2_users)}"
                )

        # Check at-most-k feasibility with detailed analysis
        for k, steps in self.instance.at_most_k:
            step_details = []
            for step in steps:
                users = {u+1 for u in range(self.instance.number_of_users)
                        if self.instance.user_step_matrix[u][step]}
                step_details.append((step+1, users))
            
            total_users = set().union(*(users for _, users in step_details))
            if len(total_users) * k < len(steps):
                cause = f"At-most-{k} constraint cannot be satisfied for steps {[s for s, _ in step_details]}:\n"
                for step, users in step_details:
                    cause += f"    Step {step}: {len(users)} users {sorted(users)}\n"
                cause += f"    Need at least {len(steps)/k:.1f} users but only have {len(total_users)}"
                causes.append(cause)

        return causes

    def _handle_infeasible(self, start_time, status):
        """Enhanced infeasibility handling"""
        if status == cp_model.INFEASIBLE:
            causes = self._analyze_infeasibility_cause()
            reason = "The problem is infeasible for the following specific reasons:\n\n"
            
            if causes:
                for i, cause in enumerate(causes, 1):
                    reason += f"{i}. {cause}\n"
            else:
                # Analyze the constraint structure
                reason += self._analyze_constraint_structure()
            
            if self.instance.SOD:
                reason += "\nNote: Problem has Separation of Duty constraints that might create additional conflicts."
            if self.instance.at_most_k:
                reason += "\nNote: Problem has At-most-k constraints that limit user assignments."
                
        else:
            reason = self._handle_other_status(status)
            
        return SolverResult.create_unsat(time.time() - start_time, reason=reason)

    def _analyze_constraint_structure(self):
        """Analyze constraint structure for potential conflicts"""
        analysis = "Analysis of constraint structure:\n"
        
        # Analyze step requirements
        for step in range(self.instance.number_of_steps):
            authorized = [u+1 for u in range(self.instance.number_of_users)
                        if self.instance.user_step_matrix[u][step]]
            sod_constraints = [s2+1 for s1, s2 in self.instance.SOD if s1 == step]
            sod_constraints.extend([s1+1 for s1, s2 in self.instance.SOD if s2 == step])
            
            if sod_constraints:
                analysis += f"\nStep {step+1}:\n"
                analysis += f"  - Has {len(authorized)} authorized users: {authorized}\n"
                analysis += f"  - Must be different from steps: {sod_constraints}\n"
                
                # Check if enough users for SOD constraints
                if len(authorized) <= len(sod_constraints):
                    analysis += f"  - POTENTIAL ISSUE: May not have enough users for SOD constraints\n"
        
        return analysis

    def _get_bod_users(self):
        """Get common users for each BOD constraint"""
        bod_info = []
        for s1, s2 in self.instance.BOD:
            common_users = set()
            for user in range(self.instance.number_of_users):
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2]):
                    common_users.add(user)
            bod_info.append((s1, s2, common_users))
        return bod_info

    def _has_authorization_gaps(self):
        """Check if any steps have no authorized users"""
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                return True
        return False

    def _has_team_conflicts(self):
        """Check for conflicts between team constraints and other constraints"""
        if not self.instance.one_team:
            return False
            
        for steps, teams in self.instance.one_team:
            # Check if team steps have BOD constraints with non-team steps
            for s1 in steps:
                for bod_s1, bod_s2 in self.instance.BOD:
                    if s1 == bod_s1 and bod_s2 not in steps:
                        return True
                    if s1 == bod_s2 and bod_s1 not in steps:
                        return True
        return False

    def _handle_error(self, start_time, error):
        """Handle exceptions with detailed error messages"""
        error_msg = f"Error during solving: {str(error)}\n"
        error_msg += "Details:\n"
        
        if isinstance(error, AttributeError):
            error_msg += "  - Internal solver error: Missing attribute\n"
        elif isinstance(error, ValueError):
            error_msg += "  - Invalid value or parameter\n"
        else:
            error_msg += f"  - Unexpected error of type {type(error).__name__}\n"
            
        return SolverResult.create_unsat(
            time.time() - start_time,
            reason=error_msg
        )
    

def solve_instance(filename, results):
    """Solve a single WSP instance"""
    print("\n" + "=" * 100)
    print(f"\nSolving instance: {filename}")
    
    try:
        # Parse instance
        instance = InstanceParser.parse_file(filename)
        
        # Create and run solver
        solver = WspSolver(instance)
        result = solver.solve()
        
        # Add metadata
        metadata = INSTANCE_METADATA.get(filename.split('/')[-1], {})
        metrics = result.get_metrics()
        metrics.update({
            'filename': filename,
            'expected_sat': metadata.get('sat', 'Unknown'),
            'unique_solution': metadata.get('unique', 'Unknown')
        })
        
        results.append(metrics)
        
        # Print results
        if result.is_sat:
            print(f"\nStatus: SAT (Expected: {metadata.get('sat', 'Unknown')})")
            print(f"Execution Time: {metrics['exe_time']}")
            print("Solution:")
            for step, user in sorted(result.assignment.items()):
                print(f"Step {step}: User {user}")
        else:
            print(f"\nStatus: UNSAT (Expected: {metadata.get('sat', 'Unknown')})")
            print(f"Execution Time: {metrics['exe_time']}")
            if result.reason:
                print(f"Reason: {result.reason}")
        
        return metrics
        
    except Exception as e:
        print(f"\nError processing {filename}:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        
        error_result = {
            'filename': filename,
            'sat': 'error',
            'exe_time': '0ms',
            'sol': [],
            'expected_sat': INSTANCE_METADATA.get(
                filename.split('/')[-1], {}
            ).get('sat', 'Unknown'),
            'unique_solution': INSTANCE_METADATA.get(
                filename.split('/')[-1], {}
            ).get('unique', 'Unknown')
        }
        results.append(error_result)
        return error_result


if __name__ == "__main__":
    results = []
    
    # Process all instance files
    instance_folder = "assets/instances/"
    instance_files = sorted(
        [f for f in os.listdir(instance_folder) 
         if f.startswith('example') and f.endswith('.txt')],
        key=lambda x: int(''.join(filter(str.isdigit, x)))
    )
    
    for filename in instance_files:
        full_path = os.path.join(instance_folder, filename)
        solve_instance(full_path, results)
    
    # Print summary
    print("\nResults Summary:")
    print("{:<15} {:<10} {:<15} {:<15} {:<15}".format(
        "Instance", "Status", "Expected SAT", "Unique Sol", "Exec Time"))
    print("-" * 70)
    
    for result in results:
        print("{:<15} {:<10} {:<15} {:<15} {:<15}".format(
            result['filename'].split('/')[-1], 
            result['sat'], 
            str(result['expected_sat']), 
            str(result['unique_solution']), 
            result['exe_time']))
