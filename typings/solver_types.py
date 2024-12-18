from enum import Enum


class WSPSolverType(Enum):
    ORTOOLS_CS = "OR-Tools (CS)"
    ORTOOLS_PBPB = "OR-Tools (PBPB)"
    ORTOOLS_UDPB = "OR-Tools (UDPB)"
    Z3_PBPB = "Z3 (PBPB)"
    Z3_UDPB = "Z3 (UDPB)"
    SAT4J_PBPB = "SAT4J (PBPB)"
    SAT4J_UDPB = "SAT4J (UDPB)"
