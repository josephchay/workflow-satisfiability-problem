from enum import Enum


class SolverType(Enum):
    ORTOOLS_CP = "OR-Tools"
    Z_THREE = "Z3"
    SAT4J = "SAT4J"
    GUROBI = "Gurobi"
    DEAP = "DEAP"
    HYPEROPT = "Hyperopt"
