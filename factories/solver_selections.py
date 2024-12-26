import jpype

from constants import SolverType
from utils import init_jvm
from solvers import BaseSolver


class SolverFactory:
    """Factory for creating WSP solvers"""
    
    def __init__(self):
        # Try to initialize JVM at factory creation
        try:
            # SAT4J requires a unique manual instantiation of the JVM
            init_jvm()
        except FileNotFoundError as e:
            print(f"Warning: {str(e)}")
        except Exception as e:
            print(f"Warning: Failed to initialize JVM: {str(e)}")

        # Import solvers only when needed to avoid unnecessary dependencies
        self.solvers = {}
        
    def _import_solver(self, solver_type: SolverType):
        """Import respective solver class"""
        from solvers import ORToolsCPSolver as solver # Default solver
            
        self.solvers[solver_type] = solver

    def create_solver(self, solver_type: SolverType, instance, active_constraints, gui_mode: bool = False) -> BaseSolver:
        """Get solver instance for specified type"""
        self._import_solver(solver_type)
        
        if solver_type in [SolverType.SAT4J]:
            if not jpype.isJVMStarted():
                raise RuntimeError(
                    "JVM not initialized. Please ensure sat4j-pb.jar is in the project root."
                )

        return self.solvers[solver_type](instance, active_constraints, gui_mode)
