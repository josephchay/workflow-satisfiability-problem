from collections import defaultdict
from typing import Dict
from ortools.sat.python import cp_model
import time

from solvers import BaseSolver
from typings import VariableManager, ConstraintManager, Solution, Verifier


class ORToolsCPSolver(BaseSolver):
    """Main solver class for WSP instances"""
    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        self.instance = instance
        self.active_constraints = active_constraints
        self.gui_mode = gui_mode
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.solve_time = 0
        self._setup_solver()
        
        # Initialize managers
        self.var_manager = VariableManager(self.model, instance)
        self.constraint_manager = None
        self.solution_verifier = Verifier(instance)
        
        # Initialize statistics storage
        self.statistics = {
            "solution_status": {},
            "problem_size": {},
            "workload_distribution": {},
            "constraint_compliance": {},
            "constraint_distribution": {},
            "detailed_analysis": {}
        }

    def _setup_solver(self):
        """Configure solver parameters"""
        self.solver.parameters.num_search_workers = 8
        self.solver.parameters.log_search_progress = False
        self.solver.parameters.cp_model_presolve = True
        self.solver.parameters.linearization_level = 2
        self.solver.parameters.optimize_with_core = True

    def solve(self):
        """Main solving method"""
        try:
            start_time = time.time()
            self.solve_time = 0
            
            print("DEBUG 1: Starting solve method")
            conflicts = self.analyze_constraint_conflicts()
            
            print("DEBUG 2: Building model")
            if not self._build_model():
                print("DEBUG 3: Model build failed")
                result = self._handle_build_failure(start_time)
                print("DEBUG 3.1: Build failure result:", result.__dict__)
                self._update_statistics(result)
                print("DEBUG 3.2: Statistics after build failure:", self.statistics)
                return result

            print("DEBUG 4: Solving model")
            status = self.solver.Solve(self.model)
            self.solve_time = time.time() - start_time
            
            print("DEBUG 5: Solver status:", status)
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                print("DEBUG 6: Found solution")
                result = self._process_solution(start_time)
                print("DEBUG 7: Processed solution:", result.__dict__)
                self._update_statistics(result)
                print("DEBUG 8: Updated statistics:", self.statistics)
                return result
            else:
                print("DEBUG 9: Infeasible")
                result = self._handle_infeasible(start_time, status)
                print("DEBUG 10: Handled infeasible:", result.__dict__)
                self._update_statistics(result)
                print("DEBUG 11: Updated statistics:", self.statistics)
                return result
                
        except Exception as e:
            print("DEBUG 12: Exception occurred:", str(e))
            result = self._handle_error(start_time, e)
            self._update_statistics(result)  # Make sure to update stats even for errors
            return result

    def _update_statistics(self, result):
        """Update comprehensive statistics"""
        # Initialize all dictionaries first
        self.statistics = {
            "solution_status": {},
            "problem_size": {},
            "workload_distribution": {},
            "constraint_compliance": {},
            "constraint_distribution": {},
            "detailed_analysis": {}
        }

        # Solution Status section
        self.statistics["solution_status"] = {
            "Status": "SAT" if result.is_sat else "UNSAT",
            "Solver Used": "OR-Tools (CP)",
            "Solution Time": f"{self.solve_time:.2f} seconds"
        }

        if not result.is_sat and result.reason:
            self.statistics["solution_status"]["UNSAT Reason"] = result.reason

        # Problem Size section (always include)
        total_auth = sum(sum(1 for x in row if x) for row in self.instance.user_step_matrix)
        auth_density = (total_auth / (self.instance.number_of_steps * self.instance.number_of_users)) * 100
        constraint_density = (self.instance.number_of_constraints / 
                            (self.instance.number_of_steps * self.instance.number_of_users)) * 100
        
        self.statistics["problem_size"] = {
            "Total Steps": self.instance.number_of_steps,
            "Total Users": self.instance.number_of_users,
            "Total Constraints": self.instance.number_of_constraints,
            "Authorization Density": f"{auth_density:.2f}%",
            "Constraint Density": f"{constraint_density:.2f}%",
            "Step-User Ratio": f"{self.instance.number_of_steps / self.instance.number_of_users:.2f}"
        }

        # Workload Distribution
        self.statistics["workload_distribution"] = {
            "Active Users": "N/A",
            "Maximum Assignment": "N/A",
            "Minimum Assignment": "N/A",
            "Average Assignment": "N/A",
            "User Utilization": "N/A"
        }
        
        if result.is_sat and hasattr(result, 'assignment'):
            user_assignments = defaultdict(list)
            for step, user in result.assignment.items():
                user_assignments[user].append(step)

            active_users = len(user_assignments)
            if active_users > 0:
                max_steps = max(len(steps) for steps in user_assignments.values())
                min_steps = min(len(steps) for steps in user_assignments.values())
                avg_steps = sum(len(steps) for steps in user_assignments.values()) / active_users
                
                self.statistics["workload_distribution"].update({
                    "Active Users": f"{active_users} of {self.instance.number_of_users}",
                    "Maximum Assignment": f"{max_steps} steps",
                    "Minimum Assignment": f"{min_steps} steps",
                    "Average Assignment": f"{avg_steps:.1f} steps",
                    "User Utilization": f"{(active_users / self.instance.number_of_users) * 100:.1f}%"
                })

        # Constraint Compliance
        self.statistics["constraint_compliance"] = {
            "Solution Quality": "No solution exists (UNSAT)" if not result.is_sat else (
                "Perfect Solution - All Constraints Satisfied" if not result.violations else 
                "Solution has violations"
            ),
            "Authorization Violations": "N/A" if not result.is_sat else len([v for v in result.violations if "Authorization" in v]),
            "Separation Of Duty Violations": "N/A" if not result.is_sat else len([v for v in result.violations if "Separation of Duty" in v]),
            "Binding Of Duty Violations": "N/A" if not result.is_sat else len([v for v in result.violations if "Binding of Duty" in v]),
            "At Most K Violations": "N/A" if not result.is_sat else len([v for v in result.violations if "At-most-" in v]),
            "One Team Violations": "N/A" if not result.is_sat else len([v for v in result.violations if "One-team" in v])
        }

        # Constraint Distribution (always include)
        self.statistics["constraint_distribution"] = {
            "Authorization": sum(1 for user in self.instance.auth if user),
            "Separation Of Duty": len(self.instance.SOD),
            "Binding Of Duty": len(self.instance.BOD),
            "At Most K": len(self.instance.at_most_k),
            "One Team": len(self.instance.one_team)
        }

        # Add detailed analysis in all cases
        if self.gui_mode:
            self._add_detailed_analysis()

            # Add UNSAT specific analysis
            if not result.is_sat:
                if "Conflict Analysis" not in self.statistics["detailed_analysis"]:
                    self.statistics["detailed_analysis"]["Conflict Analysis"] = {
                        "Detected Conflicts": [],
                        "Description": "Analysis of why the problem is unsatisfiable"
                    }
                
                if result.reason:
                    self.statistics["detailed_analysis"]["Conflict Analysis"]["Detected Conflicts"].append({
                        "Type": "UNSAT Reason",
                        "Description": result.reason
                    })
                    self.statistics["solution_status"]["UNSAT Analysis"] = result.reason

    def _add_detailed_analysis(self):
        """Add detailed analysis to statistics"""
        detailed = {}
        
        # Authorization Analysis
        auth_analysis = {
            "Per Step Breakdown": {},
            "Per User Breakdown": {},
            "Summary": {}
        }
        
        # Per-step breakdown
        for step in range(self.instance.number_of_steps):
            authorized_users = [u+1 for u in range(self.instance.number_of_users)
                              if self.instance.user_step_matrix[u][step]]
            auth_analysis["Per Step Breakdown"][f"Step {step+1}"] = {
                "Authorized Users": sorted(authorized_users),
                "Total": len(authorized_users)
            }
            
        # Per-user breakdown
        for user in range(self.instance.number_of_users):
            authorized_steps = [s+1 for s in range(self.instance.number_of_steps)
                              if self.instance.user_step_matrix[user][s]]
            if authorized_steps:  # Only include users with authorizations
                auth_analysis["Per User Breakdown"][f"User {user+1}"] = {
                    "Authorized Steps": sorted(authorized_steps),
                    "Total": len(authorized_steps)
                }
        
        detailed["Authorization Analysis"] = auth_analysis

        # Constraint Analysis
        constraint_analysis = {
            "Separation of Duty": [],
            "Binding of Duty": [],
            "At Most K": [],
            "One Team": []
        }

        # SOD constraints
        for s1, s2 in self.instance.SOD:
            constraint_analysis["Separation of Duty"].append({
                "Steps": f"{s1+1} and {s2+1}",
                "Description": f"Steps {s1+1} and {s2+1} must be performed by different users"
            })

        # BOD constraints
        for s1, s2 in self.instance.BOD:
            common_users = [u+1 for u in range(self.instance.number_of_users)
                          if (self.instance.user_step_matrix[u][s1] and 
                              self.instance.user_step_matrix[u][s2])]
            constraint_analysis["Binding of Duty"].append({
                "Steps": f"{s1+1} and {s2+1}",
                "Common Users": sorted(common_users),
                "Description": f"Steps {s1+1} and {s2+1} must be performed by the same user"
            })

        # At-most-k constraints
        for k, steps in self.instance.at_most_k:
            constraint_analysis["At Most K"].append({
                "K Value": k,
                "Steps": [s+1 for s in steps],
                "Description": f"At most {k} steps from {[s+1 for s in steps]} can be assigned to same user"
            })

        # One-team constraints
        if hasattr(self.instance, 'one_team'):
            for steps, teams in self.instance.one_team:
                constraint_analysis["One Team"].append({
                    "Steps": [s+1 for s in steps],
                    "Teams": [[u+1 for u in team] for team in teams]
                })

        detailed["Constraint Analysis"] = constraint_analysis

        # Add conflict analysis if there are any conflicts
        conflicts = self.analyze_constraint_conflicts()

        # Only add Conflict Analysis if it's not already shown in UNSAT analysis
        if conflicts and "reason" not in self.statistics["solution_status"]: 
            detailed["Conflict Analysis"] = {
                "Detected Conflicts": conflicts,
                "Description": "Potential conflicts detected in constraint specifications"
            }

        self.statistics["detailed_analysis"] = detailed

    def analyze_constraint_conflicts(self):
        """Analyze potential constraint conflicts"""
        conflicts = []
        
        # First add BOD authorization gaps as conflicts
        if self.active_constraints.get('binding_of_duty', True):
            for s1, s2 in self.instance.BOD:
                common_users = set()
                for user in range(self.instance.number_of_users):
                    if (self.instance.user_step_matrix[user][s1] and 
                        self.instance.user_step_matrix[user][s2]):
                        common_users.add(user)
                if not common_users:
                    conflicts.append({
                        "Type": "BOD Authorization Gap",
                        "Description": f"No users authorized for both steps {s1+1} and {s2+1} in BOD constraint"
                    })

        # Only check active constraints
        if self.active_constraints.get('binding_of_duty', True) and \
           self.active_constraints.get('separation_of_duty', True):
            # Check BOD-SOD conflicts
            for bod_s1, bod_s2 in self.instance.BOD:
                for sod_s1, sod_s2 in self.instance.SOD:
                    if {bod_s1, bod_s2} & {sod_s1, sod_s2}:
                        conflicts.append({
                            "Type": "BOD-SOD Conflict",
                            "Description": f"Steps {bod_s1+1},{bod_s2+1} must be same user (BOD) but "
                                         f"steps {sod_s1+1},{sod_s2+1} must be different users (SOD)"
                        })
        
        # Check authorization if active
        if self.active_constraints.get('authorizations', True):
            for step in range(self.instance.number_of_steps):
                authorized = sum(1 for u in range(self.instance.number_of_users)
                              if self.instance.user_step_matrix[u][step])
                if authorized == 0:
                    conflicts.append({
                        "Type": "Authorization Gap",
                        "Description": f"No user authorized for step {step+1}"
                    })
        
        # Check at-most-k feasibility if active
        if self.active_constraints.get('at_most_k', True):
            for k, steps in self.instance.at_most_k:
                total_users = len(set(u for u in range(self.instance.number_of_users)
                                    for s in steps if self.instance.user_step_matrix[u][s]))
                min_users_needed = len(steps) / k
                if total_users < min_users_needed:
                    conflicts.append({
                        "Type": "At-Most-K Infeasibility",
                        "Description": f"At-most-{k} constraint on steps {[s+1 for s in steps]} "
                                     f"requires at least {min_users_needed:.0f} users but only "
                                     f"has {total_users} authorized users"
                    })
        
        return conflicts

    def _process_solution(self, start_time):
        solution_dict = {}
        for step in range(self.instance.number_of_steps):
            for user, var in self.var_manager.step_variables[step]:
                if self.solver.Value(var):
                    solution_dict[step + 1] = user + 1
                    break

        # self._log("\nSolution found. Verifying constraints...")
        result = Solution.create_sat(
            time.time() - start_time,
            solution_dict
        )
        
        # Ensure violations field exists
        violations = self.solution_verifier.verify_solution(solution_dict) if hasattr(self.solution_verifier, 'verify_solution') else []
        result.violations = violations
        
        # Add required fields for metadata
        result.solve_time = self.solve_time
        result.solver_type = self.__class__.__name__
        
        if violations:
            self._log("\nCONSTRAINT VIOLATIONS FOUND!")
            # self._log("\nConstraint Violations Found:")
            # for violation in violations:
            #     self._log(violation)
        else:
            self._log("\nALL CONSTRAINTS SATISFIED!")
        print("From Process Solution method", result)
        return result
    
    def _build_model(self):
        """Build model with active constraints"""
        try:
            self._log("Creating variables...")
            self.var_manager.create_variables()
            
            self._log("Adding constraints...")
            self.constraint_manager = ConstraintManager(
                self.model,
                self.instance,
                self.var_manager
            )
            
            # Add active constraints only
            if self.active_constraints.get('authorizations', True):
                self.constraint_manager.add_authorization_constraints()
                self._log("Added authorization constraints")
            
            if self.active_constraints.get('separation_of_duty', True):
                self.constraint_manager.add_separation_of_duty()
                self._log("Added separation of duty constraints")
            
            if self.active_constraints.get('binding_of_duty', True):
                if not self.constraint_manager.add_binding_of_duty():
                    self._log("Failed to add binding of duty constraints")
                    return False
                self._log("Added binding of duty constraints")
            
            if self.active_constraints.get('at_most_k', True):
                self.constraint_manager.add_at_most_k()
                self._log("Added at-most-k constraints")
            
            if self.active_constraints.get('one_team', True):
                self.constraint_manager.add_one_team()
                self._log("Added one-team constraints")

            return True

        except Exception as e:
            self._log(f"Error building model: {str(e)}")
            return False

    def _handle_build_failure(self, start_time):
        """Handle model building failures"""
        conflicts = self.analyze_constraint_conflicts()
        
        if not conflicts:
            reason = "Problem is infeasible but no specific cause could be determined"
        else:
            reason = "\n".join(f"Conflict {i+1}: {conflict['Description']}" 
                            for i, conflict in enumerate(conflicts))

        # return Solution.create_unsat(time.time() - start_time, reason=reason)
        return Solution.create_unsat(time.time() - start_time)

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

    def _get_authorization_gaps(self):
        """Get steps with no authorized users"""
        gaps = []
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                gaps.append(step)
        return gaps

    def _get_team_conflicts(self):
        """Get conflicts between team constraints and other constraints"""
        conflicts = []
        if not hasattr(self.instance, 'one_team'):
            return conflicts
            
        for steps, teams in self.instance.one_team:
            # Check BOD conflicts
            for s1 in steps:
                for bod_s1, bod_s2 in self.instance.BOD:
                    if s1 == bod_s1 and bod_s2 not in steps:
                        conflicts.append(
                            f"Team constraint on step {s1+1} conflicts with "
                            f"BOD constraint with step {bod_s2+1}"
                        )
                    elif s1 == bod_s2 and bod_s1 not in steps:
                        conflicts.append(
                            f"Team constraint on step {s1+1} conflicts with "
                            f"BOD constraint with step {bod_s1+1}"
                        )
        return conflicts

    def _handle_infeasible(self, start_time, status):
        """Handle infeasible results"""
        causes = []
        
        # Check authorization gaps
        if self.active_constraints.get('authorizations', True):
            gaps = self._get_authorization_gaps()
            if gaps:
                causes.append(f"Steps with no authorized users: {[s+1 for s in gaps]}")

        # Check BOD feasibility
        if self.active_constraints.get('binding_of_duty', True):
            for s1, s2, common_users in self._get_bod_users():
                if not common_users:
                    causes.append(
                        f"BOD constraint cannot be satisfied: No users authorized "
                        f"for both steps {s1+1} and {s2+1}"
                    )

        # Build reason message
        if causes:
            reason = "The problem is infeasible for the following reasons:\n"
            for i, cause in enumerate(causes, 1):
                reason += f"{i}. {cause}\n"
        else:
            reason = "Problem is infeasible but no specific cause could be determined"
            
        if self.instance.SOD:
            reason += "\nNote: Problem has Separation of Duty constraints that may create conflicts"
        if self.instance.at_most_k:
            reason += "\nNote: Problem has At-most-k constraints that limit assignments"
            
        return Solution.create_unsat(time.time() - start_time, reason=reason)

    def _handle_error(self, start_time, error):
        print("Error", error)
        """Handle solver errors"""
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
