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
            instance = generator.generate_instance(
                auth_density=auth_density,
                num_sod=3,
                num_bod=2,
                num_atmost=1,
                num_sual=1,
                num_wangli=1,
                num_ada=1
            )
        elif config == "medium_mixed":
            instance = generator.generate_instance(
                auth_density=auth_density,
                num_sod=4,
                num_bod=3,
                num_atmost=2,
                num_sual=2,
                num_wangli=1,
                num_ada=2
            )
        elif config == "large_mixed":
            instance = generator.generate_instance(
                auth_density=auth_density,
                num_sod=5,
                num_bod=3,
                num_atmost=2,
                num_sual=3,
                num_wangli=2,
                num_ada=2
            )
        elif config == "extra_large_mixed":
            instance = generator.generate_instance(
                auth_density=auth_density,
                num_sod=6,
                num_bod=4,
                num_atmost=3,
                num_sual=3,
                num_wangli=2,
                num_ada=3
            )
        elif config == "sual_heavy":
            instance = generator.generate_instance(
                auth_density=auth_density,
                num_sod=2,
                num_bod=1,
                num_atmost=1,
                num_sual=4,  # More SUAL constraints
                num_wangli=1,
                num_ada=1
            )
        elif config == "wl_heavy":
            instance = generator.generate_instance(
                auth_density=auth_density,
                num_sod=2,
                num_bod=2,
                num_atmost=1,
                num_sual=1,
                num_wangli=4,  # More Wang-Li constraints
                num_ada=1
            )
        elif config == "ada_heavy":
            instance = generator.generate_instance(
                auth_density=auth_density,
                num_sod=2,
                num_bod=1,
                num_atmost=1,
                num_sual=1,
                num_wangli=1,
                num_ada=4  # More ADA constraints
            )
        elif config == "classic_heavy":
            instance = generator.generate_instance(
                auth_density=auth_density,
                num_sod=5,  # More classic constraints
                num_bod=4,
                num_atmost=3,
                num_sual=1,
                num_wangli=1,
                num_ada=1
            )
        elif config == "balanced_mixed":
            instance = generator.generate_instance(
                auth_density=auth_density,
                num_sod=3,
                num_bod=2,
                num_atmost=2,
                num_sual=2,
                num_wangli=2,
                num_ada=2
            )
        else:  # large_balanced
            instance = generator.generate_instance(
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
    # Create instances directory if it doesn't exist
    os.makedirs("assets/instances", exist_ok=True)
    
    # Instance configs tuned for size and solvability
    # (k, n, min_lines, auth_density, config_name)
    instance_configs = [
        # 300+ line instances (20-23)
        (20, 50, 300, 0.3, "medium_balanced"),
        (20, 60, 300, 0.25, "sual_focused"),
        (25, 55, 300, 0.3, "wl_focused"),
        (22, 65, 300, 0.25, "ada_focused"),
        
        # 600+ line instances (24-26)
        (30, 80, 600, 0.25, "large_balanced"),
        (35, 90, 600, 0.2, "large_mixed"),
        (32, 85, 600, 0.25, "complex_balanced"),
        
        # 1000+ line instances (27-29)
        (40, 100, 1000, 0.2, "extra_large_balanced"),
        (45, 100, 1000, 0.2, "extra_large_mixed"),
        (42, 100, 1000, 0.2, "massive_balanced")
    ]
    
    for idx, (k, n, min_lines, auth_density, config) in enumerate(instance_configs, start=20):
        print(f"\nGenerating example{idx}.txt...")
        
        while True:
            generator = InstanceGenerator(k, n, seed=random.randint(1, 10000))
            
            # Calculate constraint counts based on desired size
            base_count = k // 2
            
            if "balanced" in config:
                # Even distribution of constraints
                instance = generator.generate_instance(
                    auth_density=auth_density,
                    num_sod=base_count * 2,
                    num_bod=base_count,
                    num_atmost=base_count,
                    num_sual=base_count,
                    num_wangli=base_count,
                    num_ada=base_count
                )
            elif "sual_focused" in config:
                instance = generator.generate_instance(
                    auth_density=auth_density,
                    num_sod=base_count,
                    num_bod=base_count // 2,
                    num_atmost=base_count // 2,
                    num_sual=base_count * 3,  # More SUAL constraints
                    num_wangli=base_count // 2,
                    num_ada=base_count // 2
                )
            elif "wl_focused" in config:
                instance = generator.generate_instance(
                    auth_density=auth_density,
                    num_sod=base_count,
                    num_bod=base_count // 2,
                    num_atmost=base_count // 2,
                    num_sual=base_count // 2,
                    num_wangli=base_count * 3,  # More Wang-Li constraints
                    num_ada=base_count // 2
                )
            elif "ada_focused" in config:
                instance = generator.generate_instance(
                    auth_density=auth_density,
                    num_sod=base_count,
                    num_bod=base_count // 2,
                    num_atmost=base_count // 2,
                    num_sual=base_count // 2,
                    num_wangli=base_count // 2,
                    num_ada=base_count * 3  # More ADA constraints
                )
            else:  # mixed variants
                instance = generator.generate_instance(
                    auth_density=auth_density,
                    num_sod=base_count * 2,
                    num_bod=base_count,
                    num_atmost=base_count,
                    num_sual=int(base_count * 1.5),
                    num_wangli=int(base_count * 1.5),
                    num_ada=int(base_count * 1.5)
                )
            
            # Write instance to temporary file to check size
            temp_filename = os.path.join("assets/instances", f"temp_{idx}.txt")
            generator.write_instance(temp_filename, instance)
            
            # Check file size
            with open(temp_filename, 'r') as f:
                num_lines = sum(1 for _ in f)
                
            os.remove(temp_filename)
            
            # If instance meets size requirements, save it
            if num_lines >= min_lines:
                filename = os.path.join("assets/instances", f"example{idx}.txt")
                generator.write_instance(filename, instance)
                print(f"Generated {filename} with {num_lines} lines ({config})")
                print(f"Parameters: k={k}, n={n}, auth_density={auth_density}")
                break
            else:
                print(f"Retrying {idx} - got {num_lines} lines, need {min_lines}")


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
