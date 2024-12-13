import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import argparse
import time
from tabulate import tabulate

from solver import read_file, solve_instance
from gui import WSPGUI


def solve_file(filename: str, verbose: bool = False) -> dict:
    """Solve a single WSP instance file"""
    try:
        # Read and parse the instance
        instance = read_file(filename)

        if verbose:
            print(f"\nProcessing file: {filename}")
            print("=" * 80)
            print(f"Steps: {instance.number_of_steps}")
            print(f"Users: {instance.number_of_users}")
            print(f"Constraints: {instance.number_of_constraints}")
            print("=" * 80)

        # Solve the instance and measure time
        start_time = time.time()
        result = solve_instance(instance)
        solve_time = time.time() - start_time

        # Add timing information to result
        result['time'] = solve_time
        result['filename'] = filename

        if verbose:
            print_result(result)

        return result

    except Exception as e:
        print(f"Error processing {filename}: {str(e)}")
        return {'status': 'error', 'message': str(e), 'filename': filename}


def solve_batch(filenames: list, verbose: bool = False) -> list:
    """Solve multiple WSP instance files"""
    results = []

    for filename in filenames:
        result = solve_file(filename, verbose)
        results.append(result)

    if verbose:
        print_summary(results)

    return results


def print_result(result: dict):
    """Print the result of a single instance"""
    from ortools.sat.python import cp_model

    print("\nResults:")
    print("=" * 80)

    if result['status'] in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("Solution found!")
        if result.get('assignments'):
            solution_data = [["s" + str(s), "u" + str(u)] for s, u in result['assignments']]
            print("\n" + tabulate(solution_data, headers=['Step', 'User'], tablefmt='grid'))
        else:
            print("\nNo assignments needed")
    else:
        print("Problem is unsatisfiable")

    print(f"\nExecution time: {result['time'] * 1000:.2f}ms")
    print("=" * 80)


def print_summary(results: list):
    """Print summary of multiple results"""
    from ortools.sat.python import cp_model

    print("\nSummary:")
    print("=" * 80)

    summary_data = []
    for result in results:
        status = "Error"
        if 'status' in result:
            if result['status'] in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                status = "Satisfiable"
            elif result['status'] == cp_model.INFEASIBLE:
                status = "Unsatisfiable"

        time_ms = result.get('time', 0) * 1000
        summary_data.append([
            result['filename'],
            status,
            f"{time_ms:.2f}ms"
        ])

    print(tabulate(summary_data,
                   headers=['Instance', 'Status', 'Time'],
                   tablefmt='grid'))
    print("=" * 80)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Workflow Satisfiability Problem Solver')
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface')
    parser.add_argument('--files', nargs='*', help='Input files to process')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    args = parser.parse_args()

    # Launch GUI if requested
    if args.gui:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        gui = WSPGUI()
        gui.show()
        sys.exit(app.exec_())

    # Process files if provided
    elif args.files:
        solve_batch(args.files, args.verbose)

    # Show usage if no arguments provided
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
