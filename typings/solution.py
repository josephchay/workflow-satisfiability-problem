import time
from ortools.sat.python import cp_model
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
            assignment={},  # Empty dict
            violations=[],  # Empty list
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
            f.write(f"Wall Clock Time: {self.solve_time:.4f} seconds\n")

            solver_type = 'Unknown'
            if solver_instance:
                solver_type = getattr(solver_instance, 'SOLVER_TYPE', 'Unknown').value

            f.write(f"Solver: {solver_type}\n")
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
                    f.write("\n" + "=" * 40 + "\n")
                    f.write("DETAILED UNSAT REASONING ANALYSIS\n")
                    f.write("=" * 40 + "\n")
                    f.write(f"\t{self.reason}\n")

            # Detailed Constraint Information
            if solver_instance:
                f.write("\n" + "=" * 40 + "\n")
                f.write("CONSTRAINT DETAILS\n")
                f.write("=" * 40 + "\n")

                # 1. Authorization Constraints
                f.write("\nAuthorization Constraints:\n")
                total_auth_count = sum(sum(1 for x in row if x) for row in solver_instance.instance.user_step_matrix)
                f.write(f"\tTotal Authorizations: {total_auth_count}\n\n")
                f.write(f"\tPer-Step Authorization Breakdown ({solver_instance.instance.number_of_steps} steps):\n")
                for step in range(solver_instance.instance.number_of_steps):
                    authorized_users = [u+1 for u in range(solver_instance.instance.number_of_users)
                                    if solver_instance.instance.user_step_matrix[u][step]]
                    f.write(f"\t\tStep {step+1}: {len(authorized_users)} users authorized {authorized_users}\n")

                f.write(f"\n\tPer-User Authorization Breakdown ({solver_instance.instance.number_of_users} users):\n")
                for user in range(solver_instance.instance.number_of_users):
                    authorized_steps = [s+1 for s in range(solver_instance.instance.number_of_steps)
                                    if solver_instance.instance.user_step_matrix[user][s]]
                    
                    if authorized_steps:  # Only include users with authorizations
                        f.write(f"\t\tUser {user+1}: authorized for {len(authorized_steps)} steps {authorized_steps}\n")

                # 2. Separation of Duty Constraints
                f.write(f"\nSeparation of Duty Constraints ({len(solver_instance.instance.SOD)}):\n")
                if solver_instance.instance.SOD:
                    for s1, s2 in solver_instance.instance.SOD:
                        f.write(f"\tSteps {s1+1} and {s2+1} must be performed by different users\n")
                else:
                    f.write("\tNo Separation of Duty constraints defined.\n")

                # 3. Binding of Duty Constraints
                f.write(f"\nBinding of Duty Constraints ({len(solver_instance.instance.BOD)}):\n")
                if solver_instance.instance.BOD:
                    for s1, s2 in solver_instance.instance.BOD:
                        common_users = [u+1 for u in range(solver_instance.instance.number_of_users)
                                    if (solver_instance.instance.user_step_matrix[u][s1] and 
                                        solver_instance.instance.user_step_matrix[u][s2])]
                        
                        f.write(f"\tSteps {s1+1} and {s2+1} must be performed by the same user\n")
                        
                        if common_users:
                            f.write(f"\t\tUsers authorized for both steps: {common_users}\n")
                        else:
                            f.write(f"\t\tConstraint Feasibility Issue: No users are authorized for both steps {s1+1} and {s2+1}\n")
                            f.write(f"\t\tThis makes the instance UNSAT as it's impossible to satisfy this Binding of Duty constraint\n")
                else:
                    f.write("\tNo Binding of Duty constraints defined.\n")

                # 4. At-most-k Constraints
                f.write(f"\nAt-most-k Constraints ({len(solver_instance.instance.at_most_k)}):\n")
                if solver_instance.instance.at_most_k:
                    for k, steps in solver_instance.instance.at_most_k:
                        f.write(f"\tAt most {k} steps from {[s+1 for s in steps]} can be assigned to same user\n")
                else:
                    f.write("\tNo At-most-k constraints defined.\n")

                # 5. One-team Constraints
                f.write(f"\nOne-team Constraints ({len(solver_instance.instance.one_team)}):\n")
                if hasattr(solver_instance.instance, 'one_team') and solver_instance.instance.one_team:
                    for steps, teams in solver_instance.instance.one_team:
                        f.write(f"\tSteps {[s+1 for s in steps]}: Team groups {[[u+1 for u in team] for team in teams]}\n")
                else:
                    f.write("\tNo One-team constraints defined.\n")

                # 6. Super User At Least (SUAL) Constraints
                f.write(f"\nSuper User At Least (SUAL) Constraints ({len(solver_instance.instance.sual)}):\n")
                if hasattr(solver_instance.instance, 'sual') and solver_instance.instance.sual:
                    for scope, h, super_users in solver_instance.instance.sual:
                        f.write(f"\tScope: Steps {[s+1 for s in scope]}\n")
                        f.write(f"\tMax Authorized Users (h): {h}\n")
                        f.write(f"\tSuper Users: {[u+1 for u in super_users]}\n")
                        
                        # Analyze SUAL constraint satisfaction
                        step_details = []
                        for step in scope:
                            # Get authorized users for the step
                            auth_users = [u+1 for u in solver_instance.var_manager.get_authorized_users(step)]
                            # Get super users authorized for the step
                            authorized_super_users = [u+1 for u in (solver_instance.var_manager.get_authorized_users(step) & set(super_users))]
                            
                            step_details.append({
                                'step': step + 1,
                                'authorized_users': auth_users,
                                'authorized_super_users': authorized_super_users
                            })
                        
                        # Print step details
                        for detail in step_details:
                            f.write(f"\t\tStep {detail['step']}: Authorized Users {detail['authorized_users']}, "
                                    f"Authorized Super Users {detail['authorized_super_users']}\n")
                else:
                    f.write("\tNo SUAL constraints defined.\n")

                # 7. Wang-Li Constraints
                f.write(f"\nWang-Li Constraints ({len(solver_instance.instance.wang_li)}):\n")
                if hasattr(solver_instance.instance, 'wang_li') and solver_instance.instance.wang_li:
                    for scope, departments in solver_instance.instance.wang_li:
                        f.write(f"\tScope: Steps {[s+1 for s in scope]}\n")
                        
                        # Analyze departments and their users
                        dept_details = []
                        for dept_idx, department in enumerate(departments, 1):
                            dept_users = [u+1 for u in department]
                            
                            # Check authorization for each step
                            dept_step_auth = {}
                            for step in scope:
                                auth_users = [u+1 for u in (solver_instance.var_manager.get_authorized_users(step) & set(department))]
                                dept_step_auth[step + 1] = auth_users
                            
                            dept_details.append({
                                'dept': dept_idx,
                                'users': dept_users,
                                'step_authorizations': dept_step_auth
                            })
                        
                        # Print department details
                        for detail in dept_details:
                            f.write(f"\t\tDepartment {detail['dept']}: Users {detail['users']}\n")
                            f.write("\t\t\tStep Authorizations:\n")
                            for step, auth_users in detail['step_authorizations'].items():
                                f.write(f"\t\t\t\tStep {step}: {auth_users}\n")
                else:
                    f.write("\tNo Wang-Li constraints defined.\n")

                # 8. Assignment-Dependent (ADA) Constraints
                f.write(f"\nAssignment-Dependent (ADA) Constraints ({len(solver_instance.instance.ada)}):\n")
                if hasattr(solver_instance.instance, 'ada') and solver_instance.instance.ada:
                    for s1, s2, source_users, target_users in solver_instance.instance.ada:
                        f.write(f"\tSource Step {s1+1} -> Target Step {s2+1}\n")
                        f.write(f"\t\tSource Users: {[u+1 for u in source_users]}\n")
                        f.write(f"\t\tTarget Users: {[u+1 for u in target_users]}\n")
                        
                        # Analyze source and target step authorizations
                        source_auth = [u+1 for u in (solver_instance.var_manager.get_authorized_users(s1) & set(source_users))]
                        target_auth = [u+1 for u in (solver_instance.var_manager.get_authorized_users(s2) & set(target_users))]
                        
                        f.write(f"\t\tAuthorized Source Users: {source_auth}\n")
                        f.write(f"\t\tAuthorized Target Users: {target_auth}\n")
                else:
                    f.write("\tNo Assignment-Dependent constraints defined.\n")

                # Constraint Conflicts
                f.write("\n" + "=" * 40 + "\n")
                f.write("CONSTRAINT CONFLICT ANALYSIS\n")
                f.write("=" * 40 + "\n")
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


class UniquenessChecker(cp_model.CpSolverSolutionCallback):
    """Solution callback that checks if solution is unique"""
    def __init__(self, var_manager):
        super().__init__()
        self.var_manager = var_manager
        self.solutions_found = 0
        
    def on_solution_callback(self):
        """Called on each solution found"""
        try:
            # For debugging
            self.solutions_found += 1
            
            # Stop after finding second solution
            if self.solutions_found >= 2:
                self.StopSearch()
        except Exception as e:
            print(f"Error in uniqueness callback: {str(e)}")
            raise  # Re-raise to see full traceback


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
