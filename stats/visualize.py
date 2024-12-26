import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict
import os
import seaborn as sns
from pathlib import Path


class Visualizer:
    """Generates visualizations for WSP metadata"""
    
    def __init__(self, metadata_handler, output_dir: str = "results/plots"):
        self.metadata_handler = metadata_handler
        self.output_dir = output_dir

        os.makedirs(output_dir, exist_ok=True)
        
        # Set style with error handling
        try:
            plt.style.use('seaborn-v0_8-whitegrid')
        except:
            plt.style.use('default')
            plt.rcParams['axes.grid'] = True
            
        # Custom color scheme including a "NA" color
        self.colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c', '#34495e']
        self.na_color = '#95a5a6'  # Gray for NA/UNSAT values
        plt.rcParams['axes.prop_cycle'] = plt.cycler(color=self.colors)
        
        # General style improvements
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['legend.fontsize'] = 10
        plt.rcParams['figure.titlesize'] = 16
       
    def save_plot(self, filename: str):
        """Save plot to file with proper error handling"""
        try:
            plt.savefig(os.path.join(self.output_dir, filename), 
                        dpi=300, bbox_inches='tight')
        finally:
            plt.close('all')  # Close all figures

    def generate_all_plots(self, data: Dict[str, List]):
        """Generate all plots from metadata"""
        plot_functions = [
            (self.plot_solving_times, "solving_times.png"),
            (self.plot_problem_sizes, "problem_sizes.png"),
            (self.plot_problem_sizes_line, "problem_sizes_line.png"),
            (self.plot_constraint_distribution, "constraint_distribution.png"),
            (self.plot_constraint_activation, "constraint_activation.png"),
            (self.plot_constraint_complexity, "constraint_complexity.png"),
            (self.plot_solution_statistics, "solution_stats.png"),
            (self.plot_solution_statistics_bar, "solution_stats_bar.png"),
            (self.plot_correlation_matrix, "correlations.png"),
            (self.plot_efficiency_metrics, "efficiency.png"),
            (self.plot_instance_stats, "instance_stats.png"),
            (self.plot_step_authorizations, "step_authorizations.png"),
            (self.plot_user_authorizations, "user_authorizations.png"),
            (self.plot_authorization_density, "auth_density.png"),
            (self.plot_workload_distribution, "workload_distribution.png"),
            (self.plot_workload_distribution_line, "workload_distribution_line.png"),
            (self.plot_constraint_compliance, "constraint_compliance.png"),
        ]
        
        for plot_func, filename in plot_functions:
            try:
                plot_func(data)
            except Exception as e:
                print(f"Error generating {filename}: {str(e)}")
            finally:
                plt.close('all')

    def plot_solving_times(self, data: Dict[str, List], output_file: str = "solving_times.png"):
        plt.figure(figsize=(10, 6))
        
        instances = [Path(f).stem for f in data['filenames']]
        times = np.array(data['solving_times']) / 1000  # Convert to seconds
        
        bars = plt.bar(instances, times)
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Solving Time (seconds)')
        plt.title(f'WSP Instance Solving Times (Gray = UNSAT)\nFor Instances {instances[0]} - {instances[-1]}' if len(instances) > 1 else f'WSP Instance Solving Time: {instances[0]}')
        plt.ylim(0, max(times) * 1.2)  # Set y-limit to 120% of max time
        
        self.save_plot(output_file)
        
    def plot_step_authorizations(self, data: Dict[str, List], output_file: str = "step_authorizations.png"):
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        if 'authorization_analysis' in data and data['authorization_analysis']:
            auth_data = data['authorization_analysis']
            plt.figure(figsize=(12, 6))
            
            # Find max step number across all instances
            max_step = 0
            for instance_auth in auth_data:
                if 'per_step' in instance_auth:
                    steps = [int(s[1:]) for s in instance_auth['per_step'].keys()]
                    if steps:
                        max_step = max(max_step, max(steps))
            
            if max_step > 0:
                x = np.arange(1, max_step + 1)  # Step numbers
                width = 0.8 / len(instances)
                
                for i, (instance, auth) in enumerate(zip(instances, auth_data)):
                    values = []
                    for step in range(1, max_step + 1):
                        step_key = f's{step}'
                        if 'per_step' in auth and step_key in auth['per_step']:
                            values.append(len(auth['per_step'][step_key]))
                        else:
                            values.append(0)
                            
                    plt.bar(x + i*width - width*len(instances)/2, 
                        values, width, label=instance)
                
                plt.legend()
                plt.xlabel('Steps')
                plt.ylabel('Number of Authorized Users')
                plt.title(f'Step Authorization Distribution\nFor Instances {instances[0]} - {instances[-1]}')
                plt.xticks(x)
            else:
                plt.text(0.5, 0.5, 'No step authorization data found',
                        ha='center', va='center')
        else:
            plt.text(0.5, 0.5, 'No authorization analysis data available',
                    ha='center', va='center')
        
        plt.tight_layout()
        self.save_plot(output_file)
        
    def plot_user_authorizations(self, data: Dict[str, List], output_file: str = "user_authorizations.png"):
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        if 'authorization_analysis' in data and data['authorization_analysis']:
            auth_data = data['authorization_analysis']
            
            # Find max user number across all instances
            max_user = 0
            for instance_auth in auth_data:
                if 'per_user' in instance_auth:
                    users = [int(u[1:]) for u in instance_auth['per_user'].keys()]
                    if users:
                        max_user = max(max_user, max(users))
            
            if max_user > 0:
                x = np.arange(1, max_user + 1)  # User numbers
                width = 0.8 / len(instances)
                
                for i, (instance, auth) in enumerate(zip(instances, auth_data)):
                    values = []
                    for user in range(1, max_user + 1):
                        user_key = f'u{user}'
                        if 'per_user' in auth and user_key in auth['per_user']:
                            values.append(len(auth['per_user'][user_key]))
                        else:
                            values.append(0)
                            
                    plt.bar(x + i*width - width*len(instances)/2, 
                        values, width, label=instance)
                
                plt.legend()
                plt.xlabel('Users')
                plt.ylabel('Number of Authorized Steps')
                plt.title(f'User Authorization Distribution\nFor Instances {instances[0]} - {instances[-1]}')
                plt.xticks(x)
            else:
                plt.text(0.5, 0.5, 'No user authorization data found',
                        ha='center', va='center')
        else:
            plt.text(0.5, 0.5, 'No authorization analysis data available',
                    ha='center', va='center')
        
        plt.tight_layout()
        self.save_plot(output_file)
        
    def plot_problem_sizes(self, data: Dict[str, List],
                          output_file: str = "problem_sizes.png"):
        """Plot problem size metrics"""
        plt.figure(figsize=(12, 6))
        
        instances = [Path(f).stem for f in data['filenames']]
        x = np.arange(len(instances))
        width = 0.25
        
        plt.bar(x - width, data['num_steps'], width, label='Steps')
        plt.bar(x, data['num_users'], width, label='Users')
        plt.bar(x + width, data['num_constraints'], width, label='Constraints')
        
        plt.xticks(x, instances, rotation=45, ha='right')
        plt.ylabel('Count')
        plt.title('WSP Instance Size Comparison')
        plt.legend()
        
        self.save_plot(output_file)

    def plot_problem_sizes_line(self, data: Dict[str, List], output_file: str = "problem_sizes_line.png"):
        """Plot problem size metrics as line plot"""
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        x = np.arange(len(instances))
        
        plt.plot(x, data['num_steps'], 'o-', label='Steps', linewidth=2)
        plt.plot(x, data['num_users'], 's-', label='Users', linewidth=2)
        plt.plot(x, data['num_constraints'], '^-', label='Constraints', linewidth=2)
        
        plt.xticks(x, instances, rotation=45, ha='right')
        plt.ylabel('Count')
        plt.title(f'WSP Instance Size Comparison (Line)\nFor Instances {instances[0]} - {instances[-1]}')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        self.save_plot(output_file)
        
    def plot_workload_distribution(self, data: Dict[str, List], output_file: str = "workload_distribution.png"):
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        metrics = ['avg_steps_per_user', 'max_steps_per_user', 'utilization_percentage']
        if any(metric in data for metric in metrics):
            x = np.arange(len(instances))
            width = 0.3  # Increased for better visibility
            
            for i, metric in enumerate(metrics):
                if metric in data:
                    values = data[metric]
                    plt.bar(x + i*width - width, values, width,
                        label=metric.replace('_', ' ').title())
            
            plt.xlabel('Instances')
            plt.ylabel('Value')
            plt.title(f'Workload Distribution Metrics\nFor Instances {instances[0]} - {instances[-1]}')
            plt.legend()
            plt.xticks(x + width/2, instances, rotation=45, ha='right')
        else:
            plt.text(0.5, 0.5, 'No workload distribution data available',
                    ha='center', va='center')
        
        plt.tight_layout()
        self.save_plot(output_file)

    def plot_workload_distribution_line(self, data: Dict[str, List], output_file: str = "workload_distribution_line.png"):
        """Plot workload distribution metrics as line plot"""
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        x = np.arange(len(instances))
        
        metrics = ['avg_steps_per_user', 'max_steps_per_user', 'utilization_percentage']
        
        for metric in metrics:
            if metric in data:
                values = data[metric]
                plt.plot(x, values, 'o-', label=metric.replace('_', ' ').title(), linewidth=2)
        
        plt.xticks(x, instances, rotation=45, ha='right')
        plt.ylabel('Value')
        plt.title(f'Workload Distribution Metrics (Line)\nFor Instances {instances[0]} - {instances[-1]}')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        self.save_plot(output_file)

    def plot_constraint_compliance(self, data: Dict[str, List], output_file: str = "constraint_compliance.png"):
        """Plot constraint compliance with detailed violation breakdown"""
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        if 'solutions_found' in data and any(data['solutions_found']):
            sat_instances = [i for i, sat in enumerate(data['solutions_found']) if sat]
            
            if sat_instances:
                x = np.arange(len(instances))
                
                # Plot total violations
                plt.bar(x, data['violations'], label='Total Violations', alpha=0.3)
                
                # Annotate SAT/UNSAT status
                for i, is_sat in enumerate(data['solutions_found']):
                    color = '#2ecc71' if is_sat else '#e74c3c'
                    plt.text(i, data['violations'][i], 
                            'SAT' if is_sat else 'UNSAT',
                            ha='center', va='bottom', color=color)
                
                plt.xticks(x, instances, rotation=45, ha='right')
                plt.ylabel('Number of Violations')
                plt.title(f'Constraint Compliance\nFor Instances {instances[0]} - {instances[-1]}')
                plt.legend()
            else:
                plt.text(0.5, 0.5, 'No solutions found (all UNSAT)',
                        ha='center', va='center')
        else:
            plt.text(0.5, 0.5, 'No constraint compliance data available',
                    ha='center', va='center')
        
        plt.tight_layout()
        self.save_plot(output_file)

    def plot_constraint_distribution(self, data: Dict[str, List], output_file: str = "constraint_distribution.png"):
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        # Get all constraint types
        constraint_types = ['authorizations', 'separation_of_duty', 'binding_of_duty', 
                        'at_most_k', 'one_team', 'super_user_at_least', 
                        'wang_li', 'assignment_dependent']
        
        x = np.arange(len(instances))
        width = 0.8 / len(constraint_types)
        
        # Create legend handles and labels manually
        legend_handles = []
        legend_labels = []
        
        has_data = False
        for i, ctype in enumerate(constraint_types):
            key = f'constraint_{ctype}'
            label_added = False
            if key in data:
                for j, instance in enumerate(instances):
                    metadata = self.metadata_handler.load(f"{instance}_metadata.json")
                    if metadata and 'instance' in metadata:
                        has_constraint = metadata['instance']['details']['constraint_types'].get(ctype, 0) > 0
                        if has_constraint:
                            has_data = True
                            is_active = metadata['solver']['active_constraints'].get(ctype, False)
                            color = self.colors[i] if is_active else self.na_color
                            bar = plt.bar(x[j] + i*width - width*len(constraint_types)/2,
                                        1, width, color=color)
                            
                            # Add to legend only once per constraint type
                            if not label_added:
                                legend_handles.append(plt.Rectangle((0,0),1,1, facecolor=self.colors[i]))
                                legend_labels.append(ctype.replace('_', ' ').title())
                                label_added = True
        
        if not has_data:
            plt.text(0.5, 0.5, 'No constraint data available',
                    ha='center', va='center')
        else:
            plt.xlabel('Instances')
            plt.ylabel('Constraint Status')
            plt.title(f'Constraint Distribution\nFor Instances {instances[0]} - {instances[-1]}')
            plt.xticks(x, instances, rotation=45, ha='right')
            plt.legend(legend_handles, legend_labels, 
                    bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        self.save_plot(output_file)

    def plot_constraint_activation(self, data: Dict[str, List], output_file: str = "constraint_comparison.png"):
        """Plot activated and inactivated constraints across instances"""
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        # Track constraints across all instances
        type_stats = defaultdict(lambda: {'present': 0, 'active': 0})
        
        for instance in instances:
            metadata = self.metadata_handler.load(f"{instance}_metadata.json")
            if metadata and 'instance' in metadata:
                constraint_types = metadata['instance']['details'].get('constraint_types', {})
                active_constraints = metadata['solver']['active_constraints']
                
                for ctype, count in constraint_types.items():
                    if count > 0:
                        type_stats[ctype]['present'] += 1
                        if active_constraints.get(ctype, False):
                            type_stats[ctype]['active'] += 1
        
        if not type_stats:
            plt.text(0.5, 0.5, 'No constraint data available',
                    ha='center', va='center')
        else:
            constraint_types = sorted(type_stats.keys())
            y_pos = np.arange(len(constraint_types))
            
            inactive = [type_stats[ct]['present'] - type_stats[ct]['active'] for ct in constraint_types]
            active = [type_stats[ct]['active'] for ct in constraint_types]
            
            plt.barh(y_pos, inactive, color=self.na_color, label='Available but Inactive')
            plt.barh(y_pos, active, left=inactive, color=self.colors[0], label='Active')
            
            plt.yticks(y_pos, [ct.replace('_', ' ').title() for ct in constraint_types])
            plt.xlabel('Number of Instances')
            plt.title('Constraint Type Usage Across Instances')
            
            for i, (a, p) in enumerate(zip(active, inactive)):
                if a + p > 0:
                    plt.text(a + p + 0.1, i, f'{a}/{a+p} active', va='center')
                    
            plt.legend()
        
        plt.tight_layout()
        self.save_plot(output_file)

    def plot_solution_statistics(self, data: Dict[str, List], output_file: str = "solution_stats.png"):
        """Plot solution statistics using line graph"""
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        x = np.arange(len(instances))

        # Create figure with two y-axes
        fig, ax1 = plt.subplots(figsize=(12, 6))
        ax2 = ax1.twinx()
        
        # Plot solution status and uniqueness on primary y-axis
        l1 = ax1.plot(x, data['solutions_found'], 'o-', color='#2ecc71', 
                    label='SAT (1) / UNSAT (0)', linewidth=2)
        uniqueness_values = [float(u if u is not None else 0) for u in data['uniqueness']]
        l2 = ax1.plot(x, uniqueness_values, 's--', color='#3498db', 
                    label='Unique (1) / Multiple (0)', linewidth=2)
        
        # Plot solving time on secondary y-axis
        times = np.array(data['solving_times']) / 1000  # Convert to seconds
        l3 = ax2.plot(x, times, '^-.', color='#e74c3c', 
                    label='Solving Time (s)', linewidth=2)
        
        # Set labels and title
        ax1.set_xlabel('Instances')
        ax1.set_ylabel('Solution Status')
        ax2.set_ylabel('Solving Time (seconds)')
        plt.title(f'Solution Statistics\nFor Instances {instances[0]} - {instances[-1]}')
        
        # Set x-axis ticks
        ax1.set_xticks(x)
        ax1.set_xticklabels(instances, rotation=45, ha='right')
        
        # Add grid
        ax1.grid(True, alpha=0.3)
        
        # Add legend
        lns = l1 + l2 + l3
        labs = [l.get_label() for l in lns]
        ax1.legend(lns, labs, loc='center left', bbox_to_anchor=(1.15, 0.5))
        
        # Adjust layout to ensure everything is visible
        fig.tight_layout()
        plt.savefig(os.path.join(self.output_dir, output_file), 
                    dpi=300, bbox_inches='tight')
        plt.close()

    def plot_solution_statistics_bar(self, data: Dict[str, List], output_file: str = "solution_stats_bar.png"):
        """Plot solution statistics using bar chart"""
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        x = np.arange(len(instances))
        width = 0.25  # Width of bars
        
        # Plot bars for each metric
        plt.bar(x - width, data['solutions_found'], width,
                color='#2ecc71', label='SAT (1) / UNSAT (0)')
        
        uniqueness_values = [float(u if u is not None else 0) for u in data['uniqueness']]
        plt.bar(x, uniqueness_values, width,
                color='#3498db', label='Unique (1) / Multiple (0)')
        
        # Normalize solving times to [0,1] for comparison
        times = np.array(data['solving_times']) / 1000  # Convert to seconds
        if max(times) > 0:  # Avoid division by zero
            normalized_times = times / max(times)
        else:
            normalized_times = times
        plt.bar(x + width, normalized_times, width,
                color='#e74c3c', label='Normalized Solving Time')
        
        # Add solving time values as text above bars
        for i, time in enumerate(times):
            plt.text(x[i] + width, normalized_times[i], f'{time:.2f}s',
                    ha='center', va='bottom')
        
        plt.xlabel('Instances')
        plt.ylabel('Values')
        plt.title(f'Solution Statistics\nFor Instances {instances[0]} - {instances[-1]}')
        plt.xticks(x, instances, rotation=45, ha='right')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        self.save_plot(output_file)

    def plot_correlation_matrix(self, data: Dict[str, List], output_file: str = "correlations.png"):
        """Plot correlation matrix with robust error handling"""
        try:
            # Select numerical columns
            numerical_keys = ['solving_times', 'num_steps', 'num_users', 
                            'num_constraints', 'violations']
            numerical_data = {}
            
            # Clean and prepare data
            for k in numerical_keys:
                if k in data:
                    values = []
                    for v in data[k]:
                        if v is None or v == "N/A":
                            values.append(0)  # Use 0 for NA values
                        else:
                            values.append(float(v))
                    numerical_data[k] = values
            
            if not numerical_data:
                return
                
            # Calculate correlation matrix with error handling
            matrix = np.zeros((len(numerical_data), len(numerical_data)))
            labels = list(numerical_data.keys())
            
            for i, key1 in enumerate(labels):
                for j, key2 in enumerate(labels):
                    try:
                        if i == j:
                            matrix[i, j] = 1.0
                        else:
                            valid_indices = [idx for idx, (v1, v2) in 
                                           enumerate(zip(numerical_data[key1], numerical_data[key2]))
                                           if v1 != 0 and v2 != 0]  # Only use non-zero values
                            
                            if valid_indices:
                                x = [numerical_data[key1][i] for i in valid_indices]
                                y = [numerical_data[key2][i] for i in valid_indices]
                                matrix[i, j] = np.corrcoef(x, y)[0, 1]
                            else:
                                matrix[i, j] = np.nan
                    except:
                        matrix[i, j] = np.nan
            
            plt.figure(figsize=(10, 8))
            mask = np.isnan(matrix)  # Mask NaN values
            
            sns.heatmap(matrix, annot=True, cmap='coolwarm', center=0,
                       xticklabels=labels, yticklabels=labels,
                       mask=mask, cbar_kws={'label': 'Correlation'})
            
            plt.title('Correlation Matrix of WSP Metrics\n(Empty cells indicate insufficient data)')
            
        except Exception as e:
            print(f"Error generating correlation matrix: {str(e)}")
            # Create empty plot with message
            plt.figure(figsize=(10, 8))
            plt.text(0.5, 0.5, 'Correlation matrix unavailable\nInsufficient data',
                    ha='center', va='center')
            
        self.save_plot(output_file)
        
    def plot_efficiency_metrics(self, data: Dict[str, List],
                          output_file: str = "efficiency.png"):
        """Plot efficiency metrics"""
        plt.figure(figsize=(10, 6))
        
        instances = [Path(f).stem for f in data['filenames']]
        times = np.array(data['solving_times']) / 1000  # Convert to seconds
        
        # Add small epsilon to avoid division by zero
        times = np.where(times == 0, np.finfo(float).eps, times)
        
        # Calculate efficiency metrics
        steps_per_time = np.array(data['num_steps']) / times
        users_per_time = np.array(data['num_users']) / times
        constraints_per_time = np.array(data['num_constraints']) / times
        
        # Plot
        plt.plot(instances, steps_per_time, 'o-', label='Steps/second')
        plt.plot(instances, users_per_time, 's-', label='Users/second')
        plt.plot(instances, constraints_per_time, '^-', label='Constraints/second')
        
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Processing Rate')
        plt.title('Solver Efficiency Metrics')
        plt.legend()
        plt.yscale('log')  # Use log scale for better visualization
        
        self.save_plot(output_file)
           
    def plot_authorization_density(self, data: Dict[str, List], output_file: str = "auth_density.png"):
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        if 'num_steps' in data and 'num_users' in data and 'num_constraints' in data:
            x = np.arange(len(instances))
            # Calculate density as constraints/(steps*users)
            density = [c/(s*u)*100 for c, s, u in zip(
                data['num_constraints'],
                data['num_steps'],
                data['num_users']
            )]
            
            plt.plot(x, density, 'o-', linewidth=2, label='Density')
            mean_density = np.mean(density)
            plt.axhline(y=mean_density, color='r', linestyle='--', 
                    label=f'Mean: {mean_density:.2f}%')
            
            plt.xticks(x, instances, rotation=45, ha='right')
            plt.ylabel('Authorization Density (%)')
            plt.title(f'Authorization Density\nFor Instances {instances[0]} - {instances[-1]}')
            plt.grid(True, alpha=0.3)
            plt.legend()
        else:
            plt.text(0.5, 0.5, 'Insufficient data for authorization density',
                    ha='center', va='center')
        
        plt.tight_layout()
        self.save_plot(output_file)

    # Add method to show constraint complexity metrics
    def plot_constraint_complexity(self, data: Dict[str, List], output_file: str = "constraint_complexity.png"):
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        # Calculate complexity metrics
        if all(key in data for key in ['num_steps', 'num_users', 'num_constraints']):
            x = np.arange(len(instances))
            width = 0.3
            
            # Calculate metrics
            step_constraint_ratio = np.array(data['num_constraints']) / np.array(data['num_steps'])
            user_constraint_ratio = np.array(data['num_constraints']) / np.array(data['num_users'])
            density = np.array(data['num_constraints']) / (np.array(data['num_steps']) * np.array(data['num_users']))
            
            # Plot
            plt.bar(x - width, step_constraint_ratio, width, label='Constraints/Step')
            plt.bar(x, user_constraint_ratio, width, label='Constraints/User')
            plt.bar(x + width, density * 100, width, label='Constraint Density (%)')
            
            plt.xticks(x, instances, rotation=45, ha='right')
            plt.ylabel('Ratio/Percentage')
            plt.title(f'Constraint Complexity Metrics\nFor Instances {instances[0]} - {instances[-1]}')
            plt.legend()
        else:
            plt.text(0.5, 0.5, 'Insufficient data for complexity metrics',
                    ha='center', va='center')
        
        plt.tight_layout()
        self.save_plot(output_file)

    def plot_instance_stats(self, data: Dict[str, List], output_file: str = "instance_stats.png"):
        """Plot comprehensive instance statistics including UNSAT cases"""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            instances = [Path(f).stem for f in data['filenames']]
            x = np.arange(len(instances))
            
            # Plot 1: Solution Status
            status_colors = ['#2ecc71' if sat else '#e74c3c' 
                            for sat in data['solutions_found']]
            ax1.bar(x, [1] * len(instances), color=status_colors)
            ax1.set_title('Solution Status (Green=SAT, Red=UNSAT)')
            ax1.set_xticks(x)
            ax1.set_xticklabels(instances, rotation=45, ha='right')
            
            # Plot 2: Metrics
            metrics = ['num_steps', 'num_users', 'num_constraints']
            width = 0.25
            
            for i, metric in enumerate(metrics):
                values = []
                for val in data[metric]:
                    if val is None or val == "N/A":
                        values.append(0)
                    else:
                        values.append(float(val))
                ax2.bar(x + i*width, values, width, label=metric.replace('num_', ''))
            
            ax2.set_title('Instance Metrics')
            ax2.set_xticks(x + width)
            ax2.set_xticklabels(instances, rotation=45, ha='right')
            ax2.legend()
            
            plt.tight_layout()
            self.save_plot(output_file)
        except Exception as e:
            print(f"Error in instance_stats plot: {str(e)}")
        finally:
            plt.close('all')
