import json
import os
from datetime import datetime
from typing import Dict, List
import pandas as pd


class WSPMetadataHandler:
    def __init__(self, base_dir: str = "results"):
        self.base_dir = base_dir
        self.metadata_dir = os.path.join(base_dir, "metadata")
        self.visualizations_dir = os.path.join(base_dir, "visualizations")
        
        # Create necessary directories
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(self.visualizations_dir, exist_ok=True)

    def save_result_metadata(self, instance_details: Dict, solver_result: Dict, solver_type: str, active_constraints: Dict, filename: str) -> str:
        """Save metadata for a solver run"""
        # Calculate additional metrics if solution exists
        solution_metrics = {}
        if solver_result['sat'] == 'sat' and solver_result['sol']:
            user_distribution = self._calculate_user_distribution(solver_result['sol'])
            user_metrics = self._calculate_user_metrics(user_distribution)
            solution_metrics = {
                "users_distribution": user_distribution,
                "user_metrics": user_metrics
            }

        metadata = {
            "timestamp": datetime.now().isoformat(),
            "instance_file": filename,
            "solver_type": solver_type,
            "instance_details": instance_details,
            "solver_result": solver_result,
            "active_constraints": active_constraints,
            "solution_metrics": solution_metrics,
            "stats_summary": self._generate_stats_summary(
                instance_details, solver_result, active_constraints
            )
        }

        # Create unique filename for metadata
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metadata_filename = f"metadata_{timestamp}.json"
        
        filepath = os.path.join(self.metadata_dir, metadata_filename)
        with open(filepath, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        return filepath

    def _calculate_user_distribution(self, solution: List[Dict]) -> Dict:
        """Calculate distribution of assignments per user"""
        user_counts = {}
        for assignment in solution:
            user = f"user_{assignment['user']}"
            user_counts[user] = user_counts.get(user, 0) + 1
        return user_counts

    def _calculate_user_metrics(self, user_distribution: Dict) -> Dict:
        """Calculate user-related metrics"""
        assignments = list(user_distribution.values())
        if not assignments:
            return {
                "unique_users": 0,
                "max_assignments": 0,
                "min_assignments": 0,
                "avg_assignments": 0
            }
        return {
            "unique_users": len(user_distribution),
            "max_assignments": max(assignments),
            "min_assignments": min(assignments),
            "avg_assignments": sum(assignments) / len(assignments)
        }

    def _generate_stats_summary(self, instance_details: Dict, solver_result: Dict, active_constraints: Dict) -> Dict:
        """Generate statistical summary of results"""
        return {
            "performance_metrics": {
                "execution_time": {
                    "value": solver_result.get('result_exe_time', 0),
                    "unit": "ms"
                },
                "is_sat": solver_result.get('sat', 'unsat') == 'sat'
            },
            "instance_metrics": {
                "steps": instance_details.get('number_of_steps', 0),
                "users": instance_details.get('number_of_users', 0),
                "constraints": instance_details.get('number_of_constraints', 0),
                "densities": {
                    "auth": len(solver_result.get('sol', [])) / 
                           (instance_details.get('number_of_steps', 1) * 
                            instance_details.get('number_of_users', 1))
                    if solver_result.get('sat') == 'sat' else 0
                }
            },
            "constraint_metrics": {
                "distribution": {
                    "authorization": instance_details.get('authorization_constraints', 0),
                    "separation_of_duty": instance_details.get('separation_of_duty_constraints', 0),
                    "binding_of_duty": instance_details.get('binding_of_duty_constraints', 0),
                    "at_most_k": instance_details.get('at_most_k_constraints', 0),
                    "one_team": instance_details.get('one_team_constraints', 0)
                },
                "active": active_constraints
            }
        }

    def load_all_metadata(self) -> List[Dict]:
        """Load all metadata files and return as list of dictionaries"""
        all_metadata = []
        
        for filename in os.listdir(self.metadata_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.metadata_dir, filename)
                with open(filepath, 'r') as f:
                    metadata = json.load(f)
                    # Flatten the nested structure for easier analysis
                    flat_metadata = self._flatten_metadata(metadata)
                    all_metadata.append(flat_metadata)
                    
        return all_metadata

    def _flatten_metadata(self, metadata: Dict) -> Dict:
        """Flatten nested metadata structure"""
        flat = {}
        
        # Basic metadata
        flat['timestamp'] = metadata['timestamp']
        flat['instance_file'] = metadata['instance_file']
        flat['solver_type'] = metadata['solver_type']
        
        # Instance details
        for key, value in metadata['instance_details'].items():
            flat[key] = value
        
        # Solver results
        for key, value in metadata['solver_result'].items():
            flat[f'result_{key}'] = value

        # Active constraints
        for key, value in metadata['active_constraints'].items():
            flat[f'constraint_{key}'] = value

        # Solution metrics if available
        if metadata.get('solution_metrics', {}).get('user_metrics'):
            metrics = metadata['solution_metrics']['user_metrics']
            for key, value in metrics.items():
                flat[f'metric_{key}'] = value

        return flat

    def generate_visualizations(self):
        """Generate visualizations using saved metadata"""
        all_metadata = self.load_all_metadata()
        
        if not all_metadata:
            print("No metadata found to generate visualizations")
            return
            
        from stats import plot_all_metrics
        plot_all_metrics(all_metadata, self.visualizations_dir)

    def get_metadata_as_dataframe(self) -> pd.DataFrame:
        """Load all metadata and return as pandas DataFrame"""
        all_metadata = self.load_all_metadata()
        return pd.DataFrame(all_metadata)
