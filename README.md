# Workflow Satisfiability Problem (WSP) Solver

## Overview

This Workflow Satisfiability Problem (WSP) solver is a sophisticated tool designed to solve complex workflow allocation problems with multiple constraints. The solver supports various encoding strategies and constraint types to handle real-world workflow scenarios.

## Features

- Multiple solver implementations
- Flexible constraint handling
- Detailed solution statistics
- Visualization of results
- Command-line and graphical interfaces

### Supported Solver Types

- OR-Tools Constraint Satisfaction (CS)
- OR-Tools Pattern-Based Pseudo-Boolean (PBPB)
- OR-Tools User-Dependent Pseudo-Boolean (UDPB)
- Z3 Pattern-Based Pseudo-Boolean (PBPB)
- Z3 User-Dependent Pseudo-Boolean (UDPB)
- SAT4J Pattern-Based Pseudo-Boolean (PBPB)
- SAT4J User-Dependent Pseudo-Boolean (UDPB)

### Constraint Types

1. **Authorizations**: Restrict which users can perform specific steps
2. **Separation of Duty**: Ensure certain steps are performed by different users
3. **Binding of Duty**: Ensure certain steps are performed by the same user
4. **At-Most-K**: Limit the number of users assigned to a set of steps
5. **One-Team**: Ensure steps are assigned to users from the same team

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Dependencies

Install required dependencies:
```bash
pip install -r requirements.txt
```

### Download Additional Requirements

1. Download `sat4j-pb.jar` from [SAT4J website](https://www.sat4j.org/)
2. Place the JAR file in the `assets` directory of the project

## Usage

### Graphical User Interface (GUI)

Launch the application:
```bash
python main.py
```

### Command-Line Interface (CLI)

Basic usage:
```bash
python main_cli.py assets/instances/example17.txt results/solution17.txt
```

#### Command-Line Options

- `-s, --solver`: Select solver type
```bash
python main_cli.py assets/instances/example17.txt results/solution17.txt -s "OR-Tools (PBPB)"
```

- Constraint toggles:
```bash
# Disable specific constraints
python main_cli.py assets/instances/example17.txt results/solution17.txt --no-sod --no-bod
```

### Solver Type Selection

Available solver types:
- `OR-Tools (CS)`
- `OR-Tools (PBPB)`
- `OR-Tools (UDPB)`
- `Z3 (PBPB)`
- `Z3 (UDPB)`
- `SAT4J (PBPB)`
- `SAT4J (UDPB)`

## Input File Format

The solver uses a specific text-based input format:

```
#Steps: <number of steps>
#Users: <number of users>
#Constraints: <number of constraints>

Authorisations u1 s1 s2
Separation-of-duty s1 s2
Binding-of-duty s3 s4
At-most-k 2 s1 s2 s3
One-team s4 s5 (u1 u2) (u3 u4 u5)
```

### Constraint Types Explained

- **Authorisations**: Specify which steps a user can perform
- **Separation-of-duty**: Ensure steps are not performed by the same user
- **Binding-of-duty**: Ensure steps are performed by the same user
- **At-most-k**: Limit users for a set of steps
- **One-team**: Ensure steps are performed by users from specific teams

## Output

The solver generates:
- Solution file with step-user assignments
- Detailed statistics
- Optional visualizations

## Visualization

The solver can generate various visualizations:
- Scaling analysis
- Constraint impact
- Solution characteristics
- Instance complexity metrics

## Performance Considerations

- Solver performance varies with instance problem complexity
- More constraints generally increase solving time
- Some solver types are more efficient for specific problem structures

## License

Check out `LICENSE` under this project.

## Authors

- Joseph E. Chay (hcyjc11@nottingham.edu.my)

## Acknowledgments

Wholeheartedly, I greatly and gratefully attribute this work to Professor Dr. Doreen Sim for her continuous inspiration and supervision.
