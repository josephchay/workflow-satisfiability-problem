import customtkinter
from typing import Dict, List, Optional
import time
from instance import WSPInstance
from solver import WSPSolver
from utils import parse_instance_file

class WSPController:
    def __init__(self, view):
        self.view = view
        self.current_instance: Optional[WSPInstance] = None
        
        # Connect button callbacks
        self.view.select_button.configure(command=self.select_file)
        self.view.solve_button.configure(command=self.solve)
    
    def select_file(self):
        """Handle file selection"""
        filename = customtkinter.filedialog.askopenfilename(
            title="Select WSP Instance",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.current_instance = parse_instance_file(filename)
                self.view.update_status(f"Loaded: {filename}")
                
                # Display instance statistics
                self.display_instance_stats()
                
            except Exception as e:
                self.view.update_status(f"Error loading file: {str(e)}")
    
    def solve(self):
        """Handle solving the current instance"""
        if not self.current_instance:
            self.view.update_status("Please select a file first")
            return
        
        try:
            # Get active constraints
            active_constraints = {
                name: var.get()
                for name, var in self.view.constraint_vars.items()
            }
            
            # Start solving
            self.view.update_status("Solving...")
            self.view.update_progress(0.2)
            
            # Create solver
            solver = WSPSolver(self.current_instance, active_constraints)
            
            # Solve instance and get result
            result = solver.solve()
            
            # Update progress
            self.view.update_progress(0.8)
            
            # Convert solution format for display
            solution = None
            if result['sat'] == 'sat':
                solution = []
                for assignment in result['sol']:
                    # Parse strings like 's1: u2' into dict format
                    parts = assignment.split(': ')
                    step = int(parts[0][1:])  # Remove 's' and convert to int
                    user = int(parts[1][1:])  # Remove 'u' and convert to int
                    solution.append({'step': step, 'user': user})
            
            # Display solution
            self.view.display_solution(solution)
            
            # Collect and display statistics
            exe_time = float(result['exe_time'].replace('ms', '')) / 1000  # Convert ms to seconds
            stats = self.collect_solution_stats(solution, exe_time)
            self.view.display_statistics(stats)
            
            # Update final status
            self.view.update_progress(1.0)
            status = "Solution found!" if solution else "No solution exists (UNSAT)"
            self.view.update_status(f"{status} ({result['exe_time']})")
            
        except Exception as e:
            self.view.update_status(f"Error solving: {str(e)}")
            self.view.update_progress(0)

    def display_instance_stats(self):
        """Display statistics about the loaded instance"""
        if not self.current_instance:
            return
        
        stats = {
            "Number of Steps": self.current_instance.number_of_steps,
            "Number of Users": self.current_instance.number_of_users,
            "Number of Constraints": self.current_instance.number_of_constraints,
            "Authorization Constraints": len([u for u in self.current_instance.auth if u]),
            "Separation of Duty Constraints": len(self.current_instance.SOD),
            "Binding of Duty Constraints": len(self.current_instance.BOD),
            "At-Most-K Constraints": len(self.current_instance.at_most_k),
            "One-Team Constraints": len(self.current_instance.one_team)
        }
        
        self.view.display_statistics(stats)
    
    def collect_solution_stats(self, solution: Optional[List[Dict[str, int]]], solve_time: float) -> Dict:
        """Collect statistics about the solution"""
        if not solution:
            return {
                "Status": "UNSAT",
                "Solve Time": f"{solve_time:.2f} seconds"
            }
        
        # Count users actually used in solution
        used_users = set(assignment['user'] for assignment in solution)
        
        stats = {
            "Status": "SAT",
            "Solve Time": f"{solve_time:.2f} seconds",
            "Number of Users Used": len(used_users),
            "User Utilization": f"{(len(used_users) / self.current_instance.number_of_users * 100):.1f}%"
        }
        
        # Count assignments per user
        assignments_per_user = {}
        for assignment in solution:
            user = assignment['user']
            assignments_per_user[user] = assignments_per_user.get(user, 0) + 1
        
        if assignments_per_user:
            stats.update({"Max Assignments per User": max(assignments_per_user.values()),
            "Min Assignments per User": min(assignments_per_user.values()),
            "Avg Assignments per User": f"{sum(assignments_per_user.values()) / len(used_users):.1f}"
        })
        
        # Analyze constraint satisfaction
        constraint_stats = self._analyze_constraint_satisfaction(solution)
        stats.update(constraint_stats)
        
        return stats
    
    def _analyze_constraint_satisfaction(self, solution: List[Dict[str, int]]) -> Dict:
        """Analyze how the solution satisfies different constraints"""
        stats = {}
        
        if self.active_constraints['authorizations']:
            # Check authorization violations
            violations = 0
            for assignment in solution:
                user = assignment['user'] - 1  # Convert to 0-based
                step = assignment['step'] - 1  # Convert to 0-based
                if self.instance.auth[user] and step not in self.instance.auth[user]:
                    violations += 1
            stats["Authorization Violations"] = violations
        
        if self.active_constraints['separation_of_duty']:
            # Check SOD violations
            violations = 0
            for s1, s2 in self.instance.SOD:
                user1 = next(a['user'] for a in solution if a['step'] - 1 == s1)
                user2 = next(a['user'] for a in solution if a['step'] - 1 == s2)
                if user1 == user2:
                    violations += 1
            stats["SOD Violations"] = violations
        
        if self.active_constraints['binding_of_duty']:
            # Check BOD violations
            violations = 0
            for s1, s2 in self.instance.BOD:
                user1 = next(a['user'] for a in solution if a['step'] - 1 == s1)
                user2 = next(a['user'] for a in solution if a['step'] - 1 == s2)
                if user1 != user2:
                    violations += 1
            stats["BOD Violations"] = violations
        
        if self.active_constraints['at_most_k']:
            # Check at-most-k violations
            violations = 0
            for k, steps in self.instance.at_most_k:
                # Get unique users assigned to these steps
                users = set()
                for step in steps:
                    user = next(a['user'] for a in solution if a['step'] - 1 == step)
                    users.add(user)
                if len(users) > k:
                    violations += 1
            stats["At-Most-K Violations"] = violations
        
        if self.active_constraints['one_team']:
            # Check one-team violations
            violations = 0
            for steps, teams in self.instance.one_team:
                # Get users assigned to these steps
                assigned_users = set()
                for step in steps:
                    user = next(a['user'] for a in solution if a['step'] - 1 == step)
                    assigned_users.add(user - 1)  # Convert to 0-based
                
                # Check if all users are from one team
                valid_assignment = False
                for team in teams:
                    if assigned_users.issubset(set(team)):
                        valid_assignment = True
                        break
                
                if not valid_assignment:
                    violations += 1
            stats["One-Team Violations"] = violations
        
        return stats
    
    def validate_solution(self, solution: List[Dict[str, int]]) -> bool:
        """Validate that a solution satisfies all active constraints"""
        stats = self._analyze_constraint_satisfaction(solution)
        return all(violations == 0 for violations in stats.values())
    
    def export_solution(self, filename: str, solution: List[Dict[str, int]], solve_time: float):
        """Export the solution to a file"""
        try:
            with open(filename, 'w') as f:
                # Write header
                f.write("Workflow Satisfiability Problem - Solution\n")
                f.write("=" * 50 + "\n\n")
                
                # Write instance information
                f.write("Instance Information:\n")
                f.write(f"Number of Steps: {self.instance.number_of_steps}\n")
                f.write(f"Number of Users: {self.instance.number_of_users}\n")
                f.write(f"Number of Constraints: {self.instance.number_of_constraints}\n\n")
                
                # Write solution
                f.write("Solution:\n")
                for assignment in solution:
                    f.write(f"Step {assignment['step']} -> User {assignment['user']}\n")
                
                # Write statistics
                f.write("\nStatistics:\n")
                stats = self.collect_solution_stats(solution, solve_time)
                for key, value in stats.items():
                    f.write(f"{key}: {value}\n")
                
                self.view.update_status(f"Solution exported to {filename}")
        
        except Exception as e:
            self.view.update_status(f"Error exporting solution: {str(e)}")
    
    def get_active_constraints_info(self) -> List[str]:
        """Get information about which constraints are active"""
        active = []
        for name, var in self.view.constraint_vars.items():
            if var.get():
                active.append(name.replace('_', ' ').title())
        return active

    def load_previous_solution(self, filename: str):
        """Load a previously saved solution"""
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            # Parse solution lines
            solution = []
            solution_started = False
            for line in lines:
                if line.startswith("Solution:"):
                    solution_started = True
                    continue
                if solution_started and line.strip() and "Statistics:" not in line:
                    # Parse line like "Step 1 -> User 2"
                    parts = line.strip().split()
                    step = int(parts[1])
                    user = int(parts[4])
                    solution.append({'step': step, 'user': user})
            
            if solution:
                self.view.display_solution(solution)
                self.view.update_status(f"Previous solution loaded from {filename}")
            else:
                self.view.update_status("No solution found in file")
        
        except Exception as e:
            self.view.update_status(f"Error loading previous solution: {str(e)}")