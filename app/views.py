import os
from typing import Dict, Optional
import customtkinter
from CTkTable import CTkTable

from constants import SolverType


class AppView(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        
        # Initialize instance variables
        self.current_file = None
        self.status_label = None
        self.progressbar = None
        self.file_label = None
        self.results_table = None
        self.solver_type = None  # Will be initialized in create_solver_frame
        self.solver_description = None  # Will be initialized in create_solver_frame
        
        # Set appearance
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("blue")
        
        # Configure window
        self.title("Workflow Satisfiability Problem Solver")
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
        # Create sidebar frame with fixed width
        self.sidebar_frame = customtkinter.CTkFrame(
            self, 
            width=240,
            corner_radius=0
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(12, weight=1)
        
        # Prevent sidebar from expanding
        self.sidebar_frame.grid_propagate(False)

        # Create logo label
        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="WSP Solver",
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Create file label
        self.file_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="No file selected",
            wraplength=220
        )
        self.file_label.grid(row=1, column=0, padx=20, pady=5)

        # Create buttons
        self.select_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Select File",
            width=220
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
            width=220
        )
        self.solve_button.grid(row=8, column=0, padx=20, pady=10)

        # Create clear button
        self.clear_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Clear Results",
            command=self.clear_results,
            width=220
        )
        self.clear_button.grid(row=9, column=0, padx=20, pady=10)

        # Generate Visualizations button
        self.visualize_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Generate Visualizations",
            command=self.visualize,
            width=220
        )

    def _create_solver_frame(self):
        """Create solver selection frame"""
        self.solver_frame = customtkinter.CTkFrame(self.sidebar_frame)
        self.solver_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        # Create solver label
        solver_label = customtkinter.CTkLabel(
            self.solver_frame,
            text="Solver Selection:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        solver_label.pack(pady=5)
        
        # Create solver type selector with fixed width
        self.solver_type = customtkinter.CTkOptionMenu(
            self.solver_frame,
            values=[st.value for st in SolverType],
            command=None,  # Will be set by controller
            width=220
        )
        self.solver_type.pack(pady=5)
        
        # Create solver description label
        self.solver_description = customtkinter.CTkLabel(
            self.solver_frame,
            text="",
            wraplength=220,  # Increased wraplength
            font=customtkinter.CTkFont(size=12)
        )
        self.solver_description.pack(pady=5)

    def update_solver_description(self, description: str):
        """Update solver description text"""
        if self.solver_description:
            self.solver_description.configure(text=description)

    def _create_constraints_frame(self):
        """Create constraints frame with increased width"""
        self.constraints_frame = customtkinter.CTkFrame(self.sidebar_frame)
        self.constraints_frame.grid(row=4, column=0, rowspan=2, padx=20, pady=10, sticky="ew")
        
        # Create constraints label
        constraints_label = customtkinter.CTkLabel(
            self.constraints_frame,
            text="Active Constraints:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        constraints_label.pack(pady=5)
        
        # Create constraint switches with increased width
        self.constraint_vars = {}
        constraints = [
            ('authorizations', "Authorizations"),
            ('separation_of_duty', "Separation of Duty"),
            ('binding_of_duty', "Binding of Duty"),
            ('at_most_k', "At-Most-K"),
            ('one_team', "One-Team")
        ]
        
        for key, text in constraints:
            frame = customtkinter.CTkFrame(self.constraints_frame, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=2)
            
            self.constraint_vars[key] = customtkinter.CTkSwitch(
                frame,
                text=text,
                onvalue=True,
                offvalue=False,
                width=40  # Fixed switch width
            )
            self.constraint_vars[key].pack(side="left", padx=10)
            self.constraint_vars[key].select()  # Enable by default

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
        
        # Create frames
        self.results_frame = customtkinter.CTkScrollableFrame(self.results_tab)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.instance_frame = customtkinter.CTkFrame(self.instance_tab)
        self.instance_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.stats_frame = customtkinter.CTkFrame(self.stats_tab)
        self.stats_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_progress_indicators(self):
        # Create progress bar
        self.progressbar = customtkinter.CTkProgressBar(self.main_frame)
        self.progressbar.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.progressbar.set(0)

        # Create status label
        self.status_label = customtkinter.CTkLabel(self.main_frame, text="Ready")
        self.status_label.grid(row=2, column=0, padx=20, pady=10)

    def get_file_selection(self) -> Optional[str]:
        """Get file selection from user"""
        return customtkinter.filedialog.askopenfilename(
            title="Select WSP Instance",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

    def update_file_label(self, filename: str):
        """Update file label with selected filename"""
        if filename:
            display_name = os.path.basename(filename)
            self.file_label.configure(text=f"Current file:\n{display_name}")
            self.current_file = filename
        else:
            self.file_label.configure(text="No file selected")
            self.current_file = None

    def update_status(self, message: str):
        """Update status message"""
        self.status_label.configure(text=message)
    
    def update_progress(self, value: float):
        """Update progress bar"""
        self.progressbar.set(value)

    def display_solution(self, solution):
        """Display solution in results tab"""
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        if solution is None:
            # Display UNSAT result
            label = customtkinter.CTkLabel(
                self.results_frame,
                text="No solution exists (UNSAT)",
                font=customtkinter.CTkFont(size=14, weight="bold")
            )
            label.pack(pady=20)
            return

        # Create solution table
        values = [["Step", "Assigned User"]]
        for assignment in solution:
            values.append([
                f"s{assignment['step']}", 
                f"u{assignment['user']}"
            ])
        
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

    def display_instance_details(self, stats: Dict):
        """Display instance details in enhanced format"""
        # Clear previous content
        for widget in self.instance_frame.winfo_children():
            widget.destroy()

        content_frame = customtkinter.CTkScrollableFrame(
            self.instance_frame,
            fg_color="gray17"
        )
        content_frame.pack(fill="both", expand=True, padx=2, pady=2)

        def add_section(title: str, data: Dict):
            # Create section header
            header = customtkinter.CTkLabel(
                content_frame,
                text=title,
                font=customtkinter.CTkFont(size=16, weight="bold")
            )
            header.pack(pady=(15,5), padx=10)

            # Create metrics frame
            metrics_frame = customtkinter.CTkFrame(content_frame)
            metrics_frame.pack(fill="x", padx=20, pady=5)

            # Add metrics
            for key, value in data.items():
                if isinstance(value, dict):
                    add_section(f"{key} Details", value)
                else:
                    metric_frame = customtkinter.CTkFrame(metrics_frame)
                    metric_frame.pack(fill="x", pady=2)
                    
                    label = customtkinter.CTkLabel(
                        metric_frame,
                        text=f"{key}:",
                        font=customtkinter.CTkFont(weight="bold")
                    )
                    label.pack(side="left", padx=10)
                    
                    value_label = customtkinter.CTkLabel(
                        metric_frame,
                        text=str(value)
                    )
                    value_label.pack(side="left", padx=5)

        # Add main sections
        add_section("Instance Overview", {
            "Steps": stats.get("Steps", "N/A"),
            "Users": stats.get("Users", "N/A")
        })

        if "Constraints" in stats:
            add_section("Constraints", stats["Constraints"])

    def display_statistics(self, stats: Dict):
        """Display solving statistics"""
        # Clear previous stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        content_frame = customtkinter.CTkScrollableFrame(
            self.stats_frame,
            fg_color="gray17"
        )
        content_frame.pack(fill="both", expand=True, padx=2, pady=2)

        def add_stat_section(title: str, stats_dict: Dict):
            section_frame = customtkinter.CTkFrame(content_frame)
            section_frame.pack(fill="x", padx=10, pady=5)

            header = customtkinter.CTkLabel(
                section_frame,
                text=title,
                font=customtkinter.CTkFont(size=14, weight="bold")
            )
            header.pack(pady=5)

            for key, value in stats_dict.items():
                if isinstance(value, dict):
                    add_stat_section(key, value)
                else:
                    stat_frame = customtkinter.CTkFrame(section_frame)
                    stat_frame.pack(fill="x", pady=2)
                    
                    label = customtkinter.CTkLabel(
                        stat_frame,
                        text=f"{key}:",
                        font=customtkinter.CTkFont(weight="bold")
                    )
                    label.pack(side="left", padx=10)
                    
                    value_label = customtkinter.CTkLabel(
                        stat_frame,
                        text=str(value)
                    )
                    value_label.pack(side="left", padx=5)

        # Add main statistic sections
        if "solver_metrics" in stats:
            add_stat_section("Solver Performance", stats["solver_metrics"])
        
        if "solution_metrics" in stats:
            add_stat_section("Solution Metrics", stats["solution_metrics"])
            
        if "violations" in stats:
            add_stat_section("Constraint Violations", {"violations": stats["violations"]})

    def clear_results(self):
        """Clear all results and reset display"""
        # Clear results tab
        for widget in self.results_frame.winfo_children():
            widget.destroy()
            
        # Clear instance details
        for widget in self.instance_frame.winfo_children():
            widget.destroy()
            
        # Clear statistics
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
            
        # Reset progress and status
        self.progressbar.set(0)
        self.status_label.configure(text="Ready")
        
        # Update instance label
        self.results_instance_label.configure(text="No instance loaded")

    def visualize(self):
        """Generate visualizations"""
        pass