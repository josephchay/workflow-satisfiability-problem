# cli_solver.py
import sys
import os
from typing import Dict
from solvers import BaseWSPSolver
from factories import WSPSolverFactory
from typings import WSPSolverType
from filesystem import parse_instance_file


def solve_instance(filename: str) -> Dict:
    """Solve single WSP instance"""
    try:
        # Parse instance
        instance = parse_instance_file(filename)
        print(f"Loaded instance: {os.path.basename(filename)}")
        print(f"Steps: {instance.number_of_steps}")
        print(f"Users: {instance.number_of_users}")
        print(f"Total constraints: {instance.number_of_constraints}")

        # Create solver
        factory = WSPSolverFactory()
        active_constraints = {
            'authorizations': True,
            'separation_of_duty': True,
            'binding_of_duty': True,
            'at_most_k': True,
            'one_team': True
        }

        solver = factory.create_solver(WSPSolverType.SAT4J_PBPB, instance, active_constraints)
        
        # Solve instance
        print("\nSolving...")
        result = solver.solve()

        # Print result
        print("\nResult:")
        print(f"Status: {result['sat']}")
        print(f"Time: {result['result_exe_time']:.2f}ms")
        if result['sat'] == 'sat':
            print("Solution:")
            solution = result['sol']
            for assignment in sorted(solution, key=lambda x: x['step']):
                print(f"  Step {assignment['step']} -> User {assignment['user']}")

        return result

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cli_solver.py <instance_file>")
        sys.exit(1)

    solve_instance(sys.argv[1])
