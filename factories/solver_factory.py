from typing import Dict, Type
from solvers import ZThreeSolver, ORToolsSolver, GurobiSolver, CBCSolver, SCIPSolver, DEAPSolver, LocalSearchSolver, TabuSearchSolver

from components import Instance


class SolverFactory:
    solvers: Dict[str, Type] = {
        'z3': ZThreeSolver,
        'ortools': ORToolsSolver,
        'gurobi': GurobiSolver,
        'cbc': CBCSolver,
        'scip': SCIPSolver,
        'deap': DEAPSolver,
        'localsearch': LocalSearchSolver,
        'tabusearch': TabuSearchSolver
    }

    @staticmethod
    def solve_with_all_solvers(instance: Instance):
        results = {}
        for name, solver_class in SolverFactory.solvers.items():
            try:
                solver = solver_class(instance)
                solution = solver.solve()
                results[name] = {
                    'solution': solution,
                    'status': 'solved' if solution else 'unsolved'
                }
            except Exception as e:
                results[name] = {
                    'solution': None,
                    'status': f'error: {str(e)}'
                }
        return results

    @staticmethod
    def get_solver(name: str, instance: Instance, active_constraints=None):
        if name not in SolverFactory.solvers:
            raise ValueError(f"Unknown solver: {name}")
        return SolverFactory.solvers[name](instance, active_constraints)
