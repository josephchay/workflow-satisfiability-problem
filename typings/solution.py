from collections import defaultdict


class Solution:
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
        return Solution(
            is_sat=False,
            solve_time=solve_time,
            reason=reason
        )
    
    @staticmethod
    def create_sat(solve_time, assignment):
        """Create a SAT result"""
        return Solution(
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

    def save(self, output_file, solver_instance=None):
        """Save solution to a file with comprehensive information"""
        with open(output_file, 'w') as f:
            # Solution Status and Basic Information
            f.write(f"Solution Status: {'SAT' if self.is_sat else 'UNSAT'}\n")
            f.write(f"Solve Time: {self.solve_time:.4f} seconds\n")
            f.write(f"Solver: {getattr(self, 'solver_type', 'Unknown')}\n")
            f.write("=" * 120 + "\n\n")

            # If solution is satisfiable
            if self.is_sat:
                # Step Assignments
                f.write("Step Assignments:\n")
                for step, user in sorted(self.assignment.items()):
                    f.write(f"\tStep {step}: User {user}\n")
                
                # User Distribution
                user_steps = {}
                for step, user in self.assignment.items():
                    if user not in user_steps:
                        user_steps[user] = []
                    user_steps[user].append(step)
                
                f.write("\nUser Step Distribution:\n")
                for user, steps in sorted(user_steps.items()):
                    f.write(f"\tUser {user}: Steps {sorted(steps)}\n")
                
                # Total users used
                unique_users = len(user_steps)
                f.write(f"\nTotal Unique Users Used: {unique_users}\n")

            # If solution is unsatisfiable
            else:
                f.write("UNSATISFIABLE SOLUTION\n")
                if self.reason:
                    f.write("\nReason for Unsatisfiability:\n")
                    f.write(f"\t{self.reason}\n")

            # Detailed Constraint Information
            if solver_instance:
                f.write("\n" + "=" * 50 + "\n")
                f.write("CONSTRAINT DETAILS\n")
                f.write("=" * 50 + "\n")

                # Authorization Constraints
                f.write("\nAuthorization Constraints:\n")
                total_auth_count = sum(sum(1 for x in row if x) for row in solver_instance.instance.user_step_matrix)
                f.write(f"\tTotal Authorizations: {total_auth_count}\n\n")
                f.write("\tPer-Step Authorization Breakdown:\n")
                for step in range(solver_instance.instance.number_of_steps):
                    authorized_users = [u+1 for u in range(solver_instance.instance.number_of_users)
                                    if solver_instance.instance.user_step_matrix[u][step]]
                    f.write(f"\t\tStep {step+1}: {len(authorized_users)} users authorized {authorized_users}\n")

                f.write("\n\tPer-User Authorization Breakdown:\n")
                for user in range(solver_instance.instance.number_of_users):
                    authorized_steps = [s+1 for s in range(solver_instance.instance.number_of_steps)
                                    if solver_instance.instance.user_step_matrix[user][s]]
                    
                    if authorized_steps:  # Only include users with authorizations
                        f.write(f"\t\tUser {user+1}: authorized for {len(authorized_steps)} steps {authorized_steps}\n")

                # Separation of Duty Constraints
                f.write("\nSeparation of Duty Constraints:\n")
                if solver_instance.instance.SOD:
                    for s1, s2 in solver_instance.instance.SOD:
                        f.write(f"\tSteps {s1+1} and {s2+1} must be performed by different users\n")
                else:
                    f.write("\tNo Separation of Duty constraints defined.\n")

                # Binding of Duty Constraints
                f.write("\nBinding of Duty Constraints:\n")
                if solver_instance.instance.BOD:
                    for s1, s2 in solver_instance.instance.BOD:
                        common_users = [u+1 for u in range(solver_instance.instance.number_of_users)
                                    if (solver_instance.instance.user_step_matrix[u][s1] and 
                                        solver_instance.instance.user_step_matrix[u][s2])]
                        f.write(f"\tSteps {s1+1} and {s2+1} must be performed by same users: {common_users}\n")
                else:
                    f.write("\tNo Binding of Duty constraints defined.\n")

                # At-most-k Constraints
                f.write("\nAt-most-k Constraints:\n")
                if solver_instance.instance.at_most_k:
                    for k, steps in solver_instance.instance.at_most_k:
                        f.write(f"\tAt most {k} steps from {[s+1 for s in steps]} can be assigned to same user\n")
                else:
                    f.write("\tNo At-most-k constraints defined.\n")

                # One-team Constraints
                f.write("\nOne-team Constraints:\n")
                if hasattr(solver_instance.instance, 'one_team') and solver_instance.instance.one_team:
                    for steps, teams in solver_instance.instance.one_team:
                        f.write(f"\tSteps {[s+1 for s in steps]}: Team groups {[[u+1 for u in team] for team in teams]}\n")
                else:
                    f.write("\tNo One-team constraints defined.\n")

                # Constraint Conflicts
                f.write("\n" + "=" * 50 + "\n")
                f.write("CONSTRAINT CONFLICT ANALYSIS\n")
                f.write("=" * 50 + "\n")
                conflicts = solver_instance.analyze_constraint_conflicts()
                if conflicts:
                    f.write("Potential Conflicts Detected:\n")
                    for conflict in conflicts:
                        f.write(f"\t- {conflict['Type']}: {conflict['Description']}\n")
                else:
                    f.write("\tNo constraint conflicts detected.\n")

                # Violations (if any)
                if self.violations:
                    f.write("\n" + "=" * 50 + "\n")
                    f.write("CONSTRAINT VIOLATIONS\n")
                    f.write("=" * 50 + "\n")
                    for violation in self.violations:
                        f.write(f"\t- {violation}\n")


class Verifier:
    """Verifies and validates solutions to WSP instances"""
    def __init__(self, instance):
        self.instance = instance
        
    def verify(self, solution_dict):
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
