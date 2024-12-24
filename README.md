# Workflow Satisfiability Problem (WSP) Solver

## Overview

A powerful WSP tooling system that optimizes complex multi-user task allocations using advanced constraint satisfaction techniques. The tool supports multiple solving strategies, handles intricate organizational constraints, and provides comprehensive analytics through both graphical and command-line interfaces. 

Designed for researchers and practitioners in workflow management, access control, and optimization, this solver leverages state-of-the-art algorithms to tackle challenging resource allocation problems.

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

#### Instance Generation

The script `generate.py` generates Workflow Satisfiability Problem (WSP) instances with varying sizes and constraint types, using our novel `factories/instance_generator.py` generator.

##### Generating Standard Instances

Basic Usage:
```bash
python generate.py
```

This will create 10 instances (example20.txt through example29.txt) with varying combinations of constraints and moderate sizes.

##### Generating Complex Instances

To generate large instances with specific line count requirements:

```bash
python generate.py --large
```
or 
```bash
python generate.py --l
```

For the entire list of options, check out the `parse_arguments` method in `generate.py`.

Standard instances will generate:
**Examples 20-29**: At least 20 lines each

Complex instances will generate:

**Examples 20-23**: At least 300 lines each
**Examples 24-26**: At least 600 lines each
**Examples 27-29**: At least 1000 lines each

Each generated file will follow this naming convention:

`example{N}.txt where N starts from 20`

##### Monitoring Progress (Complex Instances)

The `-l` script provides progress updates during generation:

- Shows file being generated
- Reports actual line count
- Indicates if regeneration is needed to meet size requirements
- Displays final parameters used for each instance

##### Output Location

All generated instances will be saved in the assets/instances directory. The directory will be created automatically if it doesn't exist.

##### Instance Types

The generator creates different types of instances:

**Balanced**: Even distribution of all constraint types
**SUAL-focused**: More Super-User-At-Least constraints
**WL-focused**: More Wang-Li constraints
**ADA-focused**: More Assignment-Dependent-Authorization constraints
**Mixed**: Varied distribution of constraints

#### Solving Instances

Basic usage:
```bash
python main_cli.py assets/instances/example17.txt results/solution17.txt
```

##### Command-Line Options

- `-s, --solver`: Select solver type
```bash
python main_cli.py assets/instances/example17.txt results/solution17.txt -s "OR-Tools (PBPB)"
```

- Constraint toggles:
```bash
# Disable specific constraints
python main_cli.py assets/instances/example17.txt results/solution17.txt --no-sod --no-bod
```

```bash
# Disable more specific constraints
python main_cli.py assets/instances/example17.txt results/solution17.txt --no-sod --no-bod
```

For the entire list of options, check out the `parse_arguments` method in `main_cli.py`.

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
Super-user-at-least 3 s1 s2 s3 (u1 u2 u3)
Wang-li s1 s2 (u1 u2) (u3 u4 u5)
Assignment-dependent s1 s2 (u1 u2) (u3 u4)
```

### Constraint Types

1. **Authorizations**: Restrict which users can perform specific steps
2. **Separation of Duty (SoD)**: Ensure certain steps are performed by different users
3. **Binding of Duty (BoD)**: Ensure certain steps are performed by the same user
4. **At-Most-K**: Limit the number of users assigned to a set of steps
5. **One-Team**: Ensure steps are assigned to users from the same team
6. **Super-User-At-Least (SUAL)**: Require super users if step assignments fall below a threshold
7. **Wang-Li (WL)**: Ensure steps are performed within the same department
8. **Assignment-Dependent Authorization (ADA)**: Make step authorizations dependent on other assignments

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

Wholeheartedly, I greatly and gratefully attribute this work to Professor Dr. Doreen Sim for her expertise with continuous inspiration and supervision.
