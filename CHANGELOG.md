# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-12-27

### Added
- `ortools-fast.py` (initially a testing script), which can now solve instance problem files accurately under 5 seconds for each instance file, including the display of metrics, calculations, violations, reasonings if UNSAT.
- Proper solution events and outcome logging (saving) to user-designated output text file for CLI.
- Scrollbar for each constraint analysis panel in GUI under statistics tab.
- Novel instance generator `factories/instance_generator.py` and its dedicated `generate.py` generator script.
- New constraints `WangLi`, `SUAL`, and `AssignmentDependent` constraints.
- Activation and Deactivation for new constraints in `main_cli.py` as CLI arguments.
- README file for the `assets/instances` directory.
- ignore `examples{20-29}.txt` files in the `.gitignore`.
- SUAL, WangLi, ADA constraints activation / deactivation compatibility with default instance files.
- SAT and UNSAT notes for Workload Distribution under statistics tab panel for GUI.
- Saving of SUAL, WangLi, and ADA constraint information to solution output for CLI.
- SUAL, WangLi, and ADA constraints to active / inactive consideration for CLI
- Instance generation configuration constants.
- Increment from 3 to 10 instance files generation for complex instances.
- Documentation for generating instances with classic constraints only in README.
- One Team constraint identification.
- SUAL, WangLi, and ADA constraints detailed analysis.
- Detailed analysis for new constraints in GUI.
- Metadata information handling for each instance processed.
- Visualization graphs for single and multiple instances (accumulated) over the number of instances solved.
- Proper Visualiation graphs for solution statistics, efficiency metrics, constraint analysis.
- Cache clearing for accumulated solved instances for visualisation.
- New plots tab for the GUI to directly visualize the each of the saved files for the user.
- User Authorization, Step Authorization, Authorization Density, Constraint Comparison plot graphs for visualization.
- Line graph visualization plots for Problem Size and Workload Distribution.
- Supplementary bar graph visualization plot for Solution Statistics for better visual aid by enabling better visibility of each component under each instance.
- Z3 Solver with Variable and Constraint managers, with tailored and dedicated constraint handling logic for the solver itself.
- DEAP Genetic algorithm solver with optimzied and best hyperparameters via tuning and experimentation.
- Gurobi algorithm and solver with likewise its own constraints handlings.
- Simulated Annealing as a metaheuristic solver, further enhanced from just merely heuristic algorithm solution as a deeper dive provides a more enhancde solution.
- SAT4J as a boolean based solution as an alternative an rival competition to OR-Tools for comparison and analysis on both of their performance.
- PuLP as an integer based solution as a rival solution towards Gurobi which is also another integer based solution as it uses the CBC, short for Coin-or branch-and-cut, presenting a rather much unique implementation which can be more suitable towards WSP problems.
- Bayesian network using PGM as its based, with use of Array-based approach, capable of solving the Pigeon-hole problem with tailored principle towards our WSP.

### Changed
- Updated the GUI `views.py` and `controllers.py` to fit in to our new solver solution (`ortools-fast.py` but now in a dynamic and versatile way).
- Updated `README.md`.
- Instance Generator includes generation for OneTeam Constraint.
- `INSTANCE_METADATA` constant reflecting accurate results based on practicalized theoretical calculations.
- Update dislpay on solved instance file on the results tab of the GUI.
- UNSAT Solution output from CLI will still display the solver used.
- Store value for `parse_arg` for SUAL, WangLi, and ADA arguments in `main_cli.py`.
- ADA constraint name display for activation / deactivation panel in GUI.
- Made OR-Tools CP solver use a more specific variable manager dedicated to it.
- Imports `networkx` as `nx` for `bayesian_network_constraints.py`

### Improvement
- Modified metric information in `metadata.py` and how its handled in the `controllers.py`.
- Updated statistics tab for thorough information metrics display.
- Updated CLI `main_cli.py` script to properly handle solver, solution, and its verification.
- Added statistics visibility for UNSAT results in the statistics tab of GUI.
- Introduced Separation of Concerns (SOC) for our `VariableManager` class.
- Better large complex instance generated content for instance examples.
- New oprimized generation script.
- OneTeam constraint in statistics tab of GUI now has header for each component displayed.
- Updated how Authorization Density visualiation plots the graph.
- Turned Solution statistics graph to line plots with more sophisticated informative metrics.
- Constraint distribution graph checks whether if the instance have that constraint or not, if it does not have, then does not display that bar for that instance, and if the constraint type is present but deactivated, then displays a gray bar for that instance.
- Constraint comparison checks whether if the instance contains each constraint or not, if it does not have, then that type of constraint is not counted into the respective instance.
- Better constraint distribution tracking in the OR-Tools CP solver.
- Include metadata for constraint distribution and comparison in the saving of Metada handlings.
- Made `plot_constraint_distribution` to be able to handle larger instances.
- Changed solver type for Bayesian network from `PGM_PY` to `BAYESIAN_NETWORK` to better reflect on implementation.

### Removed
- Removed unnecessary title header description for each instance.
- No longer needed Java error log file: `hs_err_pid38680.log`.

### Refactoring
- Introduced `InstanceParser` class for better readability for use for global function `parse_instance_file`.
- Introduced SOC (Separation of Concerns) via segregated methods for `Instance` class.
- Ensured the Sidebar having a fix width and does not change upon solver selections.
- Removed `tracker.py` since the Solution and its verifier are handled in `typings/solution.py`.
- Removed `ortools-fast.py` after integrating it into the mainstream solvers.
- Moved `jvm.py` to utils and removed `initializers` directory.
- Segregated our Constraint classes from the `ConstraintManager` class to `BaseConstraint`, `AuthorizationConstraint`, `BindingOfDutyConstraint`, `SeperationOfDutyConstraint`, `AtMostKConstraint`, `OneTeamConstraint` class.
- Renamed `constraint_comparison.png` file and its related components to `constraint_activation.png`.
- Shorten method naming for `Metadatahandler` for more definitive and meaningful projection and usage.
- Segregated out constraint classes, and variables, for multi-solvers.

### Fixed
- Ensured solvers compatibility and solution processing and functionable with the GUI.
- Included Authorisation into Constraint Count (as should - presented by default instance files) for generated instance files.

## [0.1.0] - 2024-12-22

### Added
- GUI component
    1. Replacement of old console UI
    2. Constraint selection on left panel
    3. Results display in the main panel
    4. Statistics on usage, violations, and adherence in the main panel.
    5. Progress feedback and bar at the bottom of the main panel.
    6. Added formatted Table design for results.

- Number of solutions found and whether if its Unique or not (single solution) - displayed on the statistics tab
- Instance details to displayed on "instance details" new tab to ensure that information about the particularly instance before processing it
- New Constraint Satisfaction (CS) encoding for ORTools
- New Pattern-Based Pseudo-Boolean (PBPB) encoding for ORTools
- Implementation of Z3 Solvers
- New PBPB encoding for Z3 Solver
- New UDPB encoding for Z3 Solver
- `get_M()` function to handle M-variable access regardless of step order.
- Metadata with detailed metrics information based on each instance solution
- Graph visualizations on information of each instance.
- Instance-specific metrics collection for visualization and metadata storage.
- User distribution, metrics, and constraint satisfaction metadata added to be recorded for visualiations.
- More information with indentation of groups of information under the statistics tab window.
- SAT4J Pattern-Based Psuedo-Boolean (PBPB) and User-Dependent Psuedo-Boolean (UDPB)
- `LICENSE` and `editorconfig` files.
- Console User interface with instance file parsing selection.

### Changed
- Segregated out and specified our current implementation of ORTools as UDPB (User-Dependent Pseudo-Boolean).
- Merged statiscs summary and metadata information to be saved together in a single file for better management.
- Utilize mandatory argument parsing for input and output files for CLI.

### Improved
- Better implementation for Z3 solvers of both PBPB and UDPB encodings.
- Cleaner Code logic using mathematical symbols and representations instead of wording for shorter, precise, more accurate and research-based style.
- Improved `str` and `int` related logics for ORTools.
- Made statistics summary to be saved into json file format instead of MARKDOWN report.
- Ensure that `SolutionCollector` class properly handles array dimensions.
- Logics for SAT4J now able to solve Instance 16, 17, 18, 19 within matter of 1 second.
- Resolved At-Most-K violations for SAT4J PBPB implementation.
- Updated logic for all encodings for PBPB, UDPB, CS, and solvers for Z3, OR-tools, and SAT4J.
- Supplemented changes for each of the related files that are linked to these solvers and their new encodings.
- Better visuals with better section headings, font sizes, different colorings, symbols usage for the statistics tab of the GUI.
- Instance file selection now reflects on the results tab panel.
- Constraint activation / deactivation filtering in `controllers.py`
- Use of `parse_arg` for better argument parsing for `main_cli.py`
- Enabled constraint activation and deactivation via CLI arguments.

### Refactoring
- Refactored the code to have each deserving components segregated into own files, clases, methods, and functions.
- Folder directories storing multiple related files.
- __init__.py initialization files for each directory, effectively turning each of them into a package.
- Moved root files to related respetive directories, effectively leaving only the `main.py` file in the root for easier terminal execution.
- Moved instance text files folder into a more appropriated embeded folder `assets`.
