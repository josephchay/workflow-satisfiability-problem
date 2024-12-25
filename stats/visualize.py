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
        
    def plot_solving_times(self, data: Dict[str, List], output_file: str = "solving_times.png"):
        """Plot solving times comparison with UNSAT handling"""
        plt.figure(figsize=(10, 6))
        
        instances = [Path(f).stem for f in data['filenames']]
        times = []
        colors = []
        
        for i, time in enumerate(data['solving_times']):
            if time is None or time == 0:
                times.append(0)  # Use 0 for visualization
                colors.append(self.na_color)
            else:
                times.append(time / 1000)  # Convert to seconds
                colors.append(self.colors[0])
        
        bars = plt.bar(instances, times)
        for bar, color in zip(bars, colors):
            bar.set_color(color)
            if color == self.na_color:
                # Add "UNSAT" text above bar
                plt.text(bar.get_x() + bar.get_width()/2, 0.1,
                        'UNSAT', ha='center', rotation=90,
                        color='white')
        
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Solving Time (seconds)')
        plt.title('WSP Instance Solving Times (Gray = UNSAT)')
        
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

    def generate_all_plots(self, data: Dict[str, List]):
        """Generate all plots from metadata"""
        plot_functions = [
            (self.plot_solving_times, "solving_times.png"),
            (self.plot_problem_sizes, "problem_sizes.png"),
            (self.plot_constraint_distribution, "constraint_distribution.png"),
            (self.plot_solution_statistics, "solution_stats.png"),
            (self.plot_correlation_matrix, "correlations.png"),
            (self.plot_efficiency_metrics, "efficiency.png"),
            (self.plot_instance_stats, "instance_stats.png")
        ]
        
        for plot_func, filename in plot_functions:
            try:
                plot_func(data)
            except Exception as e:
                print(f"Error generating {filename}: {str(e)}")
            finally:
                plt.close('all')
