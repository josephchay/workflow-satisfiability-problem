import os
from typing import List, Dict, Optional
import customtkinter
from CTkTable import CTkTable


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
        self.sidebar_frame.grid_rowconfigure(10, weight=1)  # Increased for new button

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

        # Add folder selection button
        # self.select_folder_button = customtkinter.CTkButton(
        #     self.sidebar_frame,
        #     text="Select Folder",
        #     command=None
        # )
        # self.select_folder_button.grid(row=3, column=0, padx=20, pady=10)

        # Create solve button before constraints frame
        self.solve_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Solve",
            command=None
        )
        self.solve_button.grid(row=6, column=0, padx=20, pady=10)

        # Create clear button
        self.clear_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Clear Results",
            command=self.clear_results
        )
        self.clear_button.grid(row=7, column=0, padx=20, pady=10)

        # Create constraints frame (moved to row 4-5)
        self._create_constraints_frame()

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
    
    def update_status(self, message: str):
        self.status_label.configure(text=message)
    
    def update_progress(self, value: float):
        self.progressbar.set(value)
    
    def display_solution(self, solution: Optional[List[Dict[str, int]]]):
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
        
        # For SAT solutions, create and display table
        values = [["Step", "Assigned User"]]
        values.extend([[f"s{assignment['step']}", f"u{assignment['user']}"] 
                    for assignment in solution])
        
        self.results_table = CTkTable(
            master=self.results_frame,
            row=len(values),
            column=2,
            values=values,
            header_color="gray20",
            hover_color="gray30",
            border_width=2,
            corner_radius=10,
            width=200,  # Fixed cell width
            height=40,  # Fixed cell height
            padx=5,    # Cell padding
            pady=5
        )
        self.results_table.pack(fill="both", expand=True, padx=10, pady=10)

    def display_statistics(self, stats: Dict):
        """Display solution statistics in the Statistics tab"""
        # Clear previous stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        # Create main content frame that will stretch
        content_frame = customtkinter.CTkFrame(self.stats_frame, fg_color="gray17")
        content_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Create stats display title
        title_label = customtkinter.CTkLabel(
            content_frame,
            text="Solution Statistics",
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
