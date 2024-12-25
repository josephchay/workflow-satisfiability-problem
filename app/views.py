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
        """Create scrollable sidebar with all controls"""
        # Create outer sidebar frame
        self.sidebar_frame = customtkinter.CTkFrame(
            self, 
            width=210,
            corner_radius=0
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        # Make sidebar frame non-expandable
        self.sidebar_frame.grid_propagate(False)
        
        # Create scrollable frame for entire sidebar
        self.sidebar_scrollable = customtkinter.CTkScrollableFrame(
            self.sidebar_frame,
            width=190,
            corner_radius=0,
            fg_color="transparent"
        )
        self.sidebar_scrollable.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure outer frame to expand scrollable
        self.sidebar_frame.grid_rowconfigure(0, weight=1)
        self.sidebar_frame.grid_columnconfigure(0, weight=1)

        # 1. Header Section
        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_scrollable,
            text="WSP Solver",
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.logo_label.pack(pady=(20, 10))

        # 2. File Selection Section
        self.file_label = customtkinter.CTkLabel(
            self.sidebar_scrollable,
            text="No file selected",
            wraplength=180
        )
        self.file_label.pack(pady=5)

        self.select_button = customtkinter.CTkButton(
            self.sidebar_scrollable,
            text="Select File",
            width=180
        )
        self.select_button.pack(pady=10)

        # 3. Solver Selection Section
        solver_label = customtkinter.CTkLabel(
            self.sidebar_scrollable,
            text="Solver Selection:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        solver_label.pack(pady=(10, 5))
        
        self.solver_type = customtkinter.CTkOptionMenu(
            self.sidebar_scrollable,
            values=[st.value for st in SolverType],
            command=None,
            width=180
        )
        self.solver_type.pack(pady=5)
        
        self.solver_description = customtkinter.CTkLabel(
            self.sidebar_scrollable,
            text="",
            wraplength=180,
            font=customtkinter.CTkFont(size=12)
        )
        self.solver_description.pack(pady=5)

        # 4. Constraints Section
        constraints_label = customtkinter.CTkLabel(
            self.sidebar_scrollable,
            text="Active Constraints:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        constraints_label.pack(pady=(10, 5))
        
        self.constraint_vars = {}
        constraints = [
            ('authorizations', "Authorizations"),
            ('separation_of_duty', "SOD"),
            ('binding_of_duty', "BOD"),
            ('at_most_k', "At-Most-K"),
            ('one_team', "One-Team"),
            ('super_user_at_least', "SUAL"),
            ('wang_li', "Wang-Li"),
            ('assignment_dependent', "Asgn-Dependent")
        ]
        
        for key, text in constraints:
            frame = customtkinter.CTkFrame(self.sidebar_scrollable, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=2)
            
            self.constraint_vars[key] = customtkinter.CTkSwitch(
                frame,
                text=text,
                onvalue=True,
                offvalue=False,
                width=40
            )
            self.constraint_vars[key].pack(side="left", padx=10)
            self.constraint_vars[key].select()

        # 5. Solve Buttons Section
        self.solve_button = customtkinter.CTkButton(
            self.sidebar_scrollable,
            text="Solve",
            width=180
        )
        self.solve_button.pack(pady=(20, 10))

        self.clear_button = customtkinter.CTkButton(
            self.sidebar_scrollable,
            text="Clear Results",
            width=180
        )
        self.clear_button.pack(pady=10)

        # 6. Visualization Section
        viz_label = customtkinter.CTkLabel(
            self.sidebar_scrollable,
            text="Visualization Controls:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        viz_label.pack(pady=(20, 5))
        
        self.visualize_button = customtkinter.CTkButton(
            self.sidebar_scrollable,
            text="Generate Plots",
            width=180
        )
        self.visualize_button.pack(pady=5)
        
        self.clear_viz_button = customtkinter.CTkButton(
            self.sidebar_scrollable,
            text="Clear Plot Cache",
            width=180
        )
        self.clear_viz_button.pack(pady=5)
        
        self.viz_status_label = customtkinter.CTkLabel(
            self.sidebar_scrollable,
            text="No instances in cache",
            wraplength=160
        )
        self.viz_status_label.pack(pady=(5, 20))

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
            width=180
        )
        self.solver_type.pack(pady=5)
        
        # Create solver description label
        self.solver_description = customtkinter.CTkLabel(
            self.solver_frame,
            text="",
            wraplength=180,  # Increased wraplength
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
        
        # Create constraint switches
        self.constraint_vars = {}
        constraints = [
            ('authorizations', "Authorizations"),
            ('separation_of_duty', "Separation of Duty"),
            ('binding_of_duty', "Binding of Duty"),
            ('at_most_k', "At-Most-K"),
            ('one_team', "One-Team"),
            ('super_user_at_least', "SUAL"),
            ('wang_li', "Wang-Li"),
            ('assignment_dependent', "Asgn-Dependent")
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
        self.plots_tab = self.results_notebook.add("Plots")
        
        # Configure tabs
        for tab in [self.results_tab, self.instance_tab, self.stats_tab, self.plots_tab]:
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)

        # Create instance label for results tab
        self.results_instance_label = customtkinter.CTkLabel(
            self.results_tab,
            text="No instance loaded",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.results_instance_label.pack(pady=5)
        
        # Create scrollable frames
        self.results_frame = customtkinter.CTkScrollableFrame(self.results_tab)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.instance_frame = customtkinter.CTkScrollableFrame(self.instance_tab)
        self.instance_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.stats_frame = customtkinter.CTkScrollableFrame(self.stats_tab)
        self.stats_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Setup plots tab
        self._setup_plots_tab()

    def _setup_plots_tab(self):
        plots_frame = customtkinter.CTkScrollableFrame(self.plots_tab)
        plots_frame.pack(fill="both", expand=True, padx=10, pady=10)

        title = customtkinter.CTkLabel(
            plots_frame,
            text="Available Plots",
            font=customtkinter.CTkFont(size=16, weight="bold")
        )
        title.pack(pady=10)

        plot_types = [
            ("Solving Times", "solving_times.png", "View solving time comparison across instances"),
            ("Problem Sizes", "problem_sizes.png", "Compare instance sizes and complexity"), 
            ("Constraint Distribution", "constraint_distribution.png", "View constraint type distribution"),
            ("Constraint Comparison", "constraint_comparison.png", "Compare all the different types of constraints"),
            ("Constraint Complexity", "constraint_complexity.png", "View complexity of each constraint type"),
            ("Solution Statistics", "solution_stats.png", "Compare solution characteristics"),
            ("Correlation Matrix", "correlations.png", "View relationships between metrics"),
            ("Efficiency Metrics", "efficiency.png", "Compare solver efficiency metrics"),
            ("Instance Statistics", "instance_stats.png", "View comprehensive instance statistics"),
            ("Step Authorizations", "step_authorizations.png", "View step authorization distribution"),
            ("User Authorizations", "user_authorizations.png", "View user authorization distribution"),
            ("Authorization Density", "auth_density.png", "View authorization density metrics"),
            ("Workload Distribution", "workload_distribution.png", "View workload distribution among users"),
            ("Constraint Compliance", "constraint_compliance.png", "View constraint compliance metrics"),
        ]

        for title, filename, description in plot_types:
            frame = customtkinter.CTkFrame(plots_frame, fg_color="transparent")
            frame.pack(fill="x", padx=5, pady=5)

            button = customtkinter.CTkButton(
                frame,
                text=title,
                command=lambda f=filename: self.open_plot(f)
            )
            button.pack(side="left", padx=5)

            desc_label = customtkinter.CTkLabel(
                frame,
                text=description,
                wraplength=300
            )
            desc_label.pack(side="left", padx=5)

            # # Add generate all plots button
            # self.generate_plots_button = customtkinter.CTkButton(
            #     plots_frame,
            #     text="Generate All Plots",
            #     command=None  # Will be set by controller
            # )
            # self.generate_plots_button.pack(pady=10)

    def open_plot(self, filename):
        """Open a plot image in the default image viewer"""
        filepath = os.path.join("results/plots", filename)
        if os.path.exists(filepath):
            if os.name == 'nt':  # Windows
                os.startfile(filepath)
            else:  # Linux/Mac
                os.system(f'xdg-open "{filepath}"')
        else:
            self.update_status("Plot not yet generated. Please generate plots first.")

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
        """Display instance details with enhanced formatting"""
        # Clear previous content
        for widget in self.instance_frame.winfo_children():
            widget.destroy()

        content_frame = customtkinter.CTkFrame(
            self.instance_frame,
            fg_color="gray17"
        )
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        def create_section(title: str, description: str = ""):
            """Create a section with title and optional description"""
            section_frame = customtkinter.CTkFrame(content_frame, fg_color="transparent")
            section_frame.pack(fill="x", padx=10, pady=(15,5))
            
            # Title
            title_label = customtkinter.CTkLabel(
                section_frame,
                text=title,
                font=customtkinter.CTkFont(size=20, weight="bold")
            )
            title_label.pack(anchor="w")
            
            # Description if provided
            if description:
                desc_label = customtkinter.CTkLabel(
                    section_frame,
                    text=description,
                    font=customtkinter.CTkFont(size=12),
                    text_color="gray70"
                )
                desc_label.pack(anchor="w", pady=(0,5))
            
            # Content frame
            content = customtkinter.CTkFrame(section_frame, fg_color="gray20")
            content.pack(fill="x", pady=5)
            return content

        def add_metric(frame, label: str, value: str):
            """Add a metric row"""
            row = customtkinter.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            
            label = customtkinter.CTkLabel(
                row,
                text=label,
                font=customtkinter.CTkFont(weight="bold"),
                width=200
            )
            label.pack(side="left", padx=10)
            
            value_label = customtkinter.CTkLabel(
                row,
                text=str(value)
            )
            value_label.pack(side="left", padx=5)

        for section_name, section_data in stats.items():
            if section_name == "Basic Metrics":
                metrics_frame = create_section(
                    "Instance Overview", 
                    "Basic problem dimensions and metrics"
                )
                for key, value in section_data.items():
                    add_metric(metrics_frame, key, value)
                    
            elif section_name == "Constraint Distribution":
                const_frame = create_section(
                    "Constraint Distribution",
                    "Distribution of different constraint types"
                )
                for key, value in section_data.items():
                    add_metric(const_frame, key, value)
                    
            elif section_name == "Problem Metrics":
                problems_frame = create_section(
                    "Problem Properties",
                    "Key characteristics and ratios"
                )
                for key, value in section_data.items():
                    add_metric(problems_frame, key, value)
                    
            else:
                section_frame = create_section(
                    f"{section_name}",
                    "Additional problem information"
                )
                for key, value in section_data.items():
                    add_metric(section_frame, key, value)

    def display_statistics(self, stats: Dict):
        """Display solving statistics in enhanced format"""
        # Clear previous stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        content_frame = customtkinter.CTkFrame(
            self.stats_frame,
            fg_color="gray17"
        )
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        def create_section(title: str, description: str = "", show_note: bool = False, note_text: str = ""):
            """Create a section with title, optional description, and note for UNSAT case"""
            section_frame = customtkinter.CTkFrame(content_frame, fg_color="transparent")
            section_frame.pack(fill="x", padx=10, pady=(15,5))
            
            # Title
            title_label = customtkinter.CTkLabel(
                section_frame,
                text=title,
                font=customtkinter.CTkFont(size=20, weight="bold")
            )
            title_label.pack(anchor="w")
            
            # Description if provided
            if description:
                desc_label = customtkinter.CTkLabel(
                    section_frame,
                    text=description,
                    font=customtkinter.CTkFont(size=12),
                    text_color="gray70"
                )
                desc_label.pack(anchor="w", pady=(0,5))
            
            # Add note before content frame if needed
            if show_note:
                note_label = customtkinter.CTkLabel(
                    section_frame,  # Add to section_frame, not content frame
                    text=note_text,
                    text_color="gray70",
                    wraplength=600,
                    justify="left",
                    font=customtkinter.CTkFont(size=12, slant="italic")
                )
                note_label.pack(anchor="w", padx=5, pady=(0, 10))
            
            # Content frame
            content = customtkinter.CTkFrame(section_frame, fg_color="gray20")
            content.pack(fill="x", pady=5)
            return content

        def add_metric(frame, label: str, value: str, is_success: bool = None):
            """Add a metric row with optional success/failure coloring"""
            row = customtkinter.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            
            label_widget = customtkinter.CTkLabel(
                row,
                text=label,
                font=customtkinter.CTkFont(weight="bold"),
                width=200
            )
            label_widget.pack(side="left", padx=10)
            
            text_color = "#00ff00" if is_success == True else "red" if is_success == False else None
            value_widget = customtkinter.CTkLabel(
                row,
                text=str(value),
                text_color=text_color,
                wraplength=600,
                justify="left"
            )
            value_widget.pack(side="left", padx=5, fill="x", expand=True)

        # Solution Status Section - Always show this
        if "solution_status" in stats:
            status_frame = create_section(
                "Solution Status",
                "Overall status and performance metrics"
            )
            for key, value in stats["solution_status"].items():
                is_success = value == "SAT" if key == "Status" else None
                add_metric(status_frame, key, value, is_success=is_success)

        # Problem Size Section - Always show this
        if "problem_size" in stats:
            size_frame = create_section(
                "Problem Size",
                "Dimensions and complexity metrics"
            )
            for key, value in stats["problem_size"].items():
                # Format percentages nicely
                if isinstance(value, float) and "Density" in key:
                    value = f"{value:.2f}%"
                add_metric(size_frame, key, value)

        # Constraint Distribution Section - Always show this
        if "constraint_distribution" in stats:
            distribution_frame = create_section(
                "Constraint Distribution",
                "Number of constraints by type"
            )
            for key, value in stats["constraint_distribution"].items():
                # Format constraint names nicely
                formatted_key = key.replace("_", " ").title()
                add_metric(distribution_frame, formatted_key, value)

        # UNSAT Reason Section
        if "solution_status" in stats and stats["solution_status"].get("Status") == "UNSAT":
            unsat_frame = create_section(
                "UNSAT Analysis",
                "Reasons why no solution exists"
            )
            if "reason" in stats["solution_status"]:
                add_metric(unsat_frame, "Reason", stats["solution_status"]["reason"], is_success=False)

            # Add detailed conflict analysis if available
            if "detailed_analysis" in stats and "Conflict Analysis" in stats["detailed_analysis"]:
                conflicts = stats["detailed_analysis"]["Conflict Analysis"].get("Detected Conflicts", [])
                for i, conflict in enumerate(conflicts, 1):
                    add_metric(unsat_frame, f"Conflict {i}", conflict["Description"], is_success=False)

        # Workload Distribution Section
        if "workload_distribution" in stats:
            workload_frame = create_section(
                "Workload Distribution",
                "How work is distributed among users",
                show_note=True,
                note_text=(
                    "Note: When no solution exists (UNSAT), constraint distribution cannot be checked as distribution cannot be computed. Hence, all metrics are marked as N/A."
                    if "solution_status" in stats and stats["solution_status"].get("Status") == "UNSAT"
                    else "Note: The lower the User Utilization (%) - especially more applicable in larger instances, the more efficiently work is distributed among users (minimalism).")
            )
            for key, value in stats["workload_distribution"].items():
                add_metric(workload_frame, key, value)

        # Constraint Compliance Section
        if "constraint_compliance" in stats:
            compliance_frame = create_section(
                "Constraint Compliance",
                "Verification of all constraint types",
                show_note=("solution_status" in stats and stats["solution_status"].get("Status") == "UNSAT"),
                note_text="Note: When no solution exists (UNSAT), constraint violations cannot be checked as there is no assignment to verify against. Hence, all violation counts are marked as N/A."
            )

            # Add success/failure message with color
            if "Solution Quality" in stats["constraint_compliance"]:
                quality = stats["constraint_compliance"]["Solution Quality"]
                is_perfect = "Perfect" in quality
                add_metric(compliance_frame, "Solution Quality", quality, is_success=is_perfect)

            # Add violation counts
            for key, value in stats["constraint_compliance"].items():
                if key != "Solution Quality":
                    add_metric(compliance_frame, key, value, is_success=value == 0)

        # Detailed Analysis Section
        if "detailed_analysis" in stats:
            self._create_detailed_analysis_section(content_frame, stats["detailed_analysis"])

    def _create_detailed_analysis_section(self, parent_frame, detailed_data: Dict):
        """Create detailed analysis section with scrollable subsections"""
        # Main container frame
        container_frame = customtkinter.CTkFrame(parent_frame, fg_color="gray17")
        container_frame.pack(fill="x", padx=10, pady=(15,5))
        
        # Title and Description for Detailed Analysis
        title_label = customtkinter.CTkLabel(
            container_frame,
            text="Detailed Analysis",
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        title_label.pack(anchor="w", padx=10, pady=(10,0))
        
        desc_label = customtkinter.CTkLabel(
            container_frame,
            text="Comprehensive breakdown of authorizations and constraints",
            font=customtkinter.CTkFont(size=12),
            text_color="gray70"
        )
        desc_label.pack(anchor="w", padx=10, pady=(0,10))
        
        # Create frame for sections
        detailed_frame = customtkinter.CTkFrame(container_frame, fg_color="transparent")
        detailed_frame.pack(fill="x", padx=10, pady=5)
        
        def create_section(title, content_creator_func, description=""):
            section = customtkinter.CTkFrame(detailed_frame, fg_color="gray20")
            section.pack(fill="x", pady=5)
            
            # Header with expand/collapse
            header = customtkinter.CTkFrame(section, fg_color="transparent")
            header.pack(fill="x", padx=5, pady=2)
            
            title_frame = customtkinter.CTkFrame(header, fg_color="transparent")
            title_frame.pack(fill="x", side="left", expand=True)
            
            section_title = customtkinter.CTkLabel(
                title_frame,
                text=title,
                font=customtkinter.CTkFont(size=16, weight="bold")
            )
            section_title.pack(anchor="w", padx=5)
            
            if description:
                section_desc = customtkinter.CTkLabel(
                    title_frame,
                    text=description,
                    font=customtkinter.CTkFont(size=12),
                    text_color="gray70"
                )
                section_desc.pack(anchor="w", padx=5, pady=(0,2))
            
            is_expanded = customtkinter.BooleanVar(value=False)
            content_frame = customtkinter.CTkScrollableFrame(
                section, 
                height=300,
                fg_color="gray20"
            )
            
            def toggle_section():
                if is_expanded.get():
                    content_frame.pack(fill="x", padx=10, pady=5, expand=True)
                else:
                    content_frame.pack_forget()
            
            toggle_btn = customtkinter.CTkButton(
                header,
                text="▼",
                width=30,
                command=lambda: [
                    is_expanded.set(not is_expanded.get()),
                    toggle_btn.configure(text="▲" if is_expanded.get() else "▼"),
                    toggle_section()
                ],
                fg_color="transparent",
                text_color="white",
                hover_color="gray30"
            )
            toggle_btn.pack(side="right", padx=5)
            
            if callable(content_creator_func):
                content_creator_func(content_frame)
            
            return section

        # Authorization Analysis Section
        if "Authorization Analysis" in detailed_data:
            auth_data = detailed_data["Authorization Analysis"]
            
            # Per Step Breakdown
            if "Per Step Breakdown" in auth_data:
                def create_step_content(frame):
                    for step, data in auth_data["Per Step Breakdown"].items():
                        self._create_detail_row(frame, step, data)
                create_section(
                    "Step Authorization", 
                    create_step_content,
                    "Breakdown of authorized users for each step"
                )
                
            # Per User Breakdown
            if "Per User Breakdown" in auth_data:
                def create_user_content(frame):
                    for user, data in auth_data["Per User Breakdown"].items():
                        self._create_detail_row(frame, user, data)
                create_section(
                    "User Authorization", 
                    create_user_content,
                    "Breakdown of authorized steps for each user"
                )

        # Constraint Analysis Section
        if "Constraint Analysis" in detailed_data:
            const_data = detailed_data["Constraint Analysis"]
            
            # SOD Constraints
            if const_data.get("Separation of Duty"):
                def create_sod_content(frame):
                    for constraint in const_data["Separation of Duty"]:
                        self._create_constraint_detail(frame, constraint)
                create_section(
                    "SOD Constraints", 
                    create_sod_content,
                    "Steps that must be performed by different users"
                )
            
            # BOD Constraints
            if const_data.get("Binding of Duty"):
                def create_bod_content(frame):
                    for constraint in const_data["Binding of Duty"]:
                        self._create_constraint_detail(frame, constraint)
                create_section(
                    "BOD Constraints", 
                    create_bod_content,
                    "Steps that must be performed by the same user"
                )
            
            # At Most K Constraints
            if const_data.get("At Most K"):
                def create_amk_content(frame):
                    for constraint in const_data["At Most K"]:
                        self._create_constraint_detail(frame, constraint)
                create_section(
                    "At-Most-K Constraints", 
                    create_amk_content,
                    "Limits on number of steps assigned to a user"
                )
            
            # One Team Constraints
            if const_data.get("One Team"):
                def create_team_content(frame):
                    for constraint in const_data["One Team"]:
                        self._create_constraint_detail(frame, constraint)
                create_section(
                    "One-Team Constraints", 
                    create_team_content,
                    "Steps that must be performed by users from the same team"
                )

            # SUAL Constraints
            if const_data.get("Super User At Least"):
                def create_sual_content(frame):
                    for constraint in const_data["Super User At Least"]:
                        self._create_constraint_detail(frame, constraint)
                create_section(
                    "Super User At Least Constraints", 
                    create_sual_content,
                    "Steps that require super user assignments when user count is low"
                )

            # Wang-Li Constraints            
            if const_data.get("Wang Li"):
                def create_wl_content(frame):
                    for constraint in const_data["Wang Li"]:
                        self._create_constraint_detail(frame, constraint)
                create_section(
                    "Wang-Li Constraints", 
                    create_wl_content,
                    "Steps that must be performed by users from the same department"
                )
                
            # ADA Constraints
            if const_data.get("Assignment Dependent"):
                def create_ada_content(frame):
                    for constraint in const_data["Assignment Dependent"]:
                        self._create_constraint_detail(frame, constraint)
                create_section(
                    "Assignment Dependent Constraints", 
                    create_ada_content,
                    "Steps whose assignments depend on other step assignments"
                )

    def _create_constraint_detail(self, parent_frame, constraint: Dict):
        """Create detailed constraint information with proper formatting"""
        detail_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        detail_frame.pack(fill="x", padx=10, pady=2)
        
        # Create expandable section
        is_expanded = customtkinter.BooleanVar(value=False)
        content_frame = customtkinter.CTkFrame(detail_frame, fg_color="transparent")
        
        def toggle_content():
            if is_expanded.get():
                content_frame.pack(fill="x", padx=20, pady=2)
            else:
                content_frame.pack_forget()
        
        # Header with description and toggle button
        header_frame = customtkinter.CTkFrame(detail_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=2)
        
        # Create appropriate description based on constraint type
        if "Teams" in constraint and "Steps" in constraint:
            description = f"Steps {constraint['Steps']} must be performed by users from the same team"
        else:
            description = constraint.get("Description", "")
        
        if len(description) > 60:  # For long descriptions
            short_desc = description[:57] + "..."
            desc_label = customtkinter.CTkLabel(
                header_frame,
                text=short_desc,
                font=customtkinter.CTkFont(size=12)
            )
        else:
            desc_label = customtkinter.CTkLabel(
                header_frame,
                text=description,
                font=customtkinter.CTkFont(size=12)
            )
        desc_label.pack(side="left", padx=5)
        
        toggle_btn = customtkinter.CTkButton(
            header_frame,
            text="▼",
            width=20,
            command=lambda: [is_expanded.set(not is_expanded.get()),
                            toggle_btn.configure(text="▲" if is_expanded.get() else "▼"),
                            toggle_content()],
            fg_color="transparent",
            hover_color="gray30"
        )
        toggle_btn.pack(side="right", padx=5)
        
        # Content with detailed information
        if "Steps" in constraint:
            steps_label = customtkinter.CTkLabel(
                content_frame,
                text=f"Steps involved: {constraint['Steps']}",
                font=customtkinter.CTkFont(size=12),
                text_color="gray70"
            )
            steps_label.pack(anchor="w", padx=5)
        
        # Handle One-Team specific content
        if "Teams" in constraint:
            for team_idx, team in enumerate(constraint["Teams"], 1):
                team_label = customtkinter.CTkLabel(
                    content_frame,
                    text=f"Team {team_idx}:  " + ", ".join(f"u{u}" for u in team),
                    font=customtkinter.CTkFont(size=12),
                    text_color="gray70",
                    wraplength=350
                )
                team_label.pack(anchor="w", padx=5, pady=(2, 0))
        
        # Handle Common Users content
        if "Common Users" in constraint:
            users = constraint["Common Users"]
            chunks = self._format_list_in_chunks(users, 10)
            for chunk in chunks:
                users_label = customtkinter.CTkLabel(
                    content_frame,
                    text=f"Common users: {chunk}",
                    font=customtkinter.CTkFont(size=12),
                    text_color="gray70",
                    wraplength=350
                )
                users_label.pack(anchor="w", padx=5)
        
        # Handle At-Most-K content
        if "K Value" in constraint:
            k_label = customtkinter.CTkLabel(
                content_frame,
                text=f"K value: {constraint['K Value']}",
                font=customtkinter.CTkFont(size=12),
                text_color="gray70"
            )
            k_label.pack(anchor="w", padx=5)
            
            steps = constraint.get("Steps", [])
            if steps:
                steps_label = customtkinter.CTkLabel(
                    content_frame,
                    text=f"Steps: {', '.join(map(str, steps))}",
                    font=customtkinter.CTkFont(size=12),
                    text_color="gray70",
                    wraplength=350
                )
                steps_label.pack(anchor="w", padx=5)

    def _format_list_in_chunks(self, items, chunk_size=10):
        """Format a list into chunks for better display"""
        return [
            f"[{', '.join(map(str, items[i:i + chunk_size]))}]"
            for i in range(0, len(items), chunk_size)
        ]
    
    def _create_detail_row(self, parent_frame, title: str, data: Dict):
        """Create a detail row with proper spacing"""
        row_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=10, pady=3)
        
        # Create header frame
        header_frame = customtkinter.CTkFrame(row_frame, fg_color="transparent")
        header_frame.pack(fill="x")
        
        # Get the full list of items
        details = data.get("Authorized Steps", data.get("Authorized Users", []))
        total_count = len(details) if details else 0
        
        # Title with count
        title_str = f"{title} ({total_count})"
        title_label = customtkinter.CTkLabel(
            header_frame,
            text=title_str,
            font=customtkinter.CTkFont(size=12, weight="bold")
        )
        title_label.pack(side="left", padx=5)
        
        # Add expand/collapse button
        is_expanded = customtkinter.BooleanVar(value=False)
        details_frame = customtkinter.CTkFrame(row_frame, fg_color="transparent")
        
        def toggle_details():
            if is_expanded.get():
                details_frame.pack(fill="x", padx=20, pady=2)
            else:
                details_frame.pack_forget()
        
        toggle_btn = customtkinter.CTkButton(
            header_frame,
            text="▼",
            width=20,
            command=lambda: [is_expanded.set(not is_expanded.get()),
                            toggle_btn.configure(text="▲" if is_expanded.get() else "▼"),
                            toggle_details()],
            fg_color="transparent",
            hover_color="gray30"
        )
        toggle_btn.pack(side="right", padx=5)
        
        # Create content with all items but DON'T pack the frame yet
        if details:
            sorted_details = sorted(details)
            content_label = customtkinter.CTkLabel(
                details_frame,
                text=", ".join(map(str, sorted_details)),
                font=customtkinter.CTkFont(size=12),
                text_color="gray70",
                wraplength=600
            )
            content_label.pack(anchor="w", pady=1)

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

    def _create_visualization_frame(self):
        """Create visualization control frame"""
        viz_frame = customtkinter.CTkFrame(self.sidebar_scrollable)
        viz_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        viz_label = customtkinter.CTkLabel(
            viz_frame,
            text="Visualization Controls:",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        viz_label.pack(pady=5)
        
        # Visualize button
        self.visualize_button = customtkinter.CTkButton(
            viz_frame,
            text="Generate Visualizations",
            width=180
        )
        self.visualize_button.pack(pady=5)
        
        # Clear cache button - now using same style as other buttons
        self.clear_viz_button = customtkinter.CTkButton(
            viz_frame,
            text="Clear Plot Cache",
            width=180
        )
        self.clear_viz_button.pack(pady=5)
        
        # Status label for visualization
        self.viz_status_label = customtkinter.CTkLabel(
            viz_frame,
            text="No instances in cache",
            wraplength=160
        )
        self.viz_status_label.pack(pady=5)

    def update_viz_status(self, num_instances: int):
        """Update visualization status label"""
        if num_instances == 0:
            self.viz_status_label.configure(text="No instances in cache")
        else:
            self.viz_status_label.configure(
                text=f"{num_instances} instance{'s' if num_instances > 1 else ''} ready for visualization"
            )
