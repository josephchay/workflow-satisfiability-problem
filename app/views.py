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
            width=210,
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
            wraplength=160
        )
        self.file_label.grid(row=1, column=0, padx=20, pady=5)

        # Create buttons
        self.select_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Select File",
            width=160
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
            width=160
        )
        self.solve_button.grid(row=8, column=0, padx=20, pady=10)

        # Create clear button
        self.clear_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Clear Results",
            command=self.clear_results,
            width=160
        )
        self.clear_button.grid(row=9, column=0, padx=20, pady=10)

        # Generate Visualizations button
        self.visualize_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Generate Visualizations",
            command=self.visualize,
            width=160
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
            width=160
        )
        self.solver_type.pack(pady=5)
        
        # Create solver description label
        self.solver_description = customtkinter.CTkLabel(
            self.solver_frame,
            text="",
            wraplength=160,  # Increased wraplength
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
        
        # Create scrollable frames
        self.results_frame = customtkinter.CTkScrollableFrame(self.results_tab)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.instance_frame = customtkinter.CTkScrollableFrame(self.instance_tab)
        self.instance_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.stats_frame = customtkinter.CTkScrollableFrame(self.stats_tab)
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
        """Display solving statistics in enhanced format"""
        # Clear previous stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        content_frame = customtkinter.CTkFrame(
            self.stats_frame,
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

        def add_metric(frame, label: str, value: str, is_success: bool = None):
            """Add a metric row with optional success/failure coloring"""
            row = customtkinter.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            
            label = customtkinter.CTkLabel(
                row,
                text=label,
                font=customtkinter.CTkFont(weight="bold"),
                width=200
            )
            label.pack(side="left", padx=10)
            
            text_color = "#00ff00" if is_success == True else "red" if is_success == False else None
            value_label = customtkinter.CTkLabel(
                row,
                text=str(value),
                text_color=text_color
            )
            value_label.pack(side="left", padx=5)

        # Solution Status Section
        if "solution_status" in stats:
            status_frame = create_section(
                "Solution Status",
                "Overall status and performance metrics"
            )
            for key, value in stats["solution_status"].items():
                add_metric(status_frame, key, value)

        # Problem Size Section
        if "problem_size" in stats:
            size_frame = create_section(
                "Problem Size",
                "Dimensions and complexity metrics"
            )
            for key, value in stats["problem_size"].items():
                add_metric(size_frame, key, value)

        # Workload Distribution Section
        if "workload_distribution" in stats:
            workload_frame = create_section(
                "Workload Distribution",
                "How work is distributed among users"
            )
            for key, value in stats["workload_distribution"].items():
                add_metric(workload_frame, key, value)

        # Constraint Compliance Section
        if "constraint_compliance" in stats:
            compliance_frame = create_section(
                "Constraint Compliance",
                "Verification of all constraint types"
            )

            # Add success/failure message with color
            if "Solution Quality" in stats["constraint_compliance"]:
                quality = stats["constraint_compliance"]["Solution Quality"]
                is_perfect = "Perfect" in quality
                add_metric(compliance_frame, "Solution Quality", quality, is_success=is_perfect)

            # Add violation counts
            for key, value in stats["constraint_compliance"].items():
                if key != "Solution Quality":
                    add_metric(
                        compliance_frame, 
                        key, 
                        value,
                        is_success=value == 0
                    )

        # Constraint Distribution Section
        if "constraint_distribution" in stats:
            distribution_frame = create_section(
                "Constraint Distribution",
                "Number of constraints by type"
            )
            for key, value in stats["constraint_distribution"].items():
                add_metric(distribution_frame, key, value)

        # Detailed Analysis Section (if available)
        if "detailed_analysis" in stats:
            self._create_detailed_analysis_section(content_frame, stats["detailed_analysis"])

    def _create_detailed_analysis_section(self, parent_frame, detailed_data: Dict):
        """Create detailed analysis section with scrollable subsections"""
        detailed_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        detailed_frame.pack(fill="x", padx=10, pady=(15,5))
        
        def create_section(title, content_creator_func):
            section = customtkinter.CTkFrame(detailed_frame, fg_color="gray20")
            section.pack(fill="x", pady=5)
            
            # Header with expand/collapse
            header = customtkinter.CTkFrame(section, fg_color="transparent")
            header.pack(fill="x", padx=5, pady=2)
            
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
            
            section_btn = customtkinter.CTkButton(
                header,
                text=f"{title} ▼",
                command=lambda: [
                    is_expanded.set(not is_expanded.get()),
                    section_btn.configure(text=f"{title} ▲" if is_expanded.get() else f"{title} ▼"),
                    toggle_section()
                ],
                fg_color="transparent",
                text_color="white",
                hover_color="gray30"
            )
            section_btn.pack(fill="x", padx=5)
            
            # Only call content_creator if it's a function
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
                create_section("Step Authorization", create_step_content)
            
            # Per User Breakdown
            if "Per User Breakdown" in auth_data:
                def create_user_content(frame):
                    for user, data in auth_data["Per User Breakdown"].items():
                        self._create_detail_row(frame, user, data)
                create_section("User Authorization", create_user_content)

        # Constraint Analysis Section
        if "Constraint Analysis" in detailed_data:
            const_data = detailed_data["Constraint Analysis"]
            
            # SOD Constraints
            if const_data.get("Separation of Duty"):
                def create_sod_content(frame):
                    for constraint in const_data["Separation of Duty"]:
                        self._create_constraint_detail(frame, constraint)
                create_section("SOD Constraints", create_sod_content)
            
            # BOD Constraints
            if const_data.get("Binding of Duty"):
                def create_bod_content(frame):
                    for constraint in const_data["Binding of Duty"]:
                        self._create_constraint_detail(frame, constraint)
                create_section("BOD Constraints", create_bod_content)
            
            # At Most K Constraints
            if const_data.get("At Most K"):
                def create_amk_content(frame):
                    for constraint in const_data["At Most K"]:
                        self._create_constraint_detail(frame, constraint)
                create_section("At-Most-K Constraints", create_amk_content)
            
            # One Team Constraints
            if const_data.get("One Team"):
                def create_team_content(frame):
                    for constraint in const_data["One Team"]:
                        self._create_constraint_detail(frame, constraint)
                create_section("One-Team Constraints", create_team_content)

        # Conflict Analysis Section
        if "Conflict Analysis" in detailed_data:
            def create_conflict_content(frame):
                conflicts = detailed_data["Conflict Analysis"].get("Detected Conflicts", [])
                for conflict in conflicts:
                    conflict_row = customtkinter.CTkFrame(frame, fg_color="transparent")
                    conflict_row.pack(fill="x", padx=10, pady=2)
                    
                    conflict_label = customtkinter.CTkLabel(
                        conflict_row,
                        text=f"• {conflict['Description']}",
                        text_color="#ff6b6b",
                        wraplength=400,
                        justify="left"
                    )
                    conflict_label.pack(anchor="w", padx=5)
            create_section("Detected Conflicts", create_conflict_content)

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
        
        if "K Value" in constraint:
            k_label = customtkinter.CTkLabel(
                content_frame,
                text=f"K value: {constraint['K Value']}",
                font=customtkinter.CTkFont(size=12),
                text_color="gray70"
            )
            k_label.pack(anchor="w", padx=5)
            
            steps = constraint.get("Steps", [])
            chunks = self._format_list_in_chunks(steps, 10)
            for chunk in chunks:
                steps_label = customtkinter.CTkLabel(
                    content_frame,
                    text=f"Applicable steps: {chunk}",
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
        
        # Create content with all items
        if details:
            details_frame.pack_propagate(False)  # Prevent frame from shrinking
            for item in details:
                item_label = customtkinter.CTkLabel(
                    details_frame,
                    text=str(item),
                    font=customtkinter.CTkFont(size=12),
                    text_color="gray70"
                )
                item_label.pack(anchor="w", padx=5, pady=1)

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

        # Basic Metrics Section
        metrics_frame = customtkinter.CTkFrame(content_frame, fg_color="gray20")
        metrics_frame.pack(fill="x", padx=10, pady=5)
        
        metrics_title = customtkinter.CTkLabel(
            metrics_frame,
            text="Problem Metrics",
            font=customtkinter.CTkFont(size=18, weight="bold")
        )
        metrics_title.pack(pady=5)

        for section_name, section_data in stats.items():
            section_frame = customtkinter.CTkFrame(metrics_frame, fg_color="transparent")
            section_frame.pack(fill="x", padx=10, pady=5)
            
            section_label = customtkinter.CTkLabel(
                section_frame,
                text=section_name,
                font=customtkinter.CTkFont(size=14, weight="bold")
            )
            section_label.pack(anchor="w", pady=(5,2))
            
            for key, value in section_data.items():
                detail_frame = customtkinter.CTkFrame(section_frame, fg_color="transparent")
                detail_frame.pack(fill="x", pady=1)
                
                label = customtkinter.CTkLabel(
                    detail_frame,
                    text=f"{key}:",
                    font=customtkinter.CTkFont(weight="bold")
                )
                label.pack(side="left", padx=10)
                
                value_label = customtkinter.CTkLabel(
                    detail_frame,
                    text=str(value)
                )
                value_label.pack(side="left", padx=5)

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
