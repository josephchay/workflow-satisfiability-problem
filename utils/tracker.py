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
        
        # Get user for each step
        for s in range(len(self._variables)):
            # Find which user was assigned to this step
            for u in range(len(self._variables[s])):
                if self._variables[s][u] is not None and self.Value(self._variables[s][u]) > 0.5:
                    solution.append({'step': s + 1, 'user': u + 1})
                    break

        self._solutions.append(solution)
    
    def solution_count(self):
        return self._solution_count
    
    def get_solutions(self):
        return self._solutions[0] if self._solutions else []
