import jpype

from typings import WSPSolverType
from initializers import init_jvm
from solvers import BaseWSPSolver, ORToolsCSWSPSolver, ORToolsPBPBWSPSolver, ORToolsUDPBWSPSolver, Z3PBPBWSPSolver, Z3UDPBWSPSolver 


class WSPSolverFactory:
    """Factory for creating WSP solvers"""
    
    def __init__(self):
        # Try to initialize JVM at factory creation
        try:
            init_jvm()
        except FileNotFoundError as e:
            print(f"Warning: {str(e)}")
        except Exception as e:
            print(f"Warning: Failed to initialize JVM: {str(e)}")

        # Import solvers only when needed to avoid unnecessary dependencies
        self.solvers = {}
        
    def _import_solver(self, solver_type: WSPSolverType):
        """Import solver class based on type"""
        if solver_type not in self.solvers:
            if solver_type == WSPSolverType.ORTOOLS_CS:
                from solvers.ortools import ORToolsCSWSPSolver as solver
            elif solver_type == WSPSolverType.ORTOOLS_UDPB:
                from solvers.ortools import ORToolsUDPBWSPSolver as solver
            elif solver_type == WSPSolverType.ORTOOLS_PBPB:
                from solvers.ortools import ORToolsPBPBWSPSolver as solver
            elif solver_type == WSPSolverType.Z3_UDPB:
                from solvers.z3 import Z3UDPBWSPSolver as solver
            elif solver_type == WSPSolverType.Z3_PBPB:
                from solvers.z3 import Z3PBPBWSPSolver as solver
            elif solver_type == WSPSolverType.SAT4J_UDPB:
                from solvers.sat4j import SAT4JUDPBWSPSolver as solver
            elif solver_type == WSPSolverType.SAT4J_PBPB:
                from solvers.sat4j import SAT4JPBPBWSPSolver as solver
            else:
                raise ValueError(f"Unknown solver type: {solver_type}")
                
            self.solvers[solver_type] = solver
            
    def create_solver(self, solver_type: WSPSolverType, instance, active_constraints) -> BaseWSPSolver:
        """Get solver instance for specified type"""
        self._import_solver(solver_type)
        
        # For SAT4J solvers, verify JVM is available
        if solver_type in [WSPSolverType.SAT4J_PBPB, WSPSolverType.SAT4J_UDPB]:
            if not jpype.isJVMStarted():
                raise RuntimeError(
                    "JVM not initialized. Please ensure sat4j-pb.jar is in the project root."
                )

        return self.solvers[solver_type](instance, active_constraints)
