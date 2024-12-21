import sys
from typing import Dict
from factories import WSPSolverFactory
from typings import WSPSolverType
from typings import Instance


def solve(instance: str) -> Dict:
    """Solve single WSP instance"""
    try:
        # Create solver
        factory = WSPSolverFactory()
        active_constraints = {
            'authorizations': True,
            'separation_of_duty': True,
            'binding_of_duty': True,
            'at_most_k': True,
            'one_team': True
        }

        solver = factory.create_solver(WSPSolverType.ORTOOLS_PBPB, instance, active_constraints)
        
        # Solve instance
        solution = solver.solve()
        return solution

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python main_cli.py <instance file name> <solution save file name>')
        exit(1)

    instance = Instance(sys.argv[1])
    solution = solve(instance)
    solution.save(sys.argv[2])
