import os
import time
from typing import Dict, Optional

from constants import SolverType
from typings import Instance
from filesystem import InstanceParser
from stats import MetadataHandler


class AppController:
    def __init__(self, view, solver_factory):
        self.view = view
        self.current_instance: Optional[Instance] = None
        self.current_solver_type = SolverType.ORTOOLS_CP  # Default solver
        self.solver_factory = solver_factory
        
        # Connect button callbacks
        self.view.select_button.configure(command=self.select_file)
        self.view.solve_button.configure(command=self.solve)
        
        # Initialize metadata handler
        self.metadata_handler = MetadataHandler()
        
        # Add visualization button to view
        self.view.add_visualization_button(self.generate_visualizations)

        # Initialize solver descriptions
        self._update_solver_description()

    def on_solver_change(self, value: str):
        """Handle solver type selection change"""
        self.current_solver_type = SolverType(value)
        self._update_solver_description()
        self.view.update_status(f"Selected solver: {value}")

    def _update_solver_description(self):
        """Update the solver description based on current type"""
        descriptions = {
            SolverType.ORTOOLS_CP: "Constraint Programming encoding using OR-Tools",
            SolverType.ORTOOLS_CS: "Constraint Satisfaction encoding using OR-Tools",
            SolverType.ORTOOLS_PBPB: "Pattern-Based Pseudo-Boolean encoding using OR-Tools",
            SolverType.ORTOOLS_UDPB: "User-Dependent Pseudo-Boolean encoding using OR-Tools",
            SolverType.Z3_PBPB: "Pattern-Based Pseudo-Boolean encoding using Z3",
            SolverType.Z3_UDPB: "User-Dependent Pseudo-Boolean encoding using Z3",
            SolverType.SAT4J_PBPB: "Pattern-Based Pseudo-Boolean encoding using SAT4J",
            SolverType.SAT4J_UDPB: "User-Dependent Pseudo-Boolean encoding using SAT4J"
        }
        description = descriptions.get(self.current_solver_type, "")
        self.view.update_solver_description(description)

    def select_file(self):
        """Handle file selection"""
        filename = self.view.get_file_selection()
        
        if filename:
            try:
                instance = InstanceParser.parse_file(filename)
                self.current_instance = instance
                self.view.update_file_label(filename)
                self.view.update_status(f"File loaded: {filename}")
                
                # Display instance details
                self._display_instance_info(instance)

            except Exception as e:
                self.view.update_status(f"Error loading file: {str(e)}")
                self.current_instance = None

    def solve(self):
        """Handle solving the current instance"""
        if not self.current_instance:
            self.view.update_status("Please select a file first")
            return
        
        try:
            # Get active constraints
            active_constraints = self.get_active_constraints()
            self.view.update_status(f"Solving with {self.current_solver_type.value}...")
            self.view.update_progress(0.1)

            # Collect instance metrics
            instance_metrics = self._collect_instance_metrics()
            self.view.update_progress(0.2)

            # Create solver using factory
            solver = self.solver_factory.create_solver(
                self.current_solver_type,
                self.current_instance,
                active_constraints
            )
            
            # Run solver
            start_time = time.time()
            result = solver.solve()
            solve_time = time.time() - start_time
            
            self.view.update_progress(0.6)

            # Process solution
            if result.is_sat:
                solution = self._format_solution(result)
                stats = self._collect_solution_stats(result, solve_time)
                
                # Save metadata
                self.metadata_handler.save_result_metadata(
                    instance_details=instance_metrics,
                    solver_result=stats,
                    solver_type=self.current_solver_type.value,
                    active_constraints=active_constraints,
                    filename=os.path.basename(self.view.current_file)
                )
                
                # Display results
                self.view.display_solution(solution)
                self.view.display_statistics(stats)
                status = "Solution found!"
                
            else:
                self.view.display_solution(None)
                status = f"No solution exists (UNSAT): {result.reason}"
                
            self.view.update_progress(1.0)
            self.view.update_status(
                f"{status} using {self.current_solver_type.value} "
                f"(solved in {solve_time:.2f}s)"
            )

        except Exception as e:
            self.view.update_status(f"Error solving: {str(e)}")
            self.view.update_progress(0)
            import traceback
            traceback.print_exc()

    def get_active_constraints(self) -> Dict[str, bool]:
        """Get current active constraints from view"""
        return {
            name: var.get()
            for name, var in self.view.constraint_vars.items()
        }

    def _collect_instance_metrics(self) -> Dict:
        """Collect metrics about current instance"""
        if not self.current_instance:
            return {}

        instance = self.current_instance
        constraint_counts = {
            "authorization": len([u for u in instance.auth if u]),
            "separation_of_duty": len(instance.SOD),
            "binding_of_duty": len(instance.BOD),
            "at_most_k": len(instance.at_most_k),
            "one_team": len(instance.one_team)
        }
        
        return {
            "Steps": instance.number_of_steps,
            "Users": instance.number_of_users,
            "Total Constraints": sum(constraint_counts.values()),
            "Constraint Distribution": constraint_counts,
            "Problem Metrics": {
                "Auth Density": (constraint_counts["authorization"] / 
                               (instance.number_of_steps * instance.number_of_users)),
                "Step-User Ratio": instance.number_of_steps / instance.number_of_users
            }
        }

    def _format_solution(self, result):
        """Format solver result for display"""
        return [
            {'step': step, 'user': user}
            for step, user in result.assignment.items()
        ]

    def _collect_solution_stats(self, result, solve_time):
        """Collect comprehensive solution statistics"""
        return {
            "sat": "sat",
            "result_exe_time": solve_time * 1000,
            "sol": self._format_solution(result),
            "violations": result.violations
        }

    def _display_instance_info(self, instance):
        """Display loaded instance information"""
        stats = {
            "Steps": instance.number_of_steps,
            "Users": instance.number_of_users,
            "Constraints": {
                "Authorization": len([u for u in instance.auth if u]),
                "Separation of Duty": len(instance.SOD),
                "Binding of Duty": len(instance.BOD),
                "At-most-k": len(instance.at_most_k),
                "One-team": len(instance.one_team)
            }
        }
        self.view.display_instance_details(stats)

    def generate_visualizations(self):
        """Generate visualizations from saved metadata"""
        try:
            self.view.update_status("Generating visualizations...")
            self.metadata_handler.generate_visualizations()
            self.view.update_status("Visualizations generated!")
        except Exception as e:
            self.view.update_status(f"Error generating visualizations: {str(e)}")
