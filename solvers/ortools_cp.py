from collections import defaultdict
from typing import Dict
from ortools.sat.python import cp_model
import time

from constants import SolverType
from solvers import BaseSolver
from typings import VariableManager, ConstraintManager, Solution, UniquenessChecker, Verifier


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
        conflicts = self.identify_constraint_conflicts()
        
        try:
            start_time = time.time()
            self.solve_time = 0
            
            self._log("Building model...")
            if not self._build_model():
                self._log("Failed to build model. Analyzing infeasibility...")
                result = self._handle_build_failure(start_time, conflicts)
                self._update_statistics(result, conflicts)
                return result

            self._log("Solving model...")
            # First find initial solution
            status = self.solver.Solve(self.model)
            
            # If solution found, save it and check uniqueness
            is_unique = None
            first_solution = None
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                # Save first solution
                self._log("Found first solution, saving it...")
                first_solution = self.var_manager.get_assignment_from_solution(self.solver)
                
                self._log("Checking solution uniqueness...")
                try:
                    # Create uniqueness checker
                    uniqueness_checker = UniquenessChecker(self.var_manager)
                    
                    # Configure solver for finding all solutions
                    self.solver.parameters.enumerate_all_solutions = True
                    self.solver.parameters.num_search_workers = 1  # Use single thread for enumeration
                    
                    # Try to find second solution
                    _ = self.solver.Solve(self.model, solution_callback=uniqueness_checker)
                    
                    # Store uniqueness result
                    is_unique = uniqueness_checker.solutions_found == 1
                    self.solution_unique = is_unique  # Store for statistics
                    
                    self._log(f"Uniqueness check complete: {'unique' if is_unique else 'not unique'}")
                except Exception as e:
                    self._log(f"Error during uniqueness check: {str(e)}")
                    # If uniqueness check fails, assume non-unique
                    is_unique = False
                    self.solution_unique = False
            
            self.solve_time = time.time() - start_time
            
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                self._log("Processing solution...")
                # Use first solution we saved
                if first_solution:
                    # Create solution object using first solution found
                    result = Solution.create_sat(
                        self.solve_time,
                        first_solution
                    )
                else:
                    # Fallback to current solution if something went wrong
                    result = self._process_solution(start_time)
                    
                self._update_statistics(result, conflicts)
                return result
            else:
                self._log("No solution found. Analyzing infeasibility...")
                result = self._handle_infeasible(start_time, status, conflicts)
                self._update_statistics(result, conflicts)
                return result
                
        except Exception as e:
            self._log(f"Error during solving: {str(e)}")
            result = self._handle_error(start_time, e)
            self._update_statistics(result, conflicts)
            return result

    def _update_statistics(self, result, conflicts):
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
            "Solution Time": f"{self.solve_time:.2f} seconds",
            "Solution Uniqueness": "Unique" if result.is_sat and hasattr(self, 'solution_unique') and self.solution_unique else
                                 "Not Unique" if result.is_sat and hasattr(self, 'solution_unique') else "N/A"
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
            self._add_detailed_analysis(conflicts)

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

    def _add_detailed_analysis(self, conflicts):
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
            "One Team": [],
            "Super User At Least": [],
            "Wang Li": [],
            "Assignment Dependent": [],
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

        # SUAL constraints
        if hasattr(self.instance, 'sual'):
            for scope, h, super_users in self.instance.sual:
                auth_super_users = []
                for user in super_users:
                    if all(self.instance.user_step_matrix[user][s] for s in scope):
                        auth_super_users.append(user + 1)
                
                constraint_analysis["Super User At Least"].append({
                    "Steps": [s+1 for s in scope],
                    "Required Count": h,
                    "Authorized Super Users": sorted(auth_super_users),
                    "Description": f"Steps {[s+1 for s in scope]} must have {h} super users "
                                f"if assigned to {h} or fewer users"
                })

        # Wang-Li constraints
        if hasattr(self.instance, 'wang_li'):
            for scope, departments in self.instance.wang_li:
                dept_analysis = []
                for dept_idx, dept in enumerate(departments):
                    authorized_steps = []
                    for step in scope:
                        if any(self.instance.user_step_matrix[u][step] for u in dept):
                            authorized_steps.append(step + 1)
                    dept_analysis.append({
                        "Department": dept_idx + 1,
                        "Users": [u+1 for u in dept],
                        "Authorized Steps": authorized_steps
                    })
                
                constraint_analysis["Wang Li"].append({
                    "Steps": [s+1 for s in scope],
                    "Departments": dept_analysis,
                    "Description": f"Steps {[s+1 for s in scope]} must be assigned to users "
                                f"from the same department"
                })

        # ADA constraints
        if hasattr(self.instance, 'ada'):
            for s1, s2, source_users, target_users in self.instance.ada:
                auth_source = [u+1 for u in source_users 
                            if self.instance.user_step_matrix[u][s1]]
                auth_target = [u+1 for u in target_users 
                            if self.instance.user_step_matrix[u][s2]]
                
                constraint_analysis["Assignment Dependent"].append({
                    "Source Step": s1 + 1,
                    "Target Step": s2 + 1,
                    "Authorized Source Users": sorted(auth_source),
                    "Authorized Target Users": sorted(auth_target),
                    "Description": f"If step {s1+1} is assigned to a user from {[u+1 for u in source_users]}, "
                                f"then step {s2+1} must be assigned to a user from {[u+1 for u in target_users]}"
                })

        detailed["Constraint Analysis"] = constraint_analysis

        # # Only add Conflict Analysis if it's not already shown in UNSAT analysis
        # if conflicts and "reason" not in self.statistics["solution_status"]: 
        #     detailed["Conflict Analysis"] = {
        #         "Detected Conflicts": conflicts,
        #         "Description": "Potential conflicts detected in constraint specifications"
        #     }

        # self.statistics["detailed_analysis"] = detailed

        # Add Conflict Analysis section if conflicts exist
        if conflicts: 
            detailed["Conflict Analysis"] = {
                "Detected Conflicts": conflicts,
                "Description": "Potential conflicts detected in constraint specifications"
            }

        self.statistics["detailed_analysis"] = detailed

    def identify_constraint_conflicts(self):
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

        # Check One-team constraint feasibility
        if self.active_constraints.get('one_team', True):
            for idx, (steps, teams) in enumerate(self.instance.one_team):
                # Check if all referenced users exist and have required authorizations
                for team_idx, team in enumerate(teams):
                    unauthorized_users = []
                    for user in team:
                        has_auth = False
                        for step in steps:
                            if self.instance.user_step_matrix[user][step]:
                                has_auth = True
                                break
                        if not has_auth:
                            unauthorized_users.append(user + 1)
                            
                    if unauthorized_users:
                        conflicts.append({
                            "Type": "One-Team Authorization Gap",
                            "Description": f"Team {team_idx + 1} in constraint {idx + 1} has users {unauthorized_users} "
                                        f"who are not authorized for any steps in scope {[s+1 for s in steps]}"
                        })
                
                # Check if there's enough authorized users in each team
                for step in steps:
                    teams_covering_step = []
                    for team_idx, team in enumerate(teams):
                        if any(self.instance.user_step_matrix[user][step] for user in team):
                            teams_covering_step.append(team_idx + 1)
                    
                    if not teams_covering_step:
                        conflicts.append({
                            "Type": "One-Team Coverage Gap",
                            "Description": f"No team has any users authorized for step {step + 1}"
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

    def _handle_build_failure(self, start_time, conflicts):
        """Handle model building failures"""
        # Build reason message based on detected conflicts
        if not conflicts:
            reason = "Problem is infeasible but no specific cause could be determined"
        else:
            reason = "\n".join(f"Conflict {i+1}: {conflict['Description']}" 
                            for i, conflict in enumerate(conflicts))

        # return Solution.create_unsat(time.time() - start_time, reason=reason)
        return Solution.create_unsat(time.time() - start_time)

    def _handle_infeasible(self, start_time, status, conflicts):
        """Handle infeasible results with comprehensive conflict analysis"""
        # Build reason message based on detected conflicts
        if conflicts:
            # Organize conflicts by type
            conflict_types = {}
            for conflict in conflicts:
                conflict_type = conflict.get('Type', 'Unknown Conflict')
                if conflict_type not in conflict_types:
                    conflict_types[conflict_type] = []
                conflict_types[conflict_type].append(conflict['Description'])
            
            # Construct detailed reason
            reason = "The problem is infeasible due to the following conflicts:\n"
            for conflict_type, descriptions in conflict_types.items():
                reason += f"\n{conflict_type}:\n"
                for desc in descriptions:
                    reason += f"  - {desc}\n"
        else:
            reason = "Problem is infeasible but no specific cause could be determined"
        
        # Add general notes about constraint types
        if self.instance.SOD:
            reason += "\nNote: Separation of Duty constraints may create additional conflicts"
        if self.instance.at_most_k:
            reason += "\nNote: At-most-k constraints limit user assignments"
        
        # Add constraints from other types if they exist
        constraint_notes = [
            (hasattr(self.instance, 'sual') and self.instance.sual, "Super User At Least constraints"),
            (hasattr(self.instance, 'wang_li') and self.instance.wang_li, "Wang-Li constraints"),
            (hasattr(self.instance, 'ada') and self.instance.ada, "Assignment Dependent constraints")
        ]
        
        for has_constraints, note in constraint_notes:
            if has_constraints:
                reason += f"\nNote: {note} may introduce additional complexity"
        
        # return Solution.create_unsat(time.time() - start_time, reason=reason)
        return Solution.create_unsat(time.time() - start_time)

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
