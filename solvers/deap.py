from typing import Dict
import time
from deap import base, creator, tools, algorithms
import random

from utils import log
from constants import SolverType
from solvers import BaseSolver
from constraints.deap_constraints import DEAPVariableManager, DEAPConstraintManager
from typings import Solution, UniquenessChecker, Verifier


class DEAPSolver(BaseSolver):
    """DEAP solver implementation for WSP instances"""
    SOLVER_TYPE = SolverType.DEAP

    """Main solver using DEAP genetic algorithm approach"""
    def __init__(self, instance, active_constraints: Dict[str, bool], gui_mode: bool = False):
        self.instance = instance
        self.active_constraints = active_constraints
        self.gui_mode = gui_mode
        
        # Setup DEAP components
        self.var_manager = DEAPVariableManager(instance)
        self.var_manager.create_variables()
        self.constraint_manager = DEAPConstraintManager(instance, self.var_manager)
        
        # GA parameters
        self.population_size = 300
        self.num_generations = 100
        self.crossover_prob = 0.7
        self.mutation_prob = 0.2
        
    def solve(self):
        """Main solving method using genetic algorithm"""
        start_time = time.time()
        
        try:
            # Setup evolution with active constraints
            is_feasible, errors = self.constraint_manager.setup_evolution(self.active_constraints)
            if not is_feasible:
                return self._handle_infeasible(start_time, errors)
            
            # Create initial population
            population = self.var_manager.toolbox.population_creator(n=self.population_size)
            
            # Evaluate initial population
            for individual in population:
                individual.fitness.values = self.constraint_manager.evaluate_fitness(individual)
            
            # Store initial best individual
            best_individual = tools.selBest(population, 1)[0]
            best_fitness = best_individual.fitness.values[0]
            
            # Evolution loop
            generation = 0
            stagnant_generations = 0
            while generation < self.num_generations and best_fitness > 0:
                generation += 1
                
                # Select next generation
                offspring = self.var_manager.toolbox.select(population, len(population))
                offspring = list(map(self.var_manager.toolbox.clone, offspring))
                
                # Apply crossover
                for child1, child2 in zip(offspring[::2], offspring[1::2]):
                    if random.random() < self.crossover_prob:
                        self.var_manager.toolbox.mate(child1, child2)
                        del child1.fitness.values
                        del child2.fitness.values
                
                # Apply mutation
                for mutant in offspring:
                    if random.random() < self.mutation_prob:
                        self.var_manager.toolbox.mutate(mutant)
                        del mutant.fitness.values
                
                # Evaluate offspring
                invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
                for individual in invalid_ind:
                    individual.fitness.values = self.constraint_manager.evaluate_fitness(individual)
                
                # Replace population
                population[:] = offspring
                
                # Update best solution
                current_best = tools.selBest(population, 1)[0]
                if current_best.fitness.values[0] < best_fitness:
                    best_individual = current_best
                    best_fitness = best_individual.fitness.values[0]
                    stagnant_generations = 0
                else:
                    stagnant_generations += 1
                    
                # Early stopping if no improvement
                if stagnant_generations >= 20:
                    break
            
            # Process final solution
            if best_fitness == 0:
                # Perfect solution found
                result = Solution.create_sat(
                    time.time() - start_time,
                    self.var_manager.get_assignment_from_solution(best_individual)
                )
            else:
                # No perfect solution found
                result = Solution.create_unsat(
                    time.time() - start_time,
                    reason="No solution satisfying all constraints found using genetic algorithm"
                )
            
            return result
            
        except Exception as e:
            return self._handle_error(start_time, e)
    