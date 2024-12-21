import os
from typing import Dict, List, Optional
import time
import copy
import customtkinter

from typings import Instance
from typings import WSPSolverType, NotEquals, AtMost, OneTeam
from stats import WSPMetadataHandler


class WSPController:
    def __init__(self, view, factory):
        self.view = view
        self.current_instance: Optional[Instance] = None
        self.current_solver_type = WSPSolverType.ORTOOLS_CS  # Default solver

        # Connect button callbacks
        self.view.select_button.configure(command=self.select_file)
        self.view.solve_button.configure(command=self.solve)
        
        # Create solver factory
        self.solver_factory = factory
 
        # Initialize metadata handler
        self.metadata_handler = WSPMetadataHandler()
        
        # Add visualization button to view
        self.view.add_visualization_button(self.generate_visualizations)

    def on_solver_change(self, value: str):
        """Handle solver type selection change"""
        self.current_solver_type = WSPSolverType(value)
        self.view.update_status(f"Selected solver: {value}")

    def select_file(self):
        """Handle file selection"""
        filename = customtkinter.filedialog.askopenfilename(
            title="Select WSP Instance",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                instance = Instance(filename)  # Create new instance
                self.current_instance = instance  # Use property setter
                
                # Update file label with the selected file name
                self.view.update_file_label(filename)
                self.view.update_instance_label(filename)
                self.view.update_status(f"Loaded: {filename}")

                # Display instance statistics
                self.display_instance_stats()

            except Exception as e:
                self.view.update_status(f"Error loading file: {str(e)}")
                self.view.update_instance_label(None)
                self.current_instance = None  # Reset if error

    def get_active_constraints(self) -> Dict[str, bool]:
        """Get current active constraints from view"""
        return {
            name: var.get()
            for name, var in self.view.constraint_vars.items()
        }

    def solve(self):
        """Handle solving the current instance with respect to activated/deactivated constraints"""
        if not self.current_instance:
            self.view.update_status("Please select a file first")
            return
        
        try:
            # Get active constraints configuration
            active_constraints = self.get_active_constraints()
            self.view.update_status(f"Solving with {self.current_solver_type.value}...")
            self.view.update_progress(0.1)

            # Create copy of instance for solving
            solving_instance = copy.deepcopy(self.current_instance)

            # Filter constraints based on active status
            original_cons = solving_instance.cons
            solving_instance.cons = []
            for c in original_cons:
                if ((isinstance(c, NotEquals) and not c.is_bod and active_constraints['separation_of_duty']) or
                    (isinstance(c, NotEquals) and c.is_bod and active_constraints['binding_of_duty']) or
                    (isinstance(c, AtMost) and active_constraints['at_most_k']) or
                    (isinstance(c, OneTeam) and active_constraints['one_team'])):
                    solving_instance.cons.append(c)

            # Handle authorization deactivation
            if not active_constraints['authorizations']:
                for u in range(solving_instance.n):
                    solving_instance.auths[u].collection = [True] * solving_instance.k

            self.view.update_progress(0.2)

            # Create solver with filtered instance
            solver = self.solver_factory.create_solver(
                self.current_solver_type,
                solving_instance,
                active_constraints
            )

            # Solve instance
            start_time = time.time()
            solution = solver.solve()
            solve_time = time.time() - start_time

            self.view.update_progress(0.6)

            # Process solution
            display_solution = None
            if solution and solution.assignment:
                display_solution = [
                    {'step': s + 1, 'user': solution.assignment[s] + 1}
                    for s in range(len(solution.assignment))
                ]

            self.view.update_progress(0.7)

            # Collect instance details
            instance_details = self._collect_instance_metrics()

            # Create result dictionary
            result_dict = {
                'sat': 'sat' if display_solution else 'unsat',
                'result_exe_time': solution.time * 1000 if solution else solve_time * 1000,
                'sol': display_solution if display_solution else [],
                'solution_count': 1 if display_solution else 0,
                'is_unique': False
            }

            # Save metadata
            metadata_path = self.metadata_handler.save_result_metadata(
                instance_details=instance_details,
                solver_result=result_dict,
                solver_type=self.current_solver_type.value,
                active_constraints=active_constraints,
                filename=os.path.basename(self.view.current_file)
            )

            self.view.update_progress(0.8)

            # Collect statistics, including violations for ALL constraints
            stats = {
                "Status": "SAT" if display_solution else "UNSAT",
                "Solver Type": self.current_solver_type.value,
                "Solve Time": f"{solve_time:.2f} seconds",
                "Instance Details": instance_details
            }

            if display_solution:
                # Add solution-specific metrics
                stats["Solution Metrics"] = self._analyze_user_metrics(display_solution)
                
                # Check violations against ALL constraints (including inactive)
                # This helps users see what constraints would be violated
                violations = self._analyze_constraint_satisfaction(
                    display_solution,
                    {k: True for k in active_constraints.keys()}  # Check all constraint types
                )

                # Add violations to stats
                stats["Constraint Violations"] = {}
                # Always show all constraint types, even if 0 violations
                constraint_types = [
                    "Authorization",
                    "Separation of Duty",
                    "Binding of Duty",
                    "At Most K",
                    "One Team"
                ]
                for c_type in constraint_types:
                    stats["Constraint Violations"][c_type] = violations.get(c_type, 0)

                # Add note if some constraints were inactive
                inactive_constraints = [k for k, v in active_constraints.items() if not v]
                if inactive_constraints:
                    stats["Notes"] = {
                        "Inactive Constraints": [k.replace('_', ' ').title() for k in inactive_constraints],
                        "Warning": "Solution found by ignoring inactive constraints. Violations are shown for reference."
                    }

            # Display results
            self.view.display_solution(display_solution)
            self.view.display_statistics(stats)

            # Update final status
            self.view.update_progress(1.0)
            status = "Solution found!" if display_solution else "No solution exists (UNSAT)"
            ignored_info = "" if all(active_constraints.values()) else " (with inactive constraints)"
            self.view.update_status(
                f"{status}{ignored_info} using {self.current_solver_type.value} "
                f"(solved in {solve_time:.2f} seconds)"
            )

        except Exception as e:
            self.view.update_status(f"Error solving: {str(e)}")
            self.view.update_progress(0)
            import traceback
            traceback.print_exc()

    def _collect_instance_metrics(self) -> Dict:
        """Collect metrics about the current instance"""
        if not self.current_instance:
            return {}

        constraint_counts = self._count_constraint_types()
        total_steps = self.current_instance.k
        total_users = self.current_instance.n
            
        return {
            "Steps": total_steps,
            "Users": total_users,
            "Total Constraints": len(self.current_instance.cons),
            "Constraint Distribution": {
                k.replace('_', ' ').title(): v 
                for k, v in constraint_counts.items()
            },
            "Problem Metrics": {
                "Auth Density": (constraint_counts["authorization"] / 
                               (total_steps * total_users)),
                "Constraint Density": (len(self.current_instance.cons) /
                                    (total_steps * total_users)),
                "Step-User Ratio": total_steps / total_users
            }
        }

    def generate_visualizations(self):
        """Generate visualizations from saved metadata"""
        try:
            self.view.update_status("Generating visualizations...")
            self.metadata_handler.generate_visualizations()
            self.view.update_status("Visualizations generated successfully!")
        except Exception as e:
            self.view.update_status(f"Error generating visualizations: {str(e)}")

    def display_instance_stats(self):
        """Display statistics about the loaded instance"""
        if not self.current_instance:
            return

        # Count different types of constraints
        sod_count = sum(1 for c in self.current_instance.cons 
                    if isinstance(c, NotEquals) and not c.is_bod)
        bod_count = sum(1 for c in self.current_instance.cons 
                    if isinstance(c, NotEquals) and c.is_bod)
        atmost_count = sum(1 for c in self.current_instance.cons 
                        if isinstance(c, AtMost))
        oneteam_count = sum(1 for c in self.current_instance.cons 
                        if isinstance(c, OneTeam))

        stats = {
            "Number of Steps": self.current_instance.k,
            "Number of Users": self.current_instance.n,
            "Number of Constraints": len(self.current_instance.cons),
            "Authorization Constraints": len([u for u in self.current_instance.auths 
                                        if any(u.collection)]),
            "Separation of Duty Constraints": sod_count,
            "Binding of Duty Constraints": bod_count,
            "At-Most-K Constraints": atmost_count,
            "One-Team Constraints": oneteam_count
        }

        self.view.display_instance_details(stats)

    def _collect_solution_stats(self, solution, display_solution: List[Dict[str, int]], 
                            solve_time: float, active_constraints: Dict[str, bool]) -> Dict:
        """Collect comprehensive statistics about the solution"""
        stats = {
            "Status": "SAT" if display_solution else "UNSAT",
            "Solver Type": self.current_solver_type.value,
            "Solve Time": f"{solve_time:.2f} seconds",
            "Instance Details": self._collect_instance_metrics()
        }

        if display_solution:
            stats["Solution Metrics"] = self._analyze_user_metrics(display_solution)
            violations = self._analyze_constraint_satisfaction(display_solution, active_constraints)
            if violations:
                stats["Constraint Violations"] = violations

        return stats

    def _count_constraint_types(self) -> Dict[str, int]:
        """Count different types of constraints in current instance"""
        if not self.current_instance:
            return {}
            
        return {
            "authorization": len([u for u in self.current_instance.auths if any(u.collection)]),
            "separation_of_duty": sum(1 for c in self.current_instance.cons 
                                if isinstance(c, NotEquals) and not c.is_bod),
            "binding_of_duty": sum(1 for c in self.current_instance.cons 
                                if isinstance(c, NotEquals) and c.is_bod),
            "at_most_k": sum(1 for c in self.current_instance.cons 
                            if isinstance(c, AtMost)),
            "one_team": sum(1 for c in self.current_instance.cons 
                            if isinstance(c, OneTeam))
        }

    def _analyze_user_metrics(self, solution: List[Dict[str, int]]) -> Dict[str, float]:
        """Calculate metrics about user assignments in solution"""
        user_counts = {}
        for assignment in solution:
            user = assignment['user']
            user_counts[user] = user_counts.get(user, 0) + 1

        return {
            "unique_users": len(user_counts),
            "max_steps_per_user": max(user_counts.values()),
            "min_steps_per_user": min(user_counts.values()),
            "avg_steps_per_user": sum(user_counts.values()) / len(user_counts)
        }

    def _check_constraint_violations(self, solution: List[Dict[str, int]], c) -> bool:
        """Check if a single constraint is violated by the solution"""
        if isinstance(c, NotEquals):
            if c.is_bod:
                # Check binding of duty
                user1 = next(a['user'] for a in solution if a['step'] - 1 == c.s1)
                user2 = next(a['user'] for a in solution if a['step'] - 1 == c.s2)
                return user1 != user2
            else:
                # Check separation of duty
                user1 = next(a['user'] for a in solution if a['step'] - 1 == c.s1)
                user2 = next(a['user'] for a in solution if a['step'] - 1 == c.s2)
                return user1 == user2
        
        elif isinstance(c, AtMost):
            users = set()
            for step in c.scope:
                user = next(a['user'] for a in solution if a['step'] - 1 == step)
                users.add(user)
            return len(users) > c.limit
        
        elif isinstance(c, OneTeam):
            assigned_users = set()
            for step in c.steps:
                user = next(a['user'] for a in solution if a['step'] - 1 == step)
                assigned_users.add(user - 1)  # Convert to 0-based
            
            return not any(assigned_users.issubset(set(team)) for team in c.teams)
            
        return False

    def _analyze_constraint_satisfaction(self, solution: List[Dict[str, int]], 
                                     active_constraints: Dict[str, bool]) -> Dict:
        """Analyze how the solution satisfies different constraints"""
        violations = {}
        
        if active_constraints['authorizations']:
            # Check authorization violations
            auth_violations = sum(
                1 for assignment in solution
                if not self.current_instance.auths[assignment['user'] - 1]
                .collection[assignment['step'] - 1]
            )
            if auth_violations > 0:
                violations["Authorization"] = auth_violations

        # Group constraints by type and check violations
        for constraint_type, is_active in active_constraints.items():
            if not is_active or constraint_type == 'authorizations':
                continue

            type_violations = 0
            for c in self.current_instance.cons:
                if ((constraint_type == 'separation_of_duty' and isinstance(c, NotEquals) and not c.is_bod) or
                    (constraint_type == 'binding_of_duty' and isinstance(c, NotEquals) and c.is_bod) or
                    (constraint_type == 'at_most_k' and isinstance(c, AtMost)) or
                    (constraint_type == 'one_team' and isinstance(c, OneTeam))):
                    
                    if self._check_constraint_violations(solution, c):
                        type_violations += 1

            if type_violations > 0:
                violations[constraint_type.replace('_', ' ').title()] = type_violations

        return violations

    def _create_solution_display(self, solution) -> Optional[List[Dict[str, int]]]:
        """Convert internal solution to display format"""
        if not solution or not solution.assignment:
            return None
            
        return [
            {'step': s + 1, 'user': solution.assignment[s] + 1}
            for s in range(len(solution.assignment))
        ]
