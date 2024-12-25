from collections import defaultdict
from typing import Dict
from ortools.sat.python import cp_model
import time

from constants import SolverType
from solvers import BaseSolver
from typings import VariableManager, ConstraintManager, Solution, Verifier


class ORToolsCPSolver(BaseSolver):
    SOLVER_TYPE = SolverType.ORTOOLS_CP

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

        # Initialize constraint manager
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
            
            conflicts = self.analyze_constraint_conflicts()
            
            self._log("Building model...")
            if not self._build_model():
                print("Failed to build model. Analyzing infeasibility...")
                result = self._handle_build_failure(start_time)
                self._update_statistics(result)
                return result

            self._log("Solving model...")
            status = self.solver.Solve(self.model)
            self.solve_time = time.time() - start_time
            
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                print("Solution found. Verifying constraints...")
                result = self._process_solution(start_time)
                self._update_statistics(result)
                return result
            else:
                print("No solution found. Analyzing infeasibility...")
                result = self._handle_infeasible(start_time, status)
                self._update_statistics(result)
                return result
                
        except Exception as e:
            print(f"Error during solving: {str(e)}")
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
            "One Team Violations": "N/A" if not result.is_sat else len([v for v in result.violations if "One-team" in v]),
            "Super User At Least Violations": "N/A" if not result.is_sat else len([v for v in result.violations if "Super User" in v]),
            "Wang Li Violations": "N/A" if not result.is_sat else len([v for v in result.violations if "Wang Li" in v]),
            "Assignment Dependent Violations": "N/A" if not result.is_sat else len([v for v in result.violations if "Assignment Dependent" in v])
        }

        # Constraint Distribution
        self.statistics["constraint_distribution"] = {
            "Authorization": sum(1 for user in self.instance.auth if user),
            "Separation Of Duty": len(self.instance.SOD),
            "Binding Of Duty": len(self.instance.BOD),
            "At Most K": len(self.instance.at_most_k),
            "One Team": len(self.instance.one_team),
            "Super User At Least": len(self.instance.sual),
            "Wang Li": len(self.instance.wang_li),
            "Assignment Dependent": len(self.instance.ada),
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

        # Check BOD-SOD conflicts if both active
        if self.active_constraints.get('binding_of_duty', True) and \
        self.active_constraints.get('separation_of_duty', True):
            for bod_s1, bod_s2 in self.instance.BOD:
                for sod_s1, sod_s2 in self.instance.SOD:
                    if {bod_s1, bod_s2} & {sod_s1, sod_s2}:
                        conflicts.append({
                            "Type": "BOD-SOD Conflict",
                            "Description": f"Steps {bod_s1+1},{bod_s2+1} must be same user (BOD) but "
                                        f"steps {sod_s1+1},{sod_s2+1} must be different users (SOD)"
                        })
        
        # Check authorization gaps
        if self.active_constraints.get('authorizations', True):
            for step in range(self.instance.number_of_steps):
                authorized = sum(1 for u in range(self.instance.number_of_users)
                            if self.instance.user_step_matrix[u][step])
                if authorized == 0:
                    conflicts.append({
                        "Type": "Authorization Gap",
                        "Description": f"No user authorized for step {step+1}"
                    })
        
        # Check at-most-k feasibility
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

        # Check SUAL feasibility
        if self.active_constraints.get('super_user_at_least', True):
            for scope, h, super_users in self.instance.sual:
                # Check if there are enough super users authorized for the scope
                authorized_super_users = set()
                for u in super_users:
                    if all(self.instance.user_step_matrix[u][s] for s in scope):
                        authorized_super_users.add(u)
                
                if len(authorized_super_users) < h:
                    conflicts.append({
                        "Type": "SUAL Authorization Gap",
                        "Description": f"Only {len(authorized_super_users)} super users authorized for all steps "
                                    f"{[s+1 for s in scope]}, but {h} required"
                    })

        # Check Wang-Li feasibility
        if self.active_constraints.get('wang_li', True):
            for scope, departments in self.instance.wang_li:
                # Check if at least one department can cover all steps
                dept_coverage = [False] * len(departments)
                for i, dept in enumerate(departments):
                    can_cover = True
                    for step in scope:
                        if not any(self.instance.user_step_matrix[u][step] for u in dept):
                            can_cover = False
                            break
                    dept_coverage[i] = can_cover
                
                if not any(dept_coverage):
                    conflicts.append({
                        "Type": "Wang-Li Infeasibility",
                        "Description": f"No department can cover all steps {[s+1 for s in scope]}"
                    })

        # Check ADA feasibility
        if self.active_constraints.get('assignment_dependent', True):
            for s1, s2, source_users, target_users in self.instance.ada:
                # Check if source users are authorized for s1
                if not any(self.instance.user_step_matrix[u][s1] for u in source_users):
                    conflicts.append({
                        "Type": "ADA Source Authorization Gap",
                        "Description": f"No source users authorized for step {s1+1}"
                    })
                
                # Check if target users are authorized for s2
                if not any(self.instance.user_step_matrix[u][s2] for u in target_users):
                    conflicts.append({
                        "Type": "ADA Target Authorization Gap", 
                        "Description": f"No target users authorized for step {s2+1}"
                    })

        return conflicts

    def _process_solution(self, start_time):
        solution_dict =  self.var_manager.get_assignment_from_solution(self.solver)

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
        result.solver_type = self.SOLVER_TYPE.value
        
        if violations:
            self._log("\nCONSTRAINT VIOLATIONS FOUND!")
            # self._log("\nConstraint Violations Found:")
            # for violation in violations:
            #     self._log(violation)
        else:
            self._log("\nALL CONSTRAINTS SATISFIED!")

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
            is_feasible, errors = self.constraint_manager.add_constraints(self.active_constraints)
            if not is_feasible:
                self._log("Failed to add constraints:")
                for error in errors:
                    self._log(f"  - {error}")
                return False
                
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

    def _handle_infeasible(self, start_time, status):
        """Handle infeasible results with comprehensive conflict analysis"""
        # Detailed analysis of potential infeasibility causes
        reason = "\n"

        # 1. Authorization Gaps Analysis
        auth_gaps = self._get_authorization_gaps()
        if auth_gaps:
            reason += "CRITICAL AUTHORIZATION GAPS:\n"
            reason += "  - Some steps have NO authorized users:\n"
            for gap in auth_gaps:
                reason += f"    * Step {gap+1} has no authorized users\n"
            reason += "\n"

        # 2. Separation of Duty Constraint Analysis
        sod_conflicts = self._analyze_sod_conflicts()
        if sod_conflicts:
            reason += "SEPARATION OF DUTY (SOD) CONFLICTS:\n"
            for conflict in sod_conflicts:
                reason += f"  - {conflict}\n"
            reason += "\n"

        # 3. Binding of Duty Constraint Analysis
        bod_conflicts = self._analyze_bod_conflicts()
        if bod_conflicts:
            reason += "BINDING OF DUTY (BOD) CONFLICTS:\n"
            for conflict in bod_conflicts:
                reason += f"  - {conflict}\n"
            reason += "\n"

        # 4. At-Most-K Constraint Analysis
        amk_conflicts = self._analyze_at_most_k_conflicts()
        if amk_conflicts:
            reason += "AT-MOST-K CONSTRAINT VIOLATIONS:\n"
            for conflict in amk_conflicts:
                reason += f"  - {conflict}\n"
            reason += "\n"

        # 5. One-Team Constraint Analysis
        oneteam_conflicts = self._analyze_one_team_conflicts()
        if oneteam_conflicts:
            reason += "ONE-TEAM CONSTRAINT CONFLICTS:\n"
            for conflict in oneteam_conflicts:
                reason += f"  - {conflict}\n"
            reason += "\n"

        # 6. Authorization Distribution Analysis
        auth_distribution_issues = self._analyze_auth_distribution()
        if auth_distribution_issues:
            reason += "AUTHORIZATION DISTRIBUTION ISSUES:\n"
            for issue in auth_distribution_issues:
                reason += f"  - {issue}\n"
            reason += "\n"

        # Final summary
        if not (auth_gaps or sod_conflicts or bod_conflicts or 
                amk_conflicts or oneteam_conflicts or auth_distribution_issues):
            reason += "NO SPECIFIC CONFLICTS DETECTED\n"
            reason += "The problem appears unsatisfiable due to the complex interaction of constraints\n"

        return Solution.create_unsat(time.time() - start_time, reason=reason)

    def _get_authorization_gaps(self):
        """Get steps with no authorized users"""
        return [step for step in range(self.instance.number_of_steps)
                if not any(self.instance.user_step_matrix[user][step] 
                        for user in range(self.instance.number_of_users))]

    def _analyze_sod_conflicts(self):
        """Analyze potential Separation of Duty conflicts"""
        sod_conflicts = []
        for s1, s2 in self.instance.SOD:
            # Check if any user is authorized for both steps
            common_users = [
                user for user in range(self.instance.number_of_users)
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2])
            ]
            if common_users:
                sod_conflicts.append(
                    f"SOD Violation: Step {s1+1} and {s2+1} MUST be performed by different users, "
                    f"but users {[u+1 for u in common_users]} are authorized for both"
                )
        return sod_conflicts

    def _analyze_bod_conflicts(self):
        """Analyze Binding of Duty constraint conflicts"""
        bod_conflicts = []
        for s1, s2 in self.instance.BOD:
            # Find users authorized for both steps
            common_users = [
                user for user in range(self.instance.number_of_users)
                if (self.instance.user_step_matrix[user][s1] and 
                    self.instance.user_step_matrix[user][s2])
            ]
            if not common_users:
                bod_conflicts.append(
                    f"BOD Violation: Step {s1+1} and {s2+1} MUST be performed by the SAME user, "
                    "but NO common authorized users exist"
                )
        return bod_conflicts

    def _analyze_at_most_k_conflicts(self):
        """Analyze At-Most-K constraint potential conflicts"""
        amk_conflicts = []
        for k, steps in self.instance.at_most_k:
            # Calculate total authorized users for the step group
            total_users = len(set(
                user for user in range(self.instance.number_of_users)
                if any(self.instance.user_step_matrix[user][s] for s in steps)
            ))
            min_users_needed = len(steps) / k
            if total_users < min_users_needed:
                amk_conflicts.append(
                    f"At-Most-K Violation: Constraint requires at least {min_users_needed:.0f} users "
                    f"for steps {[s+1 for s in steps]}, but only {total_users} users are available"
                )
        return amk_conflicts

    def _analyze_one_team_conflicts(self):
        """Analyze One-Team constraint potential conflicts"""
        oneteam_conflicts = []
        if hasattr(self.instance, 'one_team'):
            for steps, teams in self.instance.one_team:
                # Check if each step has users from at least one team
                for step in steps:
                    step_users = set(
                        user for user in range(self.instance.number_of_users)
                        if self.instance.user_step_matrix[user][step]
                    )
                    
                    # Check if step users belong to any team
                    team_match = any(
                        step_users.intersection(set(team)) 
                        for team in teams
                    )
                    
                    if not team_match:
                        oneteam_conflicts.append(
                            f"One-Team Violation: Step {step+1} has NO users from any specified team groups"
                        )
        return oneteam_conflicts

    def _analyze_auth_distribution(self):
        """Analyze authorization distribution across steps and users"""
        issues = []
        
        # Steps with very few authorized users
        for step in range(self.instance.number_of_steps):
            authorized = sum(1 for u in range(self.instance.number_of_users) 
                            if self.instance.user_step_matrix[u][step])
            if authorized < 2:
                issues.append(
                    f"Low Authorization: Step {step+1} has only {authorized} authorized user(s)"
                )
        
        # Users with very few authorizations
        for user in range(self.instance.number_of_users):
            authorized_steps = sum(1 for s in range(self.instance.number_of_steps) 
                                    if self.instance.user_step_matrix[user][s])
            if authorized_steps == 0:
                issues.append(
                    f"User {user+1} has NO authorized steps"
                )
        
        return issues

    def _handle_error(self, start_time, error):
        self._log(f"Error during solving: {str(error)}")

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
