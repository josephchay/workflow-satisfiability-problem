import os
import random
import argparse
from dataclasses import dataclass
from typing import Dict, Any

from factories import InstanceGenerator


"""This script generates Workflow Satisfiability Problem (WSP) instances using our own novel `InstanceGenerator` class in `factories/instance_generator.py`."""


@dataclass
class InstanceConfig:
    k: int  # Number of steps
    n: int  # Number of users
    description: str
    min_lines: int = 0  # For complex instances
    auth_density: float = 0.3
    dept_size: int = 0  # For complex instances
    multiplier: int = 0  # For complex instances


class Generator:
    def __init__(self, classic_only: bool = False):
        self.classic_only = classic_only
        
    def generate_constraint_mix(self, base_count: int, multiplier: int, config: str, dept_size: int = 15) -> Dict[str, Any]:
        """Generate constraint counts based on configuration"""
        base_constraints = {
            'auth_density': 0.3,
            'num_sod': 0,
            'num_bod': 0,
            'num_atmost': 0,
            'num_oneteam': 0
        }
        
        # Only add non-classic constraints if not in classic-only mode
        if not self.classic_only:
            base_constraints.update({
                'num_sual': 0,
                'num_wangli': 0,
                'num_ada': 0
            })

        if "balanced" in config:
            base_constraints.update({
                'num_sod': int(base_count * multiplier),
                'num_bod': int(base_count * (multiplier // 2)),
                'num_atmost': int(base_count * (multiplier // 2)),
                'num_oneteam': int(base_count * (multiplier // 2))
            })
            if not self.classic_only:
                base_constraints.update({
                    'num_sual': int(base_count * (multiplier // 2)),
                    'num_wangli': int(base_count * (multiplier // 2)),
                    'num_ada': int(base_count * (multiplier // 2))
                })
        elif "sual_focused" in config and not self.classic_only:
            base_constraints.update({
                'num_sod': int(base_count * (multiplier // 2)),
                'num_bod': int(base_count * (multiplier // 4)),
                'num_atmost': int(base_count * (multiplier // 4)),
                'num_oneteam': int(base_count * (multiplier // 4)),
                'num_sual': int(base_count * multiplier),
                'num_wangli': int(base_count * (multiplier // 4)),
                'num_ada': int(base_count * (multiplier // 4))
            })
        elif "wl_focused" in config and not self.classic_only:
            base_constraints.update({
                'num_sod': int(base_count * (multiplier // 2)),
                'num_bod': int(base_count * (multiplier // 4)),
                'num_atmost': int(base_count * (multiplier // 4)),
                'num_oneteam': int(base_count * (multiplier // 4)),
                'num_sual': int(base_count * (multiplier // 4)),
                'num_wangli': int(base_count * multiplier),
                'num_ada': int(base_count * (multiplier // 4))
            })
        elif "ada_focused" in config and not self.classic_only:
            base_constraints.update({
                'num_sod': int(base_count * (multiplier // 2)),
                'num_bod': int(base_count * (multiplier // 4)),
                'num_atmost': int(base_count * (multiplier // 4)),
                'num_oneteam': int(base_count * (multiplier // 4)),
                'num_sual': int(base_count * (multiplier // 4)),
                'num_wangli': int(base_count * (multiplier // 4)),
                'num_ada': int(base_count * multiplier)
            })
        else:  # mixed variants
            base_constraints.update({
                'num_sod': int(base_count * multiplier),
                'num_bod': int(base_count * (multiplier // 2)),
                'num_atmost': int(base_count * (multiplier // 2)),
                'num_oneteam': int(base_count * (multiplier // 2))
            })
            if not self.classic_only:
                base_constraints.update({
                    'num_sual': int(base_count * (multiplier // 1.5)),
                    'num_wangli': int(base_count * (multiplier // 1.5)),
                    'num_ada': int(base_count * (multiplier // 1.5))
                })

        # Add users_per_dept if needed
        if dept_size > 0:
            base_constraints['users_per_dept'] = dept_size

        return base_constraints

    def generate_instances(self):
        """Generate basic WSP instances"""
        os.makedirs("assets/instances", exist_ok=True)
        
        instance_configs = [
            InstanceConfig(8, 20, "small_mixed"),
            InstanceConfig(10, 30, "medium_mixed"),
            InstanceConfig(12, 40, "large_mixed"),
            InstanceConfig(15, 45, "extra_large_mixed"),
            
            # Constraint-Focused Instances
            InstanceConfig(10, 25, "sual_heavy"),
            InstanceConfig(12, 35, "wl_heavy"),
            InstanceConfig(8, 24, "ada_heavy"),
            
            # Classic and Balanced Configurations
            InstanceConfig(10, 30, "classic_heavy"),
            InstanceConfig(12, 36, "balanced_mixed"),
            InstanceConfig(15, 50, "large_balanced"),
        ]
        
        for idx, config in enumerate(instance_configs, start=20):
            generator = InstanceGenerator(config.k, config.n, seed=idx)
            constraints = self.generate_constraint_mix(
                base_count=config.k,
                multiplier=1,
                config=config.description
            )
            
            instance = generator.add_constraints(**constraints)
            filename = os.path.join("assets/instances", f"example{idx}.txt")
            generator.write_instance(filename, instance)
            print(f"Generated {filename} with configuration {config.description}")

    def generate_complex_instances(self):
        """Generate larger WSP instances"""
        os.makedirs("assets/instances", exist_ok=True)
        
        # Complex instance configurations
        instance_configs = [
            # 300+ line instances (first 3)
            InstanceConfig(25, 80, "medium_balanced", min_lines=300, auth_density=0.25, dept_size=15, multiplier=8),
            InstanceConfig(25, 85, "sual_focused", min_lines=300, auth_density=0.25, dept_size=15, multiplier=8),
            InstanceConfig(28, 90, "wl_focused", min_lines=300, auth_density=0.25, dept_size=18, multiplier=8),
            
            # 600+ line instances (next 3)
            InstanceConfig(35, 120, "large_balanced", min_lines=600, auth_density=0.2, dept_size=20, multiplier=12),
            InstanceConfig(38, 130, "large_mixed", min_lines=600, auth_density=0.2, dept_size=22, multiplier=12),
            InstanceConfig(40, 140, "ada_focused", min_lines=600, auth_density=0.2, dept_size=25, multiplier=12),
            
            # 1000+ line instances (final 4)
            InstanceConfig(45, 180, "extra_large_balanced", min_lines=1000, auth_density=0.15, dept_size=30, multiplier=20),
            InstanceConfig(48, 200, "extra_large_mixed", min_lines=1000, auth_density=0.15, dept_size=35, multiplier=20),
            InstanceConfig(50, 220, "sual_focused", min_lines=1000, auth_density=0.15, dept_size=40, multiplier=20),
            InstanceConfig(50, 220, "massive_balanced", min_lines=1000, auth_density=0.15, dept_size=40, multiplier=20)
        ]
        
        for idx, config in enumerate(instance_configs, start=20):
            print(f"\nGenerating example{idx}.txt...")
            
            base_count = config.k
            multiplier = config.multiplier
            retry_count = 0
            
            while True:
                retry_count += 1
                if retry_count % 5 == 0:
                    print(f"Attempt {retry_count}...")
                
                generator = InstanceGenerator(config.k, config.n, seed=random.randint(1, 10000))
                
                constraints = self.generate_constraint_mix(
                    base_count=base_count,
                    multiplier=multiplier,
                    config=config.description,
                    dept_size=config.dept_size
                )
                constraints['auth_density'] = config.auth_density
                
                instance = generator.add_constraints(**constraints)
                
                # Check instance size
                temp_filename = os.path.join("assets/instances", f"temp_{idx}.txt")
                generator.write_instance(temp_filename, instance)
                
                with open(temp_filename, 'r') as f:
                    num_lines = sum(1 for _ in f)
                
                os.remove(temp_filename)
                
                if config.min_lines <= num_lines <= config.min_lines * 2:
                    filename = os.path.join("assets/instances", f"example{idx}.txt")
                    generator.write_instance(filename, instance)
                    print(f"\nSuccess! Generated {filename}")
                    print(f"Lines: {num_lines} (required: {config.min_lines})")
                    print(f"Parameters: k={config.k}, n={config.n}, auth_density={config.auth_density}")
                    print(f"Configuration: {config.description}")
                    print(f"Attempts needed: {retry_count}")
                    break
                elif num_lines > config.min_lines * 2:
                    multiplier = max(4, multiplier - 2)
                else:
                    multiplier += 2
                    if retry_count % 10 == 0:
                        print(f"Increasing multiplier to {multiplier}")


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Generate Workflow Satisfiability Problem (WSP) instances'
    )
    
    parser.add_argument('-l', '--large', 
                       action='store_true',
                       help='Generate large instances')
    
    parser.add_argument('--classic-only',
                       action='store_true',
                       help='Generate instances with only classic constraints (no SUAL, WangLi, or ADA)')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    generator = Generator(classic_only=args.classic_only)
    
    if args.large:
        generator.generate_complex_instances()
    else:
        generator.generate_instances()
