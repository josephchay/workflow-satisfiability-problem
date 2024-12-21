import os
import sys
from app import WSPView, WSPController
from typings import WSPSolverType
from factories import WSPSolverFactory


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    instructions = {}

    try:
        from ortools.sat.python import cp_model
    except ImportError:
        missing_deps.append("or-tools")
        instructions["or-tools"] = "pip install ortools"

    try:
        import z3
    except ImportError:
        missing_deps.append("z3-solver")
        instructions["z3-solver"] = "pip install z3-solver"

    try:
        import jpype
    except ImportError:
        missing_deps.append("jpype1")
        instructions["jpype1"] = "pip install jpype1"

    # Check for SAT4J jar file
    if not os.path.exists(os.path.join("assets", "sat4j-pb.jar")):
        missing_deps.append("sat4j-pb.jar")
        instructions["sat4j-pb.jar"] = "Download from https://www.sat4j.org/"

    return missing_deps, instructions


def main():
    # Check dependencies
    missing_deps, instructions = check_dependencies()

    if missing_deps:
        print("Missing dependencies:")
        for dep in missing_deps:
            print(f" - {dep}: {instructions.get(dep, 'No installation instructions available')}")
        sys.exit(1)

    try:
        # Create view
        app = WSPView()
        
        # Create controller with solver factory
        factory = WSPSolverFactory()
        controller = WSPController(app, factory)

        # Initialize solver type combobox in view
        app.solver_type.configure(values=[st.value for st in WSPSolverType])
        app.solver_type.set(controller.current_solver_type.value)  # Set default solver

        # Connect solver change callback
        app.solver_type.configure(command=controller.on_solver_change)

        # Start application
        app.mainloop()

    except Exception as e:
        print(f"Error starting application: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
