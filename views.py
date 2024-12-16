import customtkinter
from typing import List, Dict, Optional
import tkinter as tk

class WSPView(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        
        # Initialize instance variables
        self.tests_dir = None
        self.status_label = None
        self.progressbar = None
        self.current_problem = None
        
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
        self.sidebar_frame.grid_rowconfigure(8, weight=1)
        
        # Create logo
        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="WSP Solver",
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Create buttons
        self.select_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Select File",
            command=None  # Will be set by controller
        )
        self.select_button.grid(row=1, column=0, padx=20, pady=10)
        
        self.solve_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Solve",
            command=None  # Will be set by controller
        )
        self.solve_button.grid(row=2, column=0, padx=20, pady=10)

        self.clear_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="Clear Results",
            command=self.clear_results
        )
        self.clear_button.grid(row=3, column=0, padx=20, pady=10)
        
        # Create constraints frame
        self._create_constraints_frame()
        
    def _create_constraints_frame(self):
        self.constraints_frame = customtkinter.CTkFrame(self.sidebar_frame)
        self.constraints_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
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
        self.stats_tab = self.results_notebook.add("Statistics")
        
        # Configure tabs
        for tab in [self.results_tab, self.stats_tab]:
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
        
        # Create scrollable frames
        self.results_scroll = customtkinter.CTkScrollableFrame(self.results_tab)
        self.results_scroll.pack(fill="both", expand=True)
        
        self.stats_frame = customtkinter.CTkFrame(self.stats_tab)
        self.stats_frame.pack(fill="both", expand=True)
    
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
    
    def clear_results(self):
        # Clear results tab
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        
        # Clear stats tab
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        # Reset progress and status
        self.progressbar.set(0)
        self.status_label.configure(text="Ready")
    
    def display_solution(self, solution: Optional[List[Dict[str, int]]]):
        # Clear previous results
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        
        if solution is None:
            # Display UNSAT result
            unsat_label = customtkinter.CTkLabel(
                self.results_scroll,
                text="No solution exists (UNSAT)",
                font=customtkinter.CTkFont(size=14, weight="bold")
            )
            unsat_label.pack(pady=20)
            return
            
        # Create solution table
        table_frame = customtkinter.CTkFrame(self.results_scroll)
        table_frame.pack(fill="x", padx=10, pady=5)
        
        # Create headers
        headers = ["Step", "Assigned User"]
        for col, header in enumerate(headers):
            label = customtkinter.CTkLabel(
                table_frame,
                text=header,
                font=customtkinter.CTkFont(weight="bold")
            )
            label.grid(row=0, column=col, padx=5, pady=5)
        
        # Add solution rows
        for row, assignment in enumerate(solution, start=1):
            step_label = customtkinter.CTkLabel(
                table_frame,
                text=f"s{assignment['step']}"
            )
            step_label.grid(row=row, column=0, padx=5, pady=2)
            
            user_label = customtkinter.CTkLabel(
                table_frame,
                text=f"u{assignment['user']}"
            )
            user_label.grid(row=row, column=1, padx=5, pady=2)
    
    def display_statistics(self, stats: Dict):
        # Clear previous stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        # Create stats display
        stats_label = customtkinter.CTkLabel(
            self.stats_frame,
            text="Solution Statistics",
            font=customtkinter.CTkFont(size=16, weight="bold")
        )
        stats_label.pack(pady=10)
        
        for key, value in stats.items():
            stat_frame = customtkinter.CTkFrame(self.stats_frame)
            stat_frame.pack(fill="x", padx=20, pady=5)
            
            key_label = customtkinter.CTkLabel(
                stat_frame,
                text=f"{key}:",
                font=customtkinter.CTkFont(weight="bold")
            )
            key_label.pack(side="left", padx=5)
            
            value_label = customtkinter.CTkLabel(
                stat_frame,
                text=str(value)
            )
            value_label.pack(side="left", padx=5)
