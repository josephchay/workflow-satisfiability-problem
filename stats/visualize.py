import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional
import os
from datetime import datetime


class WSPVisualizer:
    def __init__(self, results_dir: str):
        self.results_dir = results_dir
        # Create results directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)
        
    def plot_scaling_analysis(self, data: List[Dict], metric: str = 'result_exe_time'):
        df = pd.DataFrame(data)
        
        plt.figure(figsize=(12, 6))
        for solver in df['solver_type'].unique():
            solver_data = df[df['solver_type'] == solver]
            plt.plot(solver_data['k'], solver_data[metric], 
                    marker='o', label=solver, markersize=8)  # Added markersize
        
        plt.yscale('log')
        # Add padding to axes limits for better visibility
        plt.margins(x=0.2, y=0.2)
        plt.xlabel('Number of steps (k)')
        plt.ylabel('Execution time (ms)' if metric == 'result_exe_time' else metric)
        plt.title(f'Scaling Analysis (n = 10k)')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(self.results_dir, f'scaling_k_{metric}.png'))
        plt.close()

    def plot_constraint_impact(self, data: List[Dict]):
        df = pd.DataFrame(data)
        constraints = ['constraint_authorizations', 'constraint_separation_of_duty', 
                    'constraint_binding_of_duty', 'constraint_at_most_k', 
                    'constraint_one_team']  # Updated constraint field names
        
        plt.figure(figsize=(12, 6))
        for constraint in constraints:
            constraint_data = df[df[constraint] == True]
            if not constraint_data.empty:  # Only plot if we have data
                sns.boxplot(data=constraint_data, x='solver_type', 
                        y='result_exe_time', label=constraint.replace('constraint_', ''))
        
        plt.yscale('log')
        plt.xlabel('Solver Type')
        plt.ylabel('Execution Time (ms)')
        plt.title('Impact of Constraints on Performance')
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(self.results_dir, 'constraint_impact.png'))
        plt.close()

    def plot_solution_characteristics(self, data: List[Dict]):
        """Plot various solution characteristics"""
        df = pd.DataFrame(data)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 15))
        
        # Performance by solver
        sns.boxplot(data=df, x='solver_type', y='result_exe_time', ax=axes[0,0])
        axes[0,0].set_title('Performance by Solver')
        axes[0,0].set_xticks(range(len(df['solver_type'].unique())))
        axes[0,0].set_xticklabels(df['solver_type'].unique(), rotation=45)
        axes[0,0].set_yscale('log')
        
        # Step-User Ratio
        sns.boxplot(data=df, x='solver_type', y='step_user_ratio', ax=axes[0,1])
        axes[0,1].set_title('Step-User Ratio')
        axes[0,1].set_xticks(range(len(df['solver_type'].unique())))
        axes[0,1].set_xticklabels(df['solver_type'].unique(), rotation=45)
        
        # Solution uniqueness
        unique_solutions = df.groupby('solver_type')['result_is_unique'].mean()
        unique_solutions.plot(kind='bar', ax=axes[1,0])
        axes[1,0].set_title('Proportion of Unique Solutions')
        axes[1,0].set_xticklabels(axes[1,0].get_xticklabels(), rotation=45)
        
        # Satisfiability
        sat_proportion = df.groupby('solver_type')['result_sat'].apply(
            lambda x: (x == 'sat').mean())
        sat_proportion.plot(kind='bar', ax=axes[1,1])
        axes[1,1].set_title('Proportion of Satisfiable Instances')
        axes[1,1].set_xticklabels(axes[1,1].get_xticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.results_dir, 'solution_characteristics.png'))
        plt.close()

    def plot_max_k_analysis(self, data: List[Dict], time_limit: float = 60000):
        """Plot maximum k that can be solved within time limit"""
        df = pd.DataFrame(data)
        df['within_limit'] = df['result_exe_time'] <= time_limit
        
        max_k = df[df['within_limit']].groupby('solver_type')['k'].max()
        
        plt.figure(figsize=(10, 6))
        max_k.plot(kind='bar')
        plt.title(f'Maximum k Solved Within {time_limit/1000}s')
        plt.xlabel('Solver Type')
        plt.ylabel('Maximum k')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.results_dir, 'max_k_analysis.png'))
        plt.close()

    def plot_instance_complexity(self, data: List[Dict]):
        """Plot relationship between instance characteristics and performance"""
        df = pd.DataFrame(data)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 15))
        
        # Number of steps vs time
        for solver in df['solver_type'].unique():
            solver_data = df[df['solver_type'] == solver]
            axes[0,0].scatter(solver_data['number_of_steps'], 
                            solver_data['result_exe_time'], 
                            label=solver, alpha=0.6)
        axes[0,0].set_yscale('log')
        axes[0,0].set_title('Steps vs Execution Time')
        axes[0,0].set_xlabel('Number of Steps')
        axes[0,0].set_ylabel('Execution Time (ms)')
        axes[0,0].legend()
        
        # Number of users vs time
        for solver in df['solver_type'].unique():
            solver_data = df[df['solver_type'] == solver]
            axes[0,1].scatter(solver_data['number_of_users'], 
                            solver_data['result_exe_time'], 
                            label=solver, alpha=0.6)
        axes[0,1].set_yscale('log')
        axes[0,1].set_title('Users vs Execution Time')
        axes[0,1].set_xlabel('Number of Users')
        axes[0,1].set_ylabel('Execution Time (ms)')
        axes[0,1].legend()
        
        # Total constraints vs time
        for solver in df['solver_type'].unique():
            solver_data = df[df['solver_type'] == solver]
            axes[1,0].scatter(solver_data['number_of_constraints'], 
                            solver_data['result_exe_time'], 
                            label=solver, alpha=0.6)
        axes[1,0].set_yscale('log')
        axes[1,0].set_title('Constraints vs Execution Time')
        axes[1,0].set_xlabel('Number of Constraints')
        axes[1,0].set_ylabel('Execution Time (ms)')
        axes[1,0].legend()
        
        # Authorization density vs time
        df['auth_density'] = df['authorization_constraints'] / (df['number_of_steps'] * df['number_of_users'])
        for solver in df['solver_type'].unique():
            solver_data = df[df['solver_type'] == solver]
            axes[1,1].scatter(solver_data['auth_density'], 
                            solver_data['result_exe_time'], 
                            label=solver, alpha=0.6)
        axes[1,1].set_yscale('log')
        axes[1,1].set_title('Authorization Density vs Execution Time')
        axes[1,1].set_xlabel('Authorization Density')
        axes[1,1].set_ylabel('Execution Time (ms)')
        axes[1,1].legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.results_dir, 'instance_complexity.png'))
        plt.close()

    def generate_report(self, data: List[Dict], output_file: Optional[str] = None):
        """Generate a comprehensive analysis report"""
        df = pd.DataFrame(data)
        
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.results_dir, f'analysis_report_{timestamp}.md')
        
        with open(output_file, 'w') as f:
            f.write('# WSP Solver Analysis Report\n\n')
            
            f.write('## Performance Summary\n\n')
            perf_summary = df.groupby('solver_type').agg({
                'result_exe_time': ['mean', 'std', 'min', 'max'],
                'result_sat': lambda x: (x == 'sat').mean(),
                'result_is_unique': 'mean'
            }).round(2)
            f.write(f'```\n{perf_summary}\n```\n\n')
            
            f.write('## Instance Characteristics\n\n')
            instance_summary = df.agg({
                'number_of_steps': ['mean', 'std', 'min', 'max'],
                'number_of_users': ['mean', 'std', 'min', 'max'],
                'number_of_constraints': ['mean', 'std', 'min', 'max']
            }).round(2)
            f.write(f'```\n{instance_summary}\n```\n\n')
            
            f.write('## Constraint Analysis\n\n')
            constraints = ['constraint_authorizations', 'constraint_separation_of_duty', 
                        'constraint_binding_of_duty', 'constraint_at_most_k', 
                        'constraint_one_team']
            for c in constraints:
                desc = c.replace('constraint_', '').replace('_', ' ').title()
                constraint_impact = df[df[c]]['result_exe_time'].describe().round(2)
                f.write(f'### {desc}\n')
                f.write(f'```\n{constraint_impact}\n```\n\n')


def plot_all_metrics(data: List[Dict], output_dir: str):
    """Helper function to generate all visualizations"""
    visualizer = WSPVisualizer(output_dir)
    
    try:
        print("Generating scaling analysis...")
        visualizer.plot_scaling_analysis(data)
        
        print("Generating constraint impact...")
        visualizer.plot_constraint_impact(data)
        
        print("Generating solution characteristics...")
        visualizer.plot_solution_characteristics(data)
        
        print("Generating max k analysis...")
        visualizer.plot_max_k_analysis(data)
        
        print("Generating instance complexity...")
        visualizer.plot_instance_complexity(data)
        
        print("Generating report...")
        visualizer.generate_report(data)
        
        print("All visualizations completed!")
    except Exception as e:
        print(f"Error generating visualizations: {str(e)}")
        import traceback
        traceback.print_exc()
