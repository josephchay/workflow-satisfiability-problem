from collections import defaultdict
import time
from typing import Dict, List, Set, Tuple

from utils import log
from typings import Solution


class BaseSolver:
    """Base class for all solvers providing common functionality"""
    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        self.instance = instance
        self.active_constraints = active_constraints
        self.gui_mode = gui_mode
        self.model = None
        self.solver = None
        self.var_manager = None
        self.constraint_manager = None
        self.solve_time = 0
        self.solution_unique = None
        
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
        """Setup solver with default parameters. Must be implemented by child classes."""
        raise NotImplementedError
        
    def solve(self):
        """Main solving method. Must be implemented by child classes."""
        raise NotImplementedError

    def _build_model(self):
        """Build model with active constraints. Must be implemented by child classes."""
        raise NotImplementedError

    def identify_constraint_conflicts(self) -> List[Dict]:
        """Analyze potential constraint conflicts - common for all solvers"""
        conflicts = []

        # First add BOD authorization gaps as conflicts
        if self.active_constraints.get('binding_of_duty', True):
            self._check_bod_conflicts(conflicts)

        # Check BOD-SOD conflicts if both active
        if self.active_constraints.get('binding_of_duty', True) and \
           self.active_constraints.get('separation_of_duty', True):
            self._check_bod_sod_conflicts(conflicts)
        
        # Check authorization gaps
        if self.active_constraints.get('authorizations', True):
            self._check_authorization_gaps(conflicts)
        
        # Check at-most-k feasibility
        if self.active_constraints.get('at_most_k', True):
            self._check_at_most_k_feasibility(conflicts)

        # Check constraints specific to extended types
        self._check_one_team_feasibility(conflicts)
        self._check_sual_feasibility(conflicts)
        self._check_wang_li_feasibility(conflicts)
        self._check_ada_feasibility(conflicts)

        return conflicts

    def _check_bod_conflicts(self, conflicts: List[Dict]):
        """Check for BOD authorization gaps"""
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

    def _check_bod_sod_conflicts(self, conflicts: List[Dict]):
        """Check for BOD-SOD conflicts"""
        for bod_s1, bod_s2 in self.instance.BOD:
            for sod_s1, sod_s2 in self.instance.SOD:
                if {bod_s1, bod_s2} & {sod_s1, sod_s2}:
                    conflicts.append({
                        "Type": "BOD-SOD Conflict",
                        "Description": f"Steps {bod_s1+1},{bod_s2+1} must be same user (BOD) but "
                                    f"steps {sod_s1+1},{sod_s2+1} must be different users (SOD)"
                    })

    def _check_authorization_gaps(self, conflicts: List[Dict]):
        """Check for steps with no authorized users"""
        for step in range(self.instance.number_of_steps):
            authorized = sum(1 for u in range(self.instance.number_of_users)
                        if self.instance.user_step_matrix[u][step])
            if authorized == 0:
                conflicts.append({
                    "Type": "Authorization Gap",
                    "Description": f"No user authorized for step {step+1}"
                })

    def _check_at_most_k_feasibility(self, conflicts: List[Dict]):
        """Check if at-most-k constraints can be satisfied"""
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

    def _check_one_team_feasibility(self, conflicts: List[Dict]):
        """Check One-team constraint feasibility"""
        if not hasattr(self.instance, 'one_team') or \
           not self.active_constraints.get('one_team', True):
            return

        for idx, (steps, teams) in enumerate(self.instance.one_team):
            self._check_team_authorizations(conflicts, idx, steps, teams)
            self._check_team_coverage(conflicts, steps, teams)

    def _check_team_authorizations(self, conflicts: List[Dict], idx: int, steps: Set[int], teams: List[Set[int]]):
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

    def _check_team_coverage(self, conflicts: List[Dict], steps: Set[int], teams: List[Set[int]]):
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

    def _check_sual_feasibility(self, conflicts: List[Dict]):
        """Check SUAL constraint feasibility"""
        if not hasattr(self.instance, 'sual') or \
           not self.active_constraints.get('super_user_at_least', True):
            return

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

    def _check_wang_li_feasibility(self, conflicts: List[Dict]):
        """Check Wang-Li constraint feasibility"""
        if not hasattr(self.instance, 'wang_li') or \
           not self.active_constraints.get('wang_li', True):
            return

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

    def _check_ada_feasibility(self, conflicts: List[Dict]):
        """Check Assignment Dependent constraint feasibility"""
        if not hasattr(self.instance, 'ada') or \
           not self.active_constraints.get('assignment_dependent', True):
            return

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
            "Authorization": sum(1 for row in self.instance.auth if any(row)),
            "Separation Of Duty": len(self.instance.SOD),
            "Binding Of Duty": len(self.instance.BOD),
            "At Most K": len(self.instance.at_most_k),
            "One Team": len(getattr(self.instance, 'one_team', [])),
            "Super User At Least": len(getattr(self.instance, 'sual', [])),
            "Wang Li": len(getattr(self.instance, 'wang_li', [])),
            "Assignment Dependent": len(getattr(self.instance, 'ada', []))
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
        """Handle solver errors in a standard way"""
        log(self.gui_mode, f"Error during solving: {str(error)}")

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
