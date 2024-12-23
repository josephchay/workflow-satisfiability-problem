import time


class BaseSolver:
    """Base class for all solvers providing common functionality"""
    def __init__(self, instance):
        self.instance = instance
        self.model = None
        self.solver = None
        self.var_manager = None
        self.constraint_manager = None
        self.start_time = None
        
    def _setup_solver(self):
        """Setup solver with default parameters. Can be overridden by child classes."""
        raise NotImplementedError
        
    def _create_model(self):
        """Create the constraint model. Must be implemented by child classes."""
        raise NotImplementedError
        
    def _build_model(self):
        """Build model with all constraints. Must be implemented by child classes."""
        raise NotImplementedError
        
    def _process_solution(self, solution_dict):
        """Process raw solution into required format. Must be implemented by child classes."""
        raise NotImplementedError

    def solve(self):
        """Main solving method. Should be implemented by child classes."""
        raise NotImplementedError
        
    def _handle_infeasible(self, status):
        """Handle infeasible or invalid results. Should be implemented by child classes."""
        raise NotImplementedError
        
    def _get_solving_time(self):
        """Get solving time in milliseconds"""
        if not self.start_time:
            return 0
        return (time.time() - self.start_time) * 1000

    def _check_authorization_gaps(self):
        """Check for steps with no authorized users"""
        gaps = []
        for step in range(self.instance.number_of_steps):
            if not any(self.instance.user_step_matrix[user][step] 
                      for user in range(self.instance.number_of_users)):
                gaps.append(step)
        return gaps

    def _get_step_authorized_users(self, step):
        """Get list of users authorized for a step"""
        return [user for user in range(self.instance.number_of_users)
                if self.instance.user_step_matrix[user][step]]

    def _get_bod_common_users(self, step1, step2):
        """Get users authorized for both steps in a BOD constraint"""
        users1 = set(self._get_step_authorized_users(step1))
        users2 = set(self._get_step_authorized_users(step2))
        return users1 & users2

    def _check_sod_conflicts(self):
        """Check for SOD conflicts"""
        conflicts = []
        for s1, s2 in self.instance.SOD:
            users1 = set(self._get_step_authorized_users(s1))
            users2 = set(self._get_step_authorized_users(s2))
            if users1 == users2 and len(users1) == 1:
                conflicts.append((s1, s2, list(users1)[0]))
        return conflicts

    def _check_at_most_k_feasibility(self):
        """Check if at-most-k constraints can potentially be satisfied"""
        infeasible = []
        for k, steps in self.instance.at_most_k:
            total_users = set()
            for step in steps:
                users = set(self._get_step_authorized_users(step))
                total_users.update(users)
            if len(total_users) * k < len(steps):
                infeasible.append((k, steps, len(total_users)))
        return infeasible

    def _log(self, message: str):
        """Print message only if not in GUI mode"""
        if not self.gui_mode:
            print(message)
