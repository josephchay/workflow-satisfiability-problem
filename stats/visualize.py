import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict
import os
import seaborn as sns
from pathlib import Path


class Visualizer:
    """Generates visualizations for WSP metadata"""
    
    def __init__(self, output_dir: str = "results/plots"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set modern style
        try:
            # Try new-style seaborn first
            plt.style.use('seaborn-v0_8-whitegrid')
        except:
            try:
                # Fallback to basic seaborn
                plt.style.use('seaborn')
            except:
                # Fallback to default style with grid
                plt.rcParams['axes.grid'] = True
                plt.rcParams['grid.alpha'] = 0.3
                
        # Set color palette
        colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c', '#34495e', '#f1c40f']
        plt.rcParams['axes.prop_cycle'] = plt.cycler(color=colors)
        
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
        """Save plot with standard formatting"""
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), 
                   dpi=300, bbox_inches='tight')
        plt.close()
        
    def plot_solving_times(self, data: Dict[str, List], 
                          output_file: str = "solving_times.png"):
        """Plot solving times comparison"""
        plt.figure(figsize=(10, 6))
        
        times = np.array(data['solving_times']) / 1000  # Convert to seconds
        instances = [Path(f).stem for f in data['filenames']]
        
        plt.bar(instances, times)
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Solving Time (seconds)')
        plt.title('WSP Instance Solving Times Comparison')
        
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
        
    def plot_constraint_distribution(self, data: Dict[str, List],
                                   output_file: str = "constraint_distribution.png"):
        """Plot constraint type distribution"""
        constraint_keys = [k for k in data.keys() if k.startswith('constraint_')]
        if not constraint_keys:
            return
            
        plt.figure(figsize=(12, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        # Create stacked bar chart
        bottom = np.zeros(len(instances))
        for key in constraint_keys:
            plt.bar(instances, data[key], bottom=bottom, 
                   label=key.replace('constraint_', ''))
            bottom += np.array(data[key])
            
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Number of Constraints')
        plt.title('Constraint Distribution Across Instances')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        self.save_plot(output_file)
        
    def plot_solution_statistics(self, data: Dict[str, List],
                               output_file: str = "solution_stats.png"):
        """Plot solution statistics"""
        plt.figure(figsize=(10, 6))
        instances = [Path(f).stem for f in data['filenames']]
        
        # Create grouped bar chart
        x = np.arange(len(instances))
        width = 0.35
        
        plt.bar(x - width/2, [int(s) for s in data['solutions_found']], 
               width, label='Solution Found')
        plt.bar(x + width/2, [int(s) if s is not None else 0 for s in data['uniqueness']], 
               width, label='Unique Solution')
        
        plt.xticks(x, instances, rotation=45, ha='right')
        plt.ylabel('Status (0/1)')
        plt.title('Solution Statistics Across Instances')
        plt.legend()
        
        self.save_plot(output_file)
        
    def plot_correlation_matrix(self, data: Dict[str, List],
                              output_file: str = "correlations.png"):
        """Plot correlation matrix between numerical metrics"""
        # Select numerical columns
        numerical_keys = ['solving_times', 'num_steps', 'num_users', 
                         'num_constraints', 'violations']
        numerical_data = {k: data[k] for k in numerical_keys if k in data}
        
        if not numerical_data:
            return
            
        # Create correlation matrix
        matrix = np.corrcoef([numerical_data[k] for k in numerical_data.keys()])
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(matrix, annot=True, cmap='coolwarm', center=0,
                   xticklabels=list(numerical_data.keys()),
                   yticklabels=list(numerical_data.keys()))
        plt.title('Correlation Matrix of WSP Metrics')
        
        self.save_plot(output_file)
        
    def plot_efficiency_metrics(self, data: Dict[str, List],
                              output_file: str = "efficiency.png"):
        """Plot efficiency metrics"""
        plt.figure(figsize=(10, 6))
        
        instances = [Path(f).stem for f in data['filenames']]
        times = np.array(data['solving_times']) / 1000
        
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
        
    def generate_all_plots(self, data: Dict[str, List]):
        """Generate all available plots"""
        self.plot_solving_times(data)
        self.plot_problem_sizes(data)
        self.plot_constraint_distribution(data)
        self.plot_solution_statistics(data)
        self.plot_correlation_matrix(data)
        self.plot_efficiency_metrics(data)
