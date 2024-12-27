import os
import traceback
import matplotlib.pyplot as plt
from typing import Dict, Optional
import traceback

from constants import SolverType
from typings import Instance
from filesystem import InstanceParser
from stats import MetadataHandler, Visualizer


class AppController:
    def __init__(self, view, solver_factory):
        self.view = view
        self.current_instance: Optional[Instance] = None
        self.current_solver_type = SolverType.ORTOOLS_CP  # Default solver
        self.solver_factory = solver_factory
        
        # Connect button callbacks
        self.view.select_button.configure(command=self.select_file)
        self.view.solve_button.configure(command=self.solve)
        self.view.visualize_button.configure(command=self.visualize)
        self.view.clear_viz_button.configure(command=self.clear_visualization_cache)
        
        # self.view.generate_plots_button.configure(command=self.generate_plots)

        # Initialize statistics handlers
        self.metadata_handler = MetadataHandler(output_dir="results/metadata")
        self.visualizer = Visualizer(self.metadata_handler, output_dir="results/plots", gui_mode=True)

        # Track solved instances
        self.solved_instances = []
        self.update_visualization_status()

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
            SolverType.ORTOOLS_CP: "OR-Tools (Boolean-based)",
            SolverType.Z_THREE: "Z3 Theorem Prover (Constraint-based)",
            SolverType.SAT4J: "SAT4J - Boolean-based & Pigeon-hole principle",
            SolverType.GUROBI: "Gurobi (Integer-based & Array-based & MIP-based)",
            SolverType.PULP: "PuLP (Integer-based & LP-based & CBC-based)",
            SolverType.SA: "Simulated Annealing (Stochastic Metaheuristic algorithm)",
            SolverType.DEAP: "DEAP (Evolutionary Genetic algorithm)",
            SolverType.BAYESIAN_NETWORK: "Bayesian Network (Probabilistic Graphical Model-based)",
        }
        description = descriptions.get(self.current_solver_type, "")
        self.view.update_solver_description(description)

    def select_file(self):
        """Handle file selection"""
        file = self.view.get_file_selection()
        
        if file:
            try:
                instance = InstanceParser.parse_file(file)
                self.current_instance = instance
                self.view.update_file_label(file)
                filename = os.path.basename(file)
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
            active_constraints = self.get_active_constraints()
            self.view.update_status(f"Solving with {self.current_solver_type.value}...")
            self.view.update_progress(0.1)

            solver = self.solver_factory.create_solver(
                self.current_solver_type,
                self.current_instance,
                active_constraints,
                gui_mode=True
            )

            result = solver.solve()

            self.view.update_progress(0.6)

            # Format solver results
            solver_results = {
                'sat': 'sat' if result.is_sat else 'unsat',
                'sol': self._format_solution(result) if result.is_sat else None,
                'exe_time': solver.solve_time * 1000,
                'violations': result.violations if hasattr(result, 'violations') else [],
                'is_unique': solver.solution_unique if hasattr(solver, 'solution_unique') else None
            }
            
            # Save metadata regardless of SAT/UNSAT
            filename = os.path.basename(self.view.current_file)
            self.metadata_handler.save(
                instance_details={
                    **solver.statistics["problem_size"],
                    'Authorization': solver.statistics["constraint_distribution"]["Authorization"],
                    'Separation Of Duty': solver.statistics["constraint_distribution"]["Separation Of Duty"],
                    'Binding Of Duty': solver.statistics["constraint_distribution"]["Binding Of Duty"],
                    'At Most K': solver.statistics["constraint_distribution"]["At Most K"],
                    'One Team': solver.statistics["constraint_distribution"]["One Team"],
                    'Super User At Least': solver.statistics["constraint_distribution"]["Super User At Least"],
                    'Wang Li': solver.statistics["constraint_distribution"]["Wang Li"],
                    'Assignment Dependent': solver.statistics["constraint_distribution"]["Assignment Dependent"]
                },
                solver_result=solver_results,
                solver_type=self.current_solver_type.value,
                active_constraints=active_constraints,
                filename=filename
            )
            
            # Track solved instance
            if filename not in self.solved_instances:
                self.solved_instances.append(filename)
                self.update_visualization_status()

            if result.is_sat:
                self.view.display_solution(solver_results['sol'])
                status = "Solution found!"
            else:
                self.view.display_solution(None)
                status = "No solution exists (UNSAT)"
                
            self.view.display_statistics(solver.statistics)
                
            self.view.results_instance_label.configure(
                text=f"Instance: {filename}"
            )

            self.view.update_progress(1.0)
            self.view.update_status(f"{status} using {self.current_solver_type.value}")

        except Exception as e:
            self.view.update_status(f"Error solving: {str(e)}")
            self.view.update_progress(0)
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
            "Basic Metrics": {
                "Total Steps": instance.number_of_steps,
                "Total Users": instance.number_of_users,
                "Total Constraints": instance.number_of_constraints
            },
            "Constraint Distribution": {
                "Authorization": len([u for u in instance.auth if u]),
                "Separation of Duty": len(instance.SOD),
                "Binding of Duty": len(instance.BOD),
                "At-most-k": len(instance.at_most_k),
                "One-team": len(getattr(instance, 'one_team', []))
            }
        }
        self.view.display_instance_details(stats)

    def visualize(self):
        """Handle visualization generation"""
        if not self.solved_instances:
            self.view.update_status("No solved instances to visualize")
            return
            
        try:
            self.view.update_status("Generating visualizations...")
            self.view.update_progress(0.1)
            
            # Get comparison data
            comparison_data = self.metadata_handler.get_comparison_data(
                self.solved_instances
            )
            
            # Generate plots with cleanup
            try:
                plt.close('all')  # Clean up any existing plots
                self.visualizer.visualize(data=comparison_data)
                
                # plots_dir = os.path.abspath(self.visualizer.output_dir)
                plots_dir = self.visualizer.output_dir
                self.view.update_status(
                    f"Generated visualizations saved to: {plots_dir}"
                )
                self.view.update_progress(1.0)
                
            except Exception as e:
                self.view.update_status(f"Error in visualization: {str(e)}")
                self.view.update_progress(0)
            finally:
                plt.close('all')
                
        except Exception as e:
            self.view.update_status(f"Error accessing data: {str(e)}")
            self.view.update_progress(0)
        
    def clear_visualization_cache(self):
        """Clean up before clearing cache"""
        try:
            plt.close('all')  # Clean up any open plots
            self.solved_instances = []
            self.update_visualization_status()
            self.view.update_status("Visualization cache cleared")
        except Exception as e:
            self.view.update_status(f"Error clearing cache: {str(e)}")
        finally:
            plt.close('all')
        
    def update_visualization_status(self):
        """Update visualization status in view"""
        self.view.update_viz_status(len(self.solved_instances))

    def generate_plots(self):
        """Generate all plots without opening directory"""
        if not self.solved_instances:
            self.view.update_status("No solved instances to visualize")
            return
            
        try:
            self.view.update_status("Generating plots...")
            self.view.update_progress(0.1)
            
            # Get comparison data
            comparison_data = self.metadata_handler.get_comparison_data(
                self.solved_instances
            )
            
            # Generate plots
            try:
                plt.close('all')  # Clean up any existing plots
                self.visualizer.generate_all_plots(comparison_data)
                
                self.view.update_status(
                    f"Successfully generated plots for {len(self.solved_instances)} instances"
                )
                
                # Switch to plots tab
                self.view.results_notebook.set("Plots")
                
            except Exception as e:
                self.view.update_status(f"Error in visualization: {str(e)}")
                traceback.print_exc()
            finally:
                plt.close('all')
                
        except Exception as e:
            self.view.update_status(f"Error accessing data: {str(e)}")
            traceback.print_exc()
        finally:
            self.view.update_progress(1.0)
