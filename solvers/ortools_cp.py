from ortools.sat.python import cp_model
import time

from typings import VariableManager, ConstraintManager, Solution, Verifier


class ORToolsCPSolver:
    """Main solver class for WSP instances"""
    def __init__(self, instance):
        self.instance = instance
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self._setup_solver()
        
        # Initialize managers
        self.var_manager = VariableManager(self.model, instance)
        self.constraint_manager = None  # Will be initialized during solve
        self.solution_verifier = Verifier(instance)

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
            
        return Solution.create_unsat(time.time() - start_time, reason=reason)

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
        result = Solution.create_sat(
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
        violations = self.solution_verifier.verify(solution_dict)
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
            
        return Solution.create_unsat(time.time() - start_time, reason=reason)

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
            
        return Solution.create_unsat(
            time.time() - start_time,
            reason=error_msg
        )
