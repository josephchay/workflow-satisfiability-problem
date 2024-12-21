import os
from typing import List, Dict, Optional
import customtkinter
from CTkTable import CTkTable

from typings import WSPSolverType


class WSPView(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        
        # Initialize instance variables
        self.current_file = None
        self.status_label = None
        self.progressbar = None
        self.file_label = None
        self.results_table = None
        
        # Set appearance
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("blue")
        
        # Configure window
        self.title("Workflow Satisfiability Problem")
        self.geometry("1200x800")
        
        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Create main layout
        self._create_layout()
        
    def _create_layout(self):
        # Create sidebar and main frame
        self._create_sidebar()
        self._create_main_frame()

    def _create_sidebar(self):
        # Create sidebar frame
        self.sidebar_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(12, weight=1)  # Increased for solver frame

        # Create logo
        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="WSP Solver",
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Create current file label
        self.file_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="No file selected",
            wraplength=180
        )
        self.file_label.grid(row=1, column=0, padx=20, pady=5)

        # Create buttons
        self.select_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Select File",
            command=None
        )
        self.select_button.grid(row=2, column=0, padx=20, pady=10)

        # Create solver selection frame
        self._create_solver_frame()

        # Create constraints frame
        self._create_constraints_frame()

        # Create solve button
        self.solve_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Solve",
            command=None
        )
        self.solve_button.grid(row=8, column=0, padx=20, pady=10)

        # Create clear button
        self.clear_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Clear Results",
            command=self.clear_results
        )
        self.clear_button.grid(row=9, column=0, padx=20, pady=10)

    def _create_solver_frame(self):
        """Create solver selection frame"""
        self.solver_frame = customtkinter.CTkFrame(self.sidebar_frame)
        self.solver_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        # Create solver label
        solver_label = customtkinter.CTkLabel(
            self.solver_frame,
            text="Solver Selection:",
            font=customtkinter.CTkFont(size=12, weight="bold")
        )
        solver_label.pack(pady=5)
        
        # Create solver type selector
        self.solver_type = customtkinter.CTkOptionMenu(
            self.solver_frame,
            values=[st.value for st in WSPSolverType],
            command=None  # Will be set by controller
        )
        self.solver_type.pack(pady=5)
        
        # Create solver description
        self.solver_description = customtkinter.CTkLabel(
            self.solver_frame,
            text="",
            wraplength=160,
            font=customtkinter.CTkFont(size=10)
        )
        self.solver_description.pack(pady=5)

    def _create_constraints_frame(self):
        self.constraints_frame = customtkinter.CTkFrame(self.sidebar_frame)
        self.constraints_frame.grid(row=4, column=0, rowspan=2, padx=20, pady=10, sticky="ew")
        
        # Create constraints label
        constraints_label = customtkinter.CTkLabel(
            self.constraints_frame,
            text="Constraints:",
            font=customtkinter.CTkFont(size=12, weight="bold")
        )
        constraints_label.pack(pady=5)
        
        # Create constraint switches
        self.constraint_vars = {
            'authorizations': customtkinter.CTkSwitch(
                self.constraints_frame,
                text="Authorizations",
                onvalue=True, offvalue=False
            ),
            'separation_of_duty': customtkinter.CTkSwitch(
                self.constraints_frame,
                text="Separation of Duty",
                onvalue=True, offvalue=False
            ),
            'binding_of_duty': customtkinter.CTkSwitch(
                self.constraints_frame,
                text="Binding of Duty",
                onvalue=True, offvalue=False
            ),
            'at_most_k': customtkinter.CTkSwitch(
                self.constraints_frame,
                text="At-Most-K",
                onvalue=True, offvalue=False
            ),
            'one_team': customtkinter.CTkSwitch(
                self.constraints_frame,
                text="One-Team",
                onvalue=True, offvalue=False
            )
        }
        
        # Pack switches
        for switch in self.constraint_vars.values():
            switch.pack(pady=2)
            switch.select()  # Enable all constraints by default

    def update_file_label(self, filename: str):
        """Update the file label with the selected filename"""
        if filename:
            # Extract just the filename from the full path
            display_name = os.path.basename(filename)
            self.file_label.configure(text=f"Current file:\n{display_name}")
            self.current_file = filename
        else:
            self.file_label.configure(text="No file selected")
            self.current_file = None

    def _create_main_frame(self):
        # Create main frame
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Create results notebook
        self._create_results_notebook()
        self._create_progress_indicators()
    
    def _create_results_notebook(self):
        # Create tabview
        self.results_notebook = customtkinter.CTkTabview(self.main_frame)
        self.results_notebook.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Add tabs
        self.results_tab = self.results_notebook.add("Results")
        self.instance_tab = self.results_notebook.add("Instance Details")
        self.stats_tab = self.results_notebook.add("Statistics")
        
        # Configure tabs
        for tab in [self.results_tab, self.instance_tab, self.stats_tab]:
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
        
        # Create instance label for results tab
        self.results_instance_label = customtkinter.CTkLabel(
            self.results_tab,
            text="No instance loaded",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.results_instance_label.pack(pady=5)
        
        # Create scrollable frame for results
        self.results_frame = customtkinter.CTkScrollableFrame(self.results_tab)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create frames for instance details and statistics that will stretch vertically
        self.instance_frame = customtkinter.CTkFrame(self.instance_tab)
        self.instance_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.stats_frame = customtkinter.CTkFrame(self.stats_tab)
        self.stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Initialize result display variables
        self.results_table = None
        self.unsat_label = None

    def display_instance_details(self, stats: Dict):
        """Display instance details in the Instance Details tab"""
        # Clear previous content
        for widget in self.instance_frame.winfo_children():
            widget.destroy()
        
        # Create main content frame that will stretch
        content_frame = customtkinter.CTkFrame(self.instance_frame, fg_color="gray17")
        content_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Create instance details title
        title_label = customtkinter.CTkLabel(
            content_frame,
            text=f"Instance Details: {os.path.basename(self.current_file) if self.current_file else 'No instance loaded'}",
            font=customtkinter.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=10)
        
        # Display stats in table-like format
        for key, value in stats.items():
            stat_frame = customtkinter.CTkFrame(content_frame, fg_color="gray20")
            stat_frame.pack(fill="x", padx=20, pady=2)
            
            key_label = customtkinter.CTkLabel(
                stat_frame,
                text=f"{key}:",
                font=customtkinter.CTkFont(weight="bold"),
                fg_color="gray20"
            )
            key_label.pack(side="left", padx=10, pady=8)
            
            value_label = customtkinter.CTkLabel(
                stat_frame,
                text=str(value),
                fg_color="gray20"
            )
            value_label.pack(side="left", padx=5, pady=8)
        
        # Add empty frame at bottom to push content up
        spacer = customtkinter.CTkFrame(content_frame, fg_color="gray17", height=200)
        spacer.pack(fill="x", expand=True)

    def init_results_table(self):
        """Initialize or reinitialize the results table"""
        if self.results_table is not None:
            self.results_table.destroy()
        
        # Create empty table with headers
        self.results_table = CTkTable(
            master=self.table_frame,
            row=1,
            column=2,
            values=[["Step", "Assigned User"]],
            header_color="gray20",
            hover_color="gray30",
            border_width=2,
            corner_radius=10
        )
        self.results_table.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_progress_indicators(self):
        # Create progress bar
        self.progressbar = customtkinter.CTkProgressBar(self.main_frame)
        self.progressbar.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.progressbar.set(0)

        # Create status label
        self.status_label = customtkinter.CTkLabel(self.main_frame, text="Ready")
        self.status_label.grid(row=2, column=0, padx=20, pady=10)

    def update_solver_description(self, solver_type: WSPSolverType):
        """Update the solver description based on selected type"""
        descriptions = {
            WSPSolverType.ORTOOLS_CS: "Constraint Satisfaction encoding using OR-Tools",
            WSPSolverType.ORTOOLS_PBPB: "Pattern-Based Pseudo-Boolean encoding using OR-Tools",
            WSPSolverType.ORTOOLS_UDPB: "User-Dependent Pseudo-Boolean encoding using OR-Tools",
            WSPSolverType.Z3_PBPB: "Pattern-Based Pseudo-Boolean encoding using Z3",
            WSPSolverType.Z3_UDPB: "User-Dependent Pseudo-Boolean encoding using Z3",
            WSPSolverType.SAT4J_PBPB: "Pattern-Based Pseudo-Boolean encoding using SAT4J",
            WSPSolverType.SAT4J_UDPB: "User-Dependent Pseudo-Boolean encoding using SAT4J"
        }
        self.solver_description.configure(text=descriptions.get(solver_type, ""))

    def update_status(self, message: str):
        self.status_label.configure(text=message)
    
    def update_progress(self, value: float):
        self.progressbar.set(value)
    
    def display_solution(self, solution):
        """Display solution in results tab"""
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        if solution is None:
            # Display UNSAT result using label
            self.unsat_label = customtkinter.CTkLabel(
                self.results_frame,
                text="No solution exists (UNSAT)",
                font=customtkinter.CTkFont(size=14, weight="bold")
            )
            self.unsat_label.pack(pady=20)
            return

        # For SAT solutions, create table
        values = [["Step", "Assigned User"]]
        for assignment in solution:
            values.append([f"s{assignment['step']}", f"u{assignment['user']}"])
        
        self.results_table = CTkTable(
            master=self.results_frame,
            row=len(values),
            column=2,
            values=values,
            header_color="gray20",
            hover_color="gray30",
            border_width=2,
            corner_radius=10,
            width=200,
            height=40,
            padx=5,
            pady=5
        )
        self.results_table.pack(fill="both", expand=True, padx=10, pady=10)

    def display_statistics(self, stats: Dict):
        """Display enhanced solution statistics"""
        # Clear previous stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        # Create scrollable frame for content
        content_frame = customtkinter.CTkScrollableFrame(self.stats_frame, fg_color="gray17")
        content_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        def add_section_header(text: str, subtext: str = None):
            """Helper to add section headers with optional subtext"""
            header = customtkinter.CTkLabel(
                content_frame,
                text=text,
                font=customtkinter.CTkFont(size=16, weight="bold"),
                anchor="w"
            )
            header.pack(pady=(15,5), padx=10, fill="x")
            
            if subtext:
                subheader = customtkinter.CTkLabel(
                    content_frame,
                    text=subtext,
                    font=customtkinter.CTkFont(size=12),
                    text_color="gray70",
                    anchor="w"
                )
                subheader.pack(pady=(0,5), padx=20, fill="x")

        def add_metric(key: str, value: str, is_violation: bool = False, indent: bool = False):
            """Helper to add individual metrics with optional indentation"""
            frame = customtkinter.CTkFrame(content_frame, fg_color="gray20")
            frame.pack(fill="x", padx=20 + (10 if indent else 0), pady=2)
            
            # Determine text color based on violation status
            text_color = "red" if is_violation and str(value) != "0" else "white"
            
            # Format key to be more readable
            key = key.replace("_", " ").title()
            
            label = customtkinter.CTkLabel(
                frame,
                text=key + ":",
                font=customtkinter.CTkFont(weight="bold"),
                fg_color="gray20",
                text_color=text_color
            )
            label.pack(side="left", padx=10, pady=8)
            
            value_label = customtkinter.CTkLabel(
                frame,
                text=str(value),
                fg_color="gray20",
                text_color=text_color
            )
            value_label.pack(side="left", padx=5, pady=8)

        # Display general solution status
        add_section_header("Solution Status", 
                        "Overall status and performance metrics")
        add_metric("Status", stats["Status"])
        add_metric("Solver Used", stats["Solver Type"])
        add_metric("Solution Time", stats["Solve Time"])

        # Display instance details if available
        if "Instance Details" in stats:
            add_section_header("Problem Size", 
                            "Dimensions and complexity metrics")
            instance = stats["Instance Details"]
            add_metric("Total Steps", str(instance.get("Steps", "N/A")))
            add_metric("Total Users", str(instance.get("Users", "N/A")))
            add_metric("Total Constraints", str(instance.get("Total Constraints", "N/A")))
            
            if "Problem Metrics" in instance:
                metrics = instance["Problem Metrics"]
                add_metric("Authorization Density", f"{metrics.get('Auth Density', 0):.2%}")
                add_metric("Constraint Density", f"{metrics.get('Constraint Density', 0):.2%}")
                add_metric("Step-User Ratio", f"{metrics.get('Step-User Ratio', 0):.2f}")

        # Display workload distribution
        if "Solution Metrics" in stats:
            add_section_header("Workload Distribution", 
                            "How work is distributed among users")
            metrics = stats["Solution Metrics"]
            add_metric("Active Users", f"{metrics['unique_users']} of {instance.get('Users', 'N/A')}")
            add_metric("Maximum Assignment", f"{metrics['max_steps_per_user']} steps")
            add_metric("Minimum Assignment", f"{metrics['min_steps_per_user']} steps")
            add_metric("Average Assignment", f"{metrics['avg_steps_per_user']:.1f} steps")
            
            # Calculate and show utilization
            if 'Users' in instance:
                utilization = (metrics['unique_users'] / instance['Users']) * 100
                add_metric("User Utilization", f"{utilization:.1f}%")

        # Display constraint information and violations
        add_section_header("Constraint Compliance", 
                        "Verification of all constraint types")
        
        # Standard constraint types to always show
        constraint_types = [
            "Authorization",
            "Separation of Duty",
            "Binding of Duty",
            "At Most K",
            "One Team"
        ]
        
        violations = stats.get("Constraint Violations", {})
        total_violations = sum(violations.values())
        
        if total_violations == 0:
            # Show perfect solution indicator
            frame = customtkinter.CTkFrame(content_frame, fg_color="gray20")
            frame.pack(fill="x", padx=20, pady=10)
            
            label = customtkinter.CTkLabel(
                frame,
                text="✓ Perfect Solution - All Constraints Satisfied",
                font=customtkinter.CTkFont(weight="bold", size=14),
                fg_color="gray20",
                text_color="lime"
            )
            label.pack(pady=10)
            
            # Still show all constraints with 0 violations
            for constraint in constraint_types:
                add_metric(f"{constraint} Violations", "0", is_violation=False, indent=True)
        else:
            # Show all constraints, including those with 0 violations
            for constraint in constraint_types:
                value = violations.get(constraint, 0)
                add_metric(f"{constraint} Violations", str(value), 
                        is_violation=True, indent=True)
            
            # Add total violations at the end
            add_metric("Total Violations", str(total_violations), 
                    is_violation=True)

        if "Instance Details" in stats and "Constraint Distribution" in stats["Instance Details"]:
            add_section_header("Constraint Distribution", 
                            "Number of constraints by type")
            for constraint, count in stats["Instance Details"]["Constraint Distribution"].items():
                add_metric(constraint, str(count))

    def add_visualization_button(self, command):
        """Add a button to generate visualizations"""
        self.visualize_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Generate Visualizations",
            command=command
        )
        self.visualize_button.grid(row=10, column=0, padx=20, pady=10)

    def clear_results(self):
        # Clear all widgets in results frame
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Clear stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        # Do not clear file label
        
        # Reset progress and status
        self.progressbar.set(0)
        self.status_label.configure(text="Ready")
