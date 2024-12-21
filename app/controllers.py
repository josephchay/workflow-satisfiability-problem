import os
from typing import Dict, List, Optional
import time
import customtkinter

from typings import Instance
from filesystem import parse_instance_file
from typings import WSPSolverType, NotEquals, AtMost, OneTeam
from stats import WSPMetadataHandler


class WSPController:
    def __init__(self, view, factory):
        self.view = view
        self.current_instance: Optional[Instance] = None
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

    @property
    def current_instance(self):
        print(f"Getting current_instance: {self._current_instance}")  # Debug print
        return self._current_instance
        
    @current_instance.setter
    def current_instance(self, value):
        print(f"Setting current_instance to: {value}")  # Debug print
        self._current_instance = value

    def on_solver_change(self, value: str):
        """Handle solver type selection change"""
        print(f"Solver change - before: instance = {self.current_instance}")  # Debug print
        self.current_solver_type = WSPSolverType(value)
        print(f"Solver change - after: instance = {self.current_instance}")  # Debug print
        self.view.update_status(f"Selected solver: {value}")

    def select_file(self):
        """Handle file selection"""
        filename = customtkinter.filedialog.askopenfilename(
            title="Select WSP Instance",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                print("Loading instance from file:", filename)  # Debug print
                instance = Instance(filename)  # Create new instance
                print("Instance created:", instance)  # Debug print
                self.current_instance = instance  # Use property setter
                print("Current instance after setting:", self.current_instance)  # Debug print
                
                # Update file label with the selected file name
                self.view.update_file_label(filename)
                self.view.update_status(f"Loaded: {filename}")

                # Display instance statistics
                self.display_instance_stats()

            except Exception as e:
                print(f"Error in select_file: {str(e)}")  # Debug print
                self.view.update_status(f"Error loading file: {str(e)}")
                self.current_instance = None  # Reset if error

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
        print("Solve method called")  # Debug print
        print(f"Current instance at start of solve: {self.current_instance}")  # Debug print
        
        if not self.current_instance:
            print("No current instance found")  # Debug print
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
            
            # Solve instance and get result
            solution = solver.solve()
            
            # Record end time
            end_time = time.time()
            solve_time = end_time - start_time
            
            # Update progress
            self.view.update_progress(0.6)
            
            # Convert solution to display format
            if solution and solution.assignment:
                display_solution = []
                for s in range(len(solution.assignment)):
                    display_solution.append({
                        'step': s + 1,
                        'user': solution.assignment[s] + 1
                    })
            else:
                display_solution = None
            
            # Update progress
            self.view.update_progress(0.8)
            
            # Display solution
            self.view.display_solution(display_solution)
            
            # Get instance details
            instance_details = {
                "number_of_steps": self.current_instance.k,
                "number_of_users": self.current_instance.n,
                "number_of_constraints": self.current_instance.m,
                "authorization_constraints": len([u for u in self.current_instance.auths if any(u.authorisation_list)]),
                "separation_of_duty_constraints": sum(1 for c in self.current_instance.cons 
                                                    if isinstance(c, NotEquals) and not c.is_bod),
                "binding_of_duty_constraints": sum(1 for c in self.current_instance.cons 
                                                    if isinstance(c, NotEquals) and c.is_bod),
                "at_most_k_constraints": sum(1 for c in self.current_instance.cons 
                                            if isinstance(c, AtMost)),
                "one_team_constraints": sum(1 for c in self.current_instance.cons 
                                            if isinstance(c, OneTeam)),
            }
            
            # Create result dictionary for metadata
            result_dict = {
                'sat': 'sat' if solution and solution.assignment else 'unsat',
                'result_exe_time': solution.time * 1000 if solution else solve_time * 1000,  # Convert to ms
                'sol': display_solution if display_solution else [],
                'solution_count': 1 if solution and solution.assignment else 0,
                'is_unique': False  # We don't track uniqueness
            }
            
            # Save metadata
            metadata_path = self.metadata_handler.save_result_metadata(
                instance_details=instance_details,
                solver_result=result_dict,
                solver_type=self.current_solver_type.value,
                active_constraints=active_constraints,
                filename=os.path.basename(self.view.current_file)
            )
            
            # Calculate and display statistics
            stats = {
                "Status": "SAT" if solution and solution.assignment else "UNSAT",
                "Solver Type": self.current_solver_type.value,
                "Solve Time": f"{solve_time:.2f} seconds",
                
                "Instance Details": {
                    "Steps": self.current_instance.k,
                    "Users": self.current_instance.n,
                    "Total Constraints": self.current_instance.m,
                    "Active Constraints": {
                        "Authorizations": active_constraints.get('authorizations', False),
                        "Separation of Duty": active_constraints.get('separation_of_duty', False),
                        "Binding of Duty": active_constraints.get('binding_of_duty', False),
                        "At-Most-K": active_constraints.get('at_most_k', False),
                        "One-Team": active_constraints.get('one_team', False)
                    }
                }
            }

            # Add solution-specific statistics if solution exists
            if solution and solution.assignment:
                # Count user assignments
                user_counts = {}
                for s in range(len(solution.assignment)):
                    user = solution.assignment[s]
                    user_counts[user] = user_counts.get(user, 0) + 1
                
                stats.update({
                    "Solution Metrics": {
                        "Unique Users Used": len(user_counts),
                        "Max Steps per User": max(user_counts.values()),
                        "Min Steps per User": min(user_counts.values()),
                        "Avg Steps per User": sum(user_counts.values()) / len(user_counts)
                    }
                })
            
            self.view.display_statistics(stats)
            
            # Update final status and progress
            self.view.update_progress(1.0)
            status = "Solution found!" if solution and solution.assignment else "No solution exists (UNSAT)"
            self.view.update_status(
                f"{status} using {self.current_solver_type.value} " \
                f"(solved in {solve_time:.2f} seconds)"
            )

        except Exception as e:
            self.view.update_status(f"Error solving: {str(e)}")
            self.view.update_progress(0)
            import traceback
            traceback.print_exc()

    def collect_instance_details(self) -> Dict:
        """Collect details about the current instance"""
        if not self.current_instance:
            return {}

        # Count different types of constraints
        sod_count = sum(1 for c in self.current_instance.cons 
                    if isinstance(c, NotEquals) and not c.is_bod)
        bod_count = sum(1 for c in self.current_instance.cons 
                    if isinstance(c, NotEquals) and c.is_bod)
        atmost_count = sum(1 for c in self.current_instance.cons 
                        if isinstance(c, AtMost))
        oneteam_count = sum(1 for c in self.current_instance.cons 
                        if isinstance(c, OneTeam))
                
        return {
            "k": self.current_instance.k,
            "number_of_steps": self.current_instance.k,
            "number_of_users": self.current_instance.n,
            "number_of_constraints": len(self.current_instance.cons),
            "authorization_constraints": len([u for u in self.current_instance.auths 
                                        if any(u.authorisation_list)]),
            "separation_of_duty_constraints": sod_count,
            "binding_of_duty_constraints": bod_count,
            "at_most_k_constraints": atmost_count,
            "one_team_constraints": oneteam_count,
            
            # Derived Metrics
            "auth_density": len([u for u in self.current_instance.auths 
                            if any(u.authorisation_list)]) / 
                        (self.current_instance.k * self.current_instance.n),
            "constraint_density": len(self.current_instance.cons) /
                                (self.current_instance.k * self.current_instance.n),
            "step_user_ratio": self.current_instance.k / self.current_instance.n
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
                                        if any(u.authorisation_list)]),
            "Separation of Duty Constraints": sod_count,
            "Binding of Duty Constraints": bod_count,
            "At-Most-K Constraints": atmost_count,
            "One-Team Constraints": oneteam_count
        }

        self.view.display_instance_details(stats)

    def collect_solution_stats(self, solution: Optional[List[Dict[str, int]]], 
                         solve_time: float, 
                         active_constraints: Dict[str, bool]) -> Dict:
        """Collect comprehensive statistics about the solution"""
        if not solution:
            return {
                "Status": "UNSAT",
                "Solver Type": self.current_solver_type.value,
                "Solve Time": f"{solve_time:.2f} seconds",
            }
        
        # Count users and assignments
        used_users = set(assignment['user'] for assignment in solution)
        assignments_per_user = {}
        for assignment in solution:
            user = assignment['user']
            assignments_per_user[user] = assignments_per_user.get(user, 0) + 1

        # Calculate densities
        auth_density = len([u for u in self.current_instance.auth if u]) / (
            self.current_instance.number_of_steps * self.current_instance.number_of_users)
        constraint_density = self.current_instance.m / (
            self.current_instance.number_of_steps * self.current_instance.number_of_users)

        stats = {
            "Status": "SAT",
            "Solver Type": self.current_solver_type.value,
            "Solve Time": f"{solve_time:.2f} seconds",
            "Number of Solutions": self.current_result.get('solution_count', 1),
            "Solution is Unique": "Yes" if self.current_result.get('is_unique', False) else "No",
            "Number of Users Used": len(used_users),
            "User Utilization": f"{(len(used_users) / self.current_instance.number_of_users * 100):.1f}%",
            "Max Assignments per User": max(assignments_per_user.values()),
            "Min Assignments per User": min(assignments_per_user.values()),
            "Avg Assignments per User": f"{sum(assignments_per_user.values()) / len(used_users):.1f}",
            
            "Instance Complexity": {
                "Steps": self.current_instance.number_of_steps,
                "Users": self.current_instance.number_of_users,
                "Total Constraints": self.current_instance.m,
                "Authorization Density": f"{auth_density:.2%}",
                "Constraint Density": f"{constraint_density:.2%}",
                "Constraint Types": {
                    "Authorization": len([u for u in self.current_instance.auth if u]),
                    "Separation of Duty": sum(1 for c in self.current_instance.cons 
                                    if isinstance(c, NotEquals) and not c.is_bod),
                    "Binding of Duty": sum(1 for c in self.current_instance.cons 
                                    if isinstance(c, NotEquals) and c.is_bod),
                    "At-Most-K": sum(1 for c in self.current_instance.cons 
                                    if isinstance(c, AtMost)),
                    "One-Team": sum(1 for c in self.current_instance.cons 
                                    if isinstance(c, OneTeam))
                }
            }
        }

        # Add constraint violations if any
        violations = self._analyze_constraint_satisfaction(solution, active_constraints)
        if violations:
            stats["Constraint Violations"] = violations

        return stats

    def _analyze_constraint_satisfaction(self, solution: List[Dict[str, int]], 
                                  active_constraints: Dict[str, bool]) -> Dict:
        """Analyze how the solution satisfies different constraints"""
        stats = {}
        
        if active_constraints['authorizations']:
            # Check authorization violations
            violations = 0
            for assignment in solution:
                user = assignment['user'] - 1  # Convert to 0-based
                step = assignment['step'] - 1  # Convert to 0-based
                if not self.current_instance.auths[user].authorisation_list[step]:
                    violations += 1
            stats["Authorization Violations"] = violations
        
        if active_constraints['separation_of_duty']:
            # Check SOD violations
            violations = 0
            for c in self.current_instance.cons:
                if isinstance(c, NotEquals) and not c.is_bod:
                    user1 = next(a['user'] for a in solution if a['step'] - 1 == c.s1)
                    user2 = next(a['user'] for a in solution if a['step'] - 1 == c.s2)
                    if user1 == user2:
                        violations += 1
            stats["SOD Violations"] = violations
        
        if active_constraints['binding_of_duty']:
            # Check BOD violations
            violations = 0
            for c in self.current_instance.cons:
                if isinstance(c, NotEquals) and c.is_bod:
                    user1 = next(a['user'] for a in solution if a['step'] - 1 == c.s1)
                    user2 = next(a['user'] for a in solution if a['step'] - 1 == c.s2)
                    if user1 != user2:
                        violations += 1
            stats["BOD Violations"] = violations
        
        if active_constraints['at_most_k']:
            # Check at-most-k violations
            violations = 0
            for c in self.current_instance.cons:
                if isinstance(c, AtMost):
                    users = set()
                    for step in c.scope:
                        user = next(a['user'] for a in solution if a['step'] - 1 == step)
                        users.add(user)
                    if len(users) > c.limit:
                        violations += 1
            stats["At-Most-K Violations"] = violations
        
        if active_constraints['one_team']:
            # Check one-team violations
            violations = 0
            for c in self.current_instance.cons:
                if isinstance(c, OneTeam):
                    assigned_users = set()
                    for step in c.steps:
                        user = next(a['user'] for a in solution if a['step'] - 1 == step)
                        assigned_users.add(user - 1)  # Convert to 0-based
                    
                    valid_assignment = False
                    for team in c.teams:
                        if assigned_users.issubset(set(team)):
                            valid_assignment = True
                            break
                    
                    if not valid_assignment:
                        violations += 1
            stats["One-Team Violations"] = violations
        
        return stats
