import os
import random
import argparse

from factories import InstanceGenerator


def generate_instances():
    # Create instances directory if it doesn't exist
    os.makedirs("assets/instances", exist_ok=True)
    
    # Instance generation parameters
    instance_configs = [
        # (k, n, config_description)
        (8, 20, "small_mixed"),
        (10, 30, "medium_mixed"),
        (12, 40, "large_mixed"),
        (15, 45, "extra_large_mixed"),
        (10, 25, "sual_heavy"),
        (12, 35, "wl_heavy"),
        (8, 24, "ada_heavy"),
        (10, 30, "classic_heavy"),
        (12, 36, "balanced_mixed"),
        (15, 50, "large_balanced")
    ]
    
    for idx, (k, n, config) in enumerate(instance_configs, start=20):  # Start from 20 to avoid overwriting instructed given example instances.
        generator = InstanceGenerator(k, n, seed=idx)
        
        # Base authorization density
        auth_density = 0.3  # 30% of users authorized for each step
        
        # Different constraint mixes based on configuration
        if config == "small_mixed":
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=3,
                num_bod=2,
                num_atmost=1,
                num_sual=1,
                num_wangli=1,
                num_ada=1
            )
        elif config == "medium_mixed":
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=4,
                num_bod=3,
                num_atmost=2,
                num_sual=2,
                num_wangli=1,
                num_ada=2
            )
        elif config == "large_mixed":
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=5,
                num_bod=3,
                num_atmost=2,
                num_sual=3,
                num_wangli=2,
                num_ada=2
            )
        elif config == "extra_large_mixed":
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=6,
                num_bod=4,
                num_atmost=3,
                num_sual=3,
                num_wangli=2,
                num_ada=3
            )
        elif config == "sual_heavy":
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=2,
                num_bod=1,
                num_atmost=1,
                num_sual=4,  # More SUAL constraints
                num_wangli=1,
                num_ada=1
            )
        elif config == "wl_heavy":
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=2,
                num_bod=2,
                num_atmost=1,
                num_sual=1,
                num_wangli=4,  # More Wang-Li constraints
                num_ada=1
            )
        elif config == "ada_heavy":
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=2,
                num_bod=1,
                num_atmost=1,
                num_sual=1,
                num_wangli=1,
                num_ada=4  # More ADA constraints
            )
        elif config == "classic_heavy":
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=5,  # More classic constraints
                num_bod=4,
                num_atmost=3,
                num_sual=1,
                num_wangli=1,
                num_ada=1
            )
        elif config == "balanced_mixed":
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=3,
                num_bod=2,
                num_atmost=2,
                num_sual=2,
                num_wangli=2,
                num_ada=2
            )
        else:  # large_balanced
            instance = generator.add_constraints(
                auth_density=auth_density,
                num_sod=4,
                num_bod=3,
                num_atmost=3,
                num_sual=3,
                num_wangli=3,
                num_ada=3
            )
            
        # Write instance to file
        filename = os.path.join("assets/instances", f"example{idx}.txt")
        generator.write_instance(filename, instance)
        print(f"Generated {filename} with configuration {config}")


def generate_complex_instances():
    """Generate larger instances with specific line count requirements"""
    # Create instances directory if it doesn't exist
    os.makedirs("assets/instances", exist_ok=True)
    
    # Instance configs tuned for size and solvability
    # Format: (k, n, min_lines, auth_density, users_per_dept, multiplier)
    instance_configs = [
        # 300+ line instances (20-23)
        (25, 80, 300, 0.25, 15, 8, "medium_balanced"),
        (25, 85, 300, 0.25, 15, 8, "sual_focused"),
        (28, 90, 300, 0.25, 18, 8, "wl_focused"),
        (30, 90, 300, 0.25, 18, 8, "ada_focused"),
        
        # 600+ line instances (24-26)
        (35, 120, 600, 0.2, 20, 12, "large_balanced"),
        (38, 130, 600, 0.2, 22, 12, "large_mixed"),
        (40, 140, 600, 0.2, 25, 12, "complex_balanced"),
        
        # 1000+ line instances (27-29)
        (45, 180, 1000, 0.15, 30, 20, "extra_large_balanced"),
        (48, 200, 1000, 0.15, 35, 20, "extra_large_mixed"),
        (50, 220, 1000, 0.15, 40, 20, "massive_balanced")
    ]
    
    for idx, (k, n, min_lines, auth_density, dept_size, initial_multiplier, config) in enumerate(instance_configs, start=20):
        print(f"\nGenerating example{idx}.txt...")
        
        # Calculate constraint counts based on desired size
        base_count = k
        multiplier = initial_multiplier
        retry_count = 0
        
        while True:
            retry_count += 1
            if retry_count % 5 == 0:  # Show progress every 5 attempts
                print(f"Attempt {retry_count}...")
            
            generator = InstanceGenerator(k, n, seed=random.randint(1, 10000))
            
            if "balanced" in config:
                instance = generator.add_constraints(
                    auth_density=auth_density,
                    num_sod=int(base_count * multiplier),
                    num_bod=int(base_count * (multiplier // 2)),
                    num_atmost=int(base_count * (multiplier // 2)),
                    num_sual=int(base_count * (multiplier // 2)),
                    num_wangli=int(base_count * (multiplier // 2)),
                    num_ada=int(base_count * (multiplier // 2)),
                    users_per_dept=dept_size
                )
            elif "sual_focused" in config:
                instance = generator.add_constraints(
                    auth_density=auth_density,
                    num_sod=int(base_count * (multiplier // 2)),
                    num_bod=int(base_count * (multiplier // 4)),
                    num_atmost=int(base_count * (multiplier // 4)),
                    num_sual=int(base_count * multiplier),
                    num_wangli=int(base_count * (multiplier // 4)),
                    num_ada=int(base_count * (multiplier // 4)),
                    users_per_dept=dept_size
                )
            elif "wl_focused" in config:
                instance = generator.add_constraints(
                    auth_density=auth_density,
                    num_sod=int(base_count * (multiplier // 2)),
                    num_bod=int(base_count * (multiplier // 4)),
                    num_atmost=int(base_count * (multiplier // 4)),
                    num_sual=int(base_count * (multiplier // 4)),
                    num_wangli=int(base_count * multiplier),
                    num_ada=int(base_count * (multiplier // 4)),
                    users_per_dept=dept_size
                )
            elif "ada_focused" in config:
                instance = generator.add_constraints(
                    auth_density=auth_density,
                    num_sod=int(base_count * (multiplier // 2)),
                    num_bod=int(base_count * (multiplier // 4)),
                    num_atmost=int(base_count * (multiplier // 4)),
                    num_sual=int(base_count * (multiplier // 4)),
                    num_wangli=int(base_count * (multiplier // 4)),
                    num_ada=int(base_count * multiplier),
                    users_per_dept=dept_size
                )
            else:  # mixed variants
                instance = generator.add_constraints(
                    auth_density=auth_density,
                    num_sod=int(base_count * multiplier),
                    num_bod=int(base_count * (multiplier // 2)),
                    num_atmost=int(base_count * (multiplier // 2)),
                    num_sual=int(base_count * (multiplier // 1.5)),
                    num_wangli=int(base_count * (multiplier // 1.5)),
                    num_ada=int(base_count * (multiplier // 1.5)),
                    users_per_dept=dept_size
                )
            
            # Write instance to temporary file to check size
            temp_filename = os.path.join("assets/instances", f"temp_{idx}.txt")
            generator.write_instance(temp_filename, instance)
            
            # Check file size
            with open(temp_filename, 'r') as f:
                num_lines = sum(1 for _ in f)
                
            os.remove(temp_filename)
            
            # If instance meets size requirements, save it
            if num_lines >= min_lines and num_lines <= min_lines * 2:  # Added upper bound
                filename = os.path.join("assets/instances", f"example{idx}.txt")
                generator.write_instance(filename, instance)
                print(f"\nSuccess! Generated {filename}")
                print(f"Lines: {num_lines} (required: {min_lines})")
                print(f"Parameters: k={k}, n={n}, auth_density={auth_density}")
                print(f"Constraints multiplier: {multiplier}")
                print(f"Configuration: {config}")
                print(f"Attempts needed: {retry_count}")
                break
            elif num_lines > min_lines * 2:  # Too many lines, decrease multiplier
                multiplier = max(4, multiplier - 2)
            else:  # Not enough lines, increase multiplier
                multiplier += 2
                if retry_count % 10 == 0:
                    print(f"Increasing multiplier to {multiplier}")


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Generate Workflow Satisfiability Problem (WSP) instances'
    )
    
    # Optional constraint toggle arguments
    parser.add_argument('-l', '--large', 
                        action='store_true', 
                        dest='large',  # This sets the attribute name
                        help='Generate large instances')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    if args.large:
        generate_complex_instances()
    else:
        generate_instances()
