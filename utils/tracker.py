from ortools.sat.python import cp_model


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    """Solution collector callback for counting solutions"""

    def __init__(self, solver_type, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._solver_type = solver_type
        self._variables = variables
        self._solution_count = 0
        self._solutions = []

    def on_solution_callback(self):
        self._solution_count += 1
        solution = []
        
        if self._solver_type == "CS":
            for s, var in enumerate(self._variables):
                user = self.Value(var)
                solution.append({'step': s + 1, 'user': user + 1})
        else:  # PBPB or UDPB
            steps = len(self._variables)
            users = len(self._variables[0])  # Get number of users from first step's assignments
            
            for s in range(steps):
                for u in range(users):
                    if self.Value(self._variables[s][u]):
                        solution.append({'step': s + 1, 'user': u + 1})
        
        self._solutions.append(solution)
    
    def solution_count(self):
        return self._solution_count
    
    def get_solutions(self):
        return self._solutions[0] if self._solutions else []
