# controllers.py
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
        self.constraint_stats = None
        
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
            # Get active constraints from view
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
            stats = self.collect_solution_stats(solution, exe_time, active_constraints)
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
    
    def collect_solution_stats(self, solution: Optional[List[Dict[str, int]]], solve_time: float, active_constraints: Dict[str, bool]) -> Dict:
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
            stats.update({
                "Max Assignments per User": max(assignments_per_user.values()),
                "Min Assignments per User": min(assignments_per_user.values()),
                "Avg Assignments per User": f"{sum(assignments_per_user.values()) / len(used_users):.1f}"
            })
        
        # Analyze constraint satisfaction for active constraints
        if active_constraints:
            constraint_stats = self._analyze_constraint_satisfaction(solution, active_constraints)
            stats.update(constraint_stats)
        
        return stats
    
    def _analyze_constraint_satisfaction(self, solution: List[Dict[str, int]], active_constraints: Dict[str, bool]) -> Dict:
        """Analyze how the solution satisfies different constraints"""
        stats = {}
        
        if active_constraints['authorizations']:
            # Check authorization violations
            violations = 0
            for assignment in solution:
                user = assignment['user'] - 1  # Convert to 0-based
                step = assignment['step'] - 1  # Convert to 0-based
                if self.current_instance.auth[user] and step not in self.current_instance.auth[user]:
                    violations += 1
            stats["Authorization Violations"] = violations
        
        if active_constraints['separation_of_duty']:
            # Check SOD violations
            violations = 0
            for s1, s2 in self.current_instance.SOD:
                user1 = next(a['user'] for a in solution if a['step'] - 1 == s1)
                user2 = next(a['user'] for a in solution if a['step'] - 1 == s2)
                if user1 == user2:
                    violations += 1
            stats["SOD Violations"] = violations
        
        if active_constraints['binding_of_duty']:
            # Check BOD violations
            violations = 0
            for s1, s2 in self.current_instance.BOD:
                user1 = next(a['user'] for a in solution if a['step'] - 1 == s1)
                user2 = next(a['user'] for a in solution if a['step'] - 1 == s2)
                if user1 != user2:
                    violations += 1
            stats["BOD Violations"] = violations
        
        if active_constraints['at_most_k']:
            # Check at-most-k violations
            violations = 0
            for k, steps in self.current_instance.at_most_k:
                users = set()
                for step in steps:
                    user = next(a['user'] for a in solution if a['step'] - 1 == step)
                    users.add(user)
                if len(users) > k:
                    violations += 1
            stats["At-Most-K Violations"] = violations
        
        if active_constraints['one_team']:
            # Check one-team violations
            violations = 0
            for steps, teams in self.current_instance.one_team:
                assigned_users = set()
                for step in steps:
                    user = next(a['user'] for a in solution if a['step'] - 1 == step)
                    assigned_users.add(user - 1)  # Convert to 0-based
                
                valid_assignment = False
                for team in teams:
                    if assigned_users.issubset(set(team)):
                        valid_assignment = True
                        break
                
                if not valid_assignment:
                    violations += 1
            stats["One-Team Violations"] = violations
        
        return stats
