import argparse
import sys
from typing import Dict, Optional, Tuple

from constants import SolverType
from factories import SolverFactory
from filesystem import InstanceParser
from typings import Instance, Solution
from solvers import BaseSolver


def solve(instance: Instance, 
          solver_type: SolverType, 
          active_constraints: Optional[Dict[str, bool]] = None) -> Tuple[Optional[BaseSolver], Optional[Solution]]:
    """Solve single WSP instance with specified solver type"""
    try:
        # Create solver factory
        factory = SolverFactory()
        
        # Set default active constraints if not provided
        if active_constraints is None:
            active_constraints = {
                'authorizations': True,
                'separation_of_duty': True,
                'binding_of_duty': True,
                'at_most_k': True,
                'one_team': True
            }

        # Create and use specified solver
        solver = factory.create_solver(solver_type, instance, active_constraints, gui_mode=False)
        
        # Solve instance
        solution = solver.solve()
        return solver, solution

    except Exception as e:
        print(f"Error solving with {solver_type.value}: {str(e)}")
        return None


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Solve Workflow Satisfiability Problem (WSP) instance'
    )
    
    # Positional arguments for input and output files
    parser.add_argument('input_file', 
                        help='Path to the WSP instance input file')
    parser.add_argument('output_file', 
                        help='Path to save the solution output')
    
    # Optional solver type argument
    # Note: SolverType enum values are used as choices. Checkout `constants/solver_type.py` for more details.
    solver_choices = [st.value for st in SolverType]
    parser.add_argument('-s', '--solver', 
                        choices=solver_choices, 
                        default=SolverType.ORTOOLS_CP.value,
                        help='Solver type to use (default: %(default)s)')
    
    # Optional constraint toggle arguments
    parser.add_argument('--no-auth', 
                        action='store_true', 
                        help='Disable authorization constraints')
    parser.add_argument('--no-sod', 
                        action='store_true', 
                        help='Disable separation of duty constraints')
    parser.add_argument('--no-bod', 
                        action='store_true', 
                        help='Disable binding of duty constraints')
    parser.add_argument('--no-atmosk', 
                        action='store_true', 
                        help='Disable at-most-k constraints')
    parser.add_argument('--no-oneteam', 
                        action='store_true', 
                        help='Disable one-team constraints')
    parser.add_argument('--no-sual', 
                        action='store_true',
                        help='Disable Super-User-At-Least constraints')
    parser.add_argument('--no-wl', 
                        action='store_true',
                        help='Disable Wang-Li constraints')
    parser.add_argument('--no-ada', 
                        action='store_true',
                        help='Disable Assignment-Dependent Authorization constraints')
    
    return parser.parse_args()


def main():
    # Parse arguments
    args = parse_arguments()
    
    # Set up active constraints
    active_constraints = {
        'authorizations': not args.no_auth,
        'separation_of_duty': not args.no_sod,
        'binding_of_duty': not args.no_bod,
        'at_most_k': not args.no_atmosk,
        'one_team': not args.no_oneteam,
        'super_user_at_least': not args.no_sual,
        'wang_li': not args.no_wl,
        'assignment_dependent': not args.no_ada
    }
    
    # Determine solver type
    try:
        solver_type = SolverType(args.solver)
    except ValueError:
        print(f"Invalid solver type: {args.solver}")
        sys.exit(1)
    
    # Load instance
    try:
        instance = InstanceParser.parse_file(args.input_file)
    except Exception as e:
        print(f"Error loading instance file: {str(e)}")
        sys.exit(1)
    
    # Solve instance
    solver, solution = solve(instance, solver_type, active_constraints)
    
    if solution is None:
        print("Failed to solve the instance.")
        sys.exit(1)
    
    # Save solution
    try:
        solution.save(args.output_file, solver)
        print(f"\nSolution saved to {args.output_file}")
    except Exception as e:
        print(f"Error saving solution: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
