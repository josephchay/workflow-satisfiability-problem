# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Refactoring
- Introduced `InstanceParser` class for better readability for use for global function `parse_instance_file`.
- Introduced SOC (Separation of Concerns) via segregated methods for `Instance` class.

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
