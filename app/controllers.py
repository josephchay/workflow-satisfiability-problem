import os
from typing import Dict, List, Optional
import time
import customtkinter

from typings import WSPInstance
from filesystem import parse_instance_file
from typings import WSPSolverType
from stats import WSPMetadataHandler


class WSPController:
    def __init__(self, view, factory):
        self.view = view
        self.current_instance: Optional[WSPInstance] = None
        self.current_solver_type = WSPSolverType.ORTOOLS_CS  # Default solver

        # Connect button callbacks
        self.view.select_button.configure(command=self.select_file)
        # self.view.select_folder_button.configure(command=self.select_folder)
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
                self.current_instance = parse_instance_file(filename)
                # Update file label with the selected file name
                self.view.update_file_label(filename)
                self.view.update_status(f"Loaded: {filename}")

                # Display instance statistics
                self.display_instance_stats()

            except Exception as e:
                self.view.update_status(f"Error loading file: {str(e)}")

    def select_folder(self):
        """Handle folder selection and solve all instances"""
        folder = customtkinter.filedialog.askdirectory(
            title="Select Folder with WSP Instances"
        )

        if not folder:
            return

        # Get all txt files in the folder
        instance_files = [f for f in os.listdir(folder) if f.endswith('.txt')]
        total_files = len(instance_files)
        
        if total_files == 0:
            self.view.update_status("No .txt files found in folder")
            return

        # Create summary statistics
        summary_stats = {
            'total': total_files,
            'sat': 0,
            'unsat': 0,
            'errors': 0,
            'times': []
        }

        # Process each file
        for i, filename in enumerate(instance_files, 1):
            full_path = os.path.join(folder, filename)
            self.view.update_file_label(full_path)
            self.view.update_status(f"Processing file {i}/{total_files}: {filename}")
            self.view.update_progress(i / total_files)

            try:
                # Load and solve instance
                instance = parse_instance_file(full_path)
                solver = self.solver_factory.create_solver(
                    self.current_solver_type,
                    instance,
                    self.get_active_constraints()
                )
                result = solver.solve()

                # Update statistics
                if result['sat'] == 'sat':
                    summary_stats['sat'] += 1
                else:
                    summary_stats['unsat'] += 1
                    
                summary_stats['times'].append(
                    float(result['result_exe_time'].replace('ms', ''))
                )

            except Exception as e:
                summary_stats['errors'] += 1
                print(f"Error processing {filename}: {str(e)}")

        # Display final summary
        avg_time = sum(summary_stats['times']) / len(summary_stats['times'])
        summary = {
            "Total Instances": summary_stats['total'],
            "Satisfiable": summary_stats['sat'],
            "Unsatisfiable": summary_stats['unsat'],
            "Errors": summary_stats['errors'],
            "Average Time": f"{avg_time:.2f}ms"
        }

        self.view.display_statistics(summary)
        self.view.update_status("Folder processing complete")
        self.view.update_progress(1.0)

    def get_active_constraints(self) -> Dict[str, bool]:
        """Get current active constraints from view"""
        return {
            name: var.get()
            for name, var in self.view.constraint_vars.items()
        }

    def _create_solver_settings(self):
        """Create solver selection frame"""
        self.solver_frame = customtkinter.CTkFrame(self.sidebar_frame)
        self.solver_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        solver_label = customtkinter.CTkLabel(
            self.solver_frame,
            text="Solver Settings:",
            font=customtkinter.CTkFont(size=12, weight="bold")
        )
        solver_label.pack(pady=5)
        
        # Create solver type dropdown
        self.solver_type = customtkinter.CTkOptionMenu(
            self.solver_frame,
            values=[st.value for st in WSPSolverType],
            command=self.on_solver_change
        )
        self.solver_type.pack(pady=5)
        
        # Set default solver
        self.current_solver_type = WSPSolverType.ORTOOLS_CS

    def solve(self):
        """Handle solving the current instance"""

        if not self.current_instance:
            self.view.update_status("Please select a file first")
            return
        
        try:
            # Get active constraints
            active_constraints = self.get_active_constraints()
            
            # Start solving
            self.view.update_status(f"Solving with {self.current_solver_type.value}...")
            self.view.update_progress(0.2)
            
            # Create solver using factory
            solver = self.solver_factory.create_solver(
                self.current_solver_type,
                self.current_instance,
                active_constraints
            )
            
            # Record start time
            start_time = time.time()
            
            # Solve instance
            self.current_result = solver.solve()
            
            # Record end time
            end_time = time.time()
            solve_time = end_time - start_time

            self.current_result['result_exe_time'] = solve_time * 1000  # Convert to milliseconds
            
            # Update progress
            self.view.update_progress(0.8)
            
            # Convert solution format for display
            solution = None
            if self.current_result['sat'] == 'sat':
                solution = self.current_result['sol']
            
            # Display solution
            self.view.display_solution(solution)
            
            # Get instance details
            instance_details = self.collect_instance_details()
            
            # Save metadata
            self.metadata_handler.save_result_metadata(
                instance_details=instance_details,
                solver_result=self.current_result,
                solver_type=self.current_solver_type.value,
                active_constraints=active_constraints,
                filename=os.path.basename(self.view.current_file)
            )
            
            # Display statistics
            stats = self.collect_solution_stats(solution, solve_time, active_constraints)
            stats["Solver Type"] = self.current_solver_type.value  # Add solver info to stats
            self.view.display_statistics(stats)
            
            # Update final status
            self.view.update_progress(1.0)
            status = "Solution found!" if solution else "No solution exists (UNSAT)"
            self.view.update_status(
                f"{status} using {self.current_solver_type.value} " \
                f"(solved in {solve_time:.2f} seconds)"
            )
            
        except Exception as e:
            self.view.update_status(f"Error solving: {str(e)}")
            self.view.update_progress(0)

    def collect_instance_details(self) -> Dict:
        """Collect details about the current instance"""
        if not self.current_instance:
            return {}
            
        return {
            "k": self.current_instance.number_of_steps,
            "number_of_steps": self.current_instance.number_of_steps,
            "number_of_users": self.current_instance.number_of_users,
            "number_of_constraints": self.current_instance.number_of_constraints,
            "authorization_constraints": len([u for u in self.current_instance.auth if u]),
            "separation_of_duty_constraints": len(self.current_instance.SOD),
            "binding_of_duty_constraints": len(self.current_instance.BOD),
            "at_most_k_constraints": len(self.current_instance.at_most_k),
            "one_team_constraints": len(self.current_instance.one_team),
            # Add derived metrics
            "auth_density": len([u for u in self.current_instance.auth if u]) / 
                        (self.current_instance.number_of_steps * self.current_instance.number_of_users),
            "constraint_density": self.current_instance.number_of_constraints /
                                (self.current_instance.number_of_steps * self.current_instance.number_of_users),
            "step_user_ratio": self.current_instance.number_of_steps / self.current_instance.number_of_users
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

        stats = {
            "Number of Steps": self.current_instance.number_of_steps,
            "Number of Users": self.current_instance.number_of_users,
            "Number of Constraints": self.current_instance.number_of_constraints,
            "Authorization Constraints": len([u for u in self.current_instance.auth if u]),
            "Separation of Duty Constraints": len(self.current_instance.SOD),
            "Binding of Duty Constraints": len(self.current_instance.BOD),
            "At-Most-K Constraints": len(self.current_instance.at_most_k),
            "One-Team Constraints": len(self.current_instance.one_team)
        }

        self.view.display_instance_details(stats)

    def collect_solution_stats(self, solution: Optional[List[Dict[str, int]]], 
                         solve_time: float, 
                         active_constraints: Dict[str, bool]) -> Dict:
        if not solution:
            stats = {
                "status": "unsat",
                "performance_metrics": {
                    "execution_time_ms": solve_time * 1000,
                    "solution_count": 0,
                    "is_unique": False
                }
            }
            return stats

        # Count users and assignments
        used_users = set(assignment['user'] for assignment in solution)
        assignments_per_user = {}
        for assignment in solution:
            user = assignment['user']
            assignments_per_user[user] = assignments_per_user.get(user, 0) + 1

        stats = {
            "status": "sat",
            "performance_metrics": {
                "execution_time_ms": solve_time * 1000,
                "solution_count": self.current_result.get('solution_count', 1),
                "is_unique": self.current_result.get('is_unique', False)
            },
            "solution_metrics": {
                "users_used": len(used_users),
                "user_utilization": len(used_users) / self.current_instance.number_of_users,
                "assignments_per_user": {
                    "max": max(assignments_per_user.values()),
                    "min": min(assignments_per_user.values()),
                    "avg": sum(assignments_per_user.values()) / len(used_users)
                }
            },
            "constraint_metrics": {
                "constraint_density": self.current_instance.number_of_constraints / 
                                    (self.current_instance.number_of_steps * self.current_instance.number_of_users),
                "authorization_density": len([u for u in self.current_instance.auth if u]) / 
                                    (self.current_instance.number_of_steps * self.current_instance.number_of_users),
                "constraint_distribution": {
                    "auth": len([u for u in self.current_instance.auth if u]),
                    "sod": len(self.current_instance.SOD),
                    "bod": len(self.current_instance.BOD),
                    "at_most_k": len(self.current_instance.at_most_k),
                    "one_team": len(self.current_instance.one_team)
                }
            }
        }
        return stats

    def _analyze_constraint_satisfaction(self, solution: List[Dict[str, int]], active_constraints: Dict[str, bool]) -> Dict:
        """Analyze how the solution satisfies different constraints"""
        stats = {}
        
        if active_constraints['authorizations']:
            # Check authorization violations
            violations = 0
            for assignment in solution:
                user = assignment['user'] - 1  # Convert to 0-based
                step = assignment['step'] - 1  # Convert to 0-based
                if self.current_instance.auth[user] and step not in self.current_instance.auth[user]:
                    violations += 1
            stats["Authorization Violations"] = violations
        
        if active_constraints['separation_of_duty']:
            # Check SOD violations
            violations = 0
            for s1, s2 in self.current_instance.SOD:
                user1 = next(a['user'] for a in solution if a['step'] - 1 == s1)
                user2 = next(a['user'] for a in solution if a['step'] - 1 == s2)
                if user1 == user2:
                    violations += 1
            stats["SOD Violations"] = violations
        
        if active_constraints['binding_of_duty']:
            # Check BOD violations
            violations = 0
            for s1, s2 in self.current_instance.BOD:
                user1 = next(a['user'] for a in solution if a['step'] - 1 == s1)
                user2 = next(a['user'] for a in solution if a['step'] - 1 == s2)
                if user1 != user2:
                    violations += 1
            stats["BOD Violations"] = violations
        
        if active_constraints['at_most_k']:
            # Check at-most-k violations
            violations = 0
            for k, steps in self.current_instance.at_most_k:
                users = set()
                for step in steps:
                    user = next(a['user'] for a in solution if a['step'] - 1 == step)
                    users.add(user)
                if len(users) > k:
                    violations += 1
            stats["At-Most-K Violations"] = violations
        
        if active_constraints['one_team']:
            # Check one-team violations
            violations = 0
            for steps, teams in self.current_instance.one_team:
                assigned_users = set()
                for step in steps:
                    user = next(a['user'] for a in solution if a['step'] - 1 == step)
                    assigned_users.add(user - 1)  # Convert to 0-based
                
                valid_assignment = False
                for team in teams:
                    if assigned_users.issubset(set(team)):
                        valid_assignment = True
                        break
                
                if not valid_assignment:
                    violations += 1
            stats["One-Team Violations"] = violations
        
        return stats
