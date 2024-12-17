# main.py
import os
import sys
from views import WSPView
from controllers import WSPController
from typings import SolverType
from factories import WSPSolverFactory


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        missing_deps.append("or-tools")
    
    try:
        import z3
    except ImportError:
        missing_deps.append("z3-solver")
        
    # # Check for SAT4J jar file
    # if not os.path.exists("sat4j-pb.jar"):
    #     missing_deps.append("sat4j-pb.jar")
    
    return missing_deps

def main():
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print("Missing dependencies:", ", ".join(missing_deps))
        print("Please install missing dependencies:")
        print("pip install or-tools z3-solver")
        print("Download sat4j-pb.jar from https://www.sat4j.org/")
        sys.exit(1)
    
    try:
        # Create view
        app = WSPView()
        
        # Create controller with solver factory
        factory = WSPSolverFactory()
        controller = WSPController(app, factory)
        
        # Initialize solver type combobox in view
        app.solver_type.configure(values=[st.value for st in SolverType])
        app.solver_type.set(SolverType.ORTOOLS_CS.value)  # Set default solver
        
        # Connect solver change callback
        app.solver_type.configure(command=controller.on_solver_change)
        
        # Start application
        app.mainloop()
        
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
