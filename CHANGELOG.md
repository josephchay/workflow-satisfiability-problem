# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed
- Segregated out and specified our current implementation of ORTools as UDPB (User-Dependent Pseudo-Boolean).
- Merged statiscs summary and metadata information to be saved together in a single file for better management.

### Improved
- Better implementation for Z3 solvers of both PBPB and UDPB encodings.
- Cleaner Code logic using mathematical symbols and representations instead of wording for shorter, precise, more accurate and research-based style.
- Improved `str` and `int` related logics for ORTools.
- Made statistics summary to be saved into json file format instead of MARKDOWN report.

### Refactoring
- Refactored the code to have each deserving components segregated into own files, clases, methods, and functions.
- Folder directories storing multiple related files.
- __init__.py initialization files for each directory, effectively turning each of them into a package.
- Moved root files to related respetive directories, effectively leaving only the `main.py` file in the root for easier terminal execution.
- Moved instance text files folder into a more appropriated embeded folder `assets`.
