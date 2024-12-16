# Import library for stack trace handling
import traceback
# Import regular expressions library
import re
# Import specialized collection types
from collections import defaultdict, Counter
# Import path handling utilities
from pathlib import Path
# Import time module with alias
import time as time_module
# Import typing hints
from typing import List

# Import solver factory for creating solver instances
from factories.solver_factory import SolverFactory
# Import file reading utilities
from filesystem import FileReader
# Import GUI components
import customtkinter
# Import utility functions
from utilities.functions import format_elapsed_time


# Main controller class for operations
class WSPController:
    # Initialize controller with view reference
    def __init__(self, view):
        self.view = view

    # Handle folder selection for test instances
    def select_folder(self):
        # Open folder dialog
        folder = customtkinter.filedialog.askdirectory(title="Select Tests Directory")
        if folder:
            # Store selected path
            self.view.tests_dir = Path(folder)
            # Update status label
            self.view.status_label.configure(text=f"Selected folder: {folder}")

    # Execute with selected settings
    def run(self):
        # Check if test directory is selected
        if not self.view.tests_dir:
            self.view.status_label.configure(text="Please select a folder of instances.")
            return

        # Get selected solvers
        solver1 = self.view.solver_menu.get()
        solver2 = self.view.second_solver_menu.get() if self.view.comparison_mode_var.get() else None

        # Validate solver selection
        if not self._validate_solver_selection(solver1, solver2):
            return

        # Collect active constraints from UI
        active_constraints = [
            name for name, switch in self.view.constraint_vars.items()
            if switch.get()
        ]

        # Clear previous results
        self.view.clear_results()
        # Set view to "All" tab
        self.view.results_notebook.set("All")
        # Update UI
        self.view.update_idletasks()

        # Process test files with selected solvers
        self._process_files(solver1, solver2, active_constraints)

    # Validate solver selections
    def _validate_solver_selection(self, solver1, solver2):
        # Check if first solver is selected
        if solver1 == "Select Solver":
            self.view.status_label.configure(text="Please select at least one solver.")
            return False

        # Additional validation for comparison mode
        if self.view.comparison_mode_var.get():
            # Check if second solver is selected
            if solver2 == "Select Solver" or solver2 is None:
                self.view.status_label.configure(text="Please select a second solver for comparison.")
                return False
            # Check if different solvers are selected
            if solver1 == solver2:
                self.view.status_label.configure(text="Please select two different solvers to compare.")
                return False

        return True

    # Process all test files
    def _process_files(self, solver1, solver2, active_constraints):
        # Initialize results collections
        comparison_results = []
        unsat_results = []
        total_solution_time = 0

        # Get sorted list of instance files
        instance_files = sorted(
            [f for f in self.view.tests_dir.iterdir()
             if (f.name.startswith('sat') or f.name.startswith('unsat')) and f.name != ".idea"],
            key=lambda x: int(re.search(r'\d+', x.stem).group() or 0)
        )

        # Process each instance file
        total_files = len(instance_files)
        for i, test_file in enumerate(instance_files):
            try:
                # Process individual file
                self._process_single_file(
                    test_file, solver1, solver2,
                    comparison_results, unsat_results, total_solution_time,
                    i, total_files, active_constraints
                )
            except Exception as e:
                print(f"Error processing {test_file.name}: {str(e)}")
                continue

        # Display final results
        self._display_results(solver1, solver2, comparison_results, unsat_results, total_solution_time)

    # Process a single instance file
    def _process_single_file(self, instance_file, solver1, solver2, comparison_results, unsat_results,
                             total_solution_time, current_index, total_files, active_constraints):
        """Process a single test file and update the results."""
        # Update status display
        self.view.status_label.configure(text=f"Processing {instance_file.name}...")
        self.view.progressbar.set((current_index + 1) / total_files)
        self.view.update()

        # Read instance file
        instance = FileReader.read_file(str(instance_file))
        self.view.current_problem = instance

        # Process first solver
        start_time1 = time_module.time()
        solver1_instance = SolverFactory.get_solver(solver1, instance, active_constraints)
        solution1 = solver1_instance.solve()
        time1 = int((time_module.time() - start_time1) * 1000)
        total_solution_time += time1

        # Single solver mode processing
        if not self.view.comparison_mode_var.get():
            if solution1:
                # Format and store satisfiable solution
                formatted_solution = self.view.format_solution(solution1)
                comparison_results.append({
                    'instance_name': instance_file.stem,
                    'solution': solution1,
                    'problem': instance,
                    'formatted_solution': formatted_solution,
                    'time': time1
                })
            else:
                # Store unsatisfiable result
                unsat_results.append({
                    'instance_name': instance_file.stem,
                    'formatted_solution': "N/A"
                })
        else:
            # Comparison mode processing
            start_time2 = time_module.time()
            solver2_instance = SolverFactory.get_solver(solver2, instance, active_constraints)
            solution2 = solver2_instance.solve()
            time2 = int((time_module.time() - start_time2) * 1000)
            total_solution_time += time2

            # Format solutions
            formatted_solution1 = self.view.format_solution(solution1) if solution1 else "N/A"
            formatted_solution2 = self.view.format_solution(solution2) if solution2 else "N/A"

            # Store results based on satisfiability
            if solution1 is None and solution2 is None:
                unsat_results.append({
                    'instance_name': instance_file.stem,
                    'formatted_solution': "N/A"
                })
            else:
                comparison_results.append({
                    'instance_name': instance_file.stem,
                    'solver1': {
                        'name': solver1,
                        'solution': solution1,
                        'formatted_solution': formatted_solution1,
                        'time': time1
                    },
                    'solver2': {
                        'name': solver2,
                        'solution': solution2,
                        'formatted_solution': formatted_solution2,
                        'time': time2
                    },
                    'problem': instance,
                    'time': time1
                })

    # Display final processing results in GUI
    def _display_results(self, solver1, solver2, comparison_results, unsat_results, total_solution_time):
        """Display the results in the GUI."""
        # Clear existing results
        for widget in self.view.all_scroll.winfo_children():
            widget.destroy()

        # Reset scroll position
        self.view.all_scroll._parent_canvas.yview_moveto(0)

        # Handle comparison mode results
        if self.view.comparison_mode_var.get():
            # Debug output
            print(f"\nProcessing comparison between {solver1} and {solver2}")
            print(f"Number of results to compare: {len(comparison_results)}")

            # Get active constraints
            active_constraints = [
                name for name, switch in self.view.constraint_vars.items()
                if switch.get()
            ]

            # Create comparison table with delay for UI responsiveness
            self.view.after(100, lambda: self.view.comparison_controller.create_comparison_table(
                comparison_results,
                active_constraints
            ))
        else:
            # Single solver mode: format results for table creation
            formatted_results = []
            for result in comparison_results:
                if isinstance(result.get('solution'), list):
                    formatted_results.append({
                        'instance_name': result['instance_name'],
                        'solution': result['solution'],
                        'problem': result['problem'],
                        'formatted_solution': result['formatted_solution']
                    })

            # Create result tables
            self.view.create_tables(formatted_results, unsat_results)

        # Update status with completion time
        formatted_final_time = format_elapsed_time(total_solution_time)
        self.view.status_label.configure(
            text=f"Completed! Processed {len(comparison_results) + len(unsat_results)} instances in {formatted_final_time}"
        )

        # Additional comparison mode processing
        if self.view.comparison_mode_var.get():
            print(f"\nProcessing comparison between {solver1} and {solver2}")
            print(f"Number of results to compare: {len(comparison_results)}")

            # Get active constraints for comparison
            active_constraints = [
                name for name, switch in self.view.constraint_vars.items()
                if switch.get()
            ]

            # Create comparison table with delay
            self.view.after(100, lambda: self.view.comparison_controller.create_comparison_table(
                comparison_results,
                active_constraints
            ))


class ComparisonController:
    def __init__(self, view):
        self.view = view

    # Toggle comparison mode UI elements
    def toggle_comparison_mode(self):
        if self.view.comparison_mode_var.get():
            # Show comparison controls
            self.view.second_solver_label.grid()
            self.view.second_solver_menu.grid()
        else:
            # Hide comparison controls
            self.view.second_solver_label.grid_remove()
            self.view.second_solver_menu.grid_remove()
