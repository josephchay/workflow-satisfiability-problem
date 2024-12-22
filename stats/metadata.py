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

    def save_result_metadata(self, instance_details: Dict, solver_result: Dict, 
                           solver_type: str, active_constraints: Dict, filename: str) -> str:
        """Save enhanced metadata for a solver run"""
        # Calculate additional metrics
        solution_metrics = {}
        if solver_result['sat'] == 'sat' and solver_result['sol']:
            user_metrics = self._calculate_user_metrics(solver_result['sol'])
            density_metrics = self._calculate_density_metrics(instance_details)
            
            solution_metrics = {
                "user_metrics": user_metrics,
                "density_metrics": density_metrics,
                "constraint_violations": solver_result.get('violations', {})
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

        # Save metadata
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metadata_filename = f"metadata_{timestamp}.json"
        filepath = os.path.join(self.metadata_dir, metadata_filename)
        
        with open(filepath, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        return filepath
    
    def _analyze_user_metrics(self, solution: List[Dict]) -> Dict:
        """Calculate user-related metrics from solution"""
        user_counts = {}
        for assignment in solution:
            user = assignment['user']
            user_counts[user] = user_counts.get(user, 0) + 1
            
        return {
            "unique_users": len(user_counts),
            "max_steps_per_user": max(user_counts.values()) if user_counts else 0,
            "min_steps_per_user": min(user_counts.values()) if user_counts else 0,
            "avg_steps_per_user": sum(user_counts.values()) / len(user_counts) if user_counts else 0
        }

    def _calculate_user_distribution(self, solution: List[Dict]) -> Dict:
        """Calculate distribution of assignments per user"""
        user_counts = {}
        for assignment in solution:
            user = f"user_{assignment['user']}"
            user_counts[user] = user_counts.get(user, 0) + 1
        return user_counts

    def _calculate_user_metrics(self, solution: List[Dict]) -> Dict:
        """Calculate user assignment metrics"""
        user_counts = {}
        for assignment in solution:
            user = assignment['user']
            user_counts[user] = user_counts.get(user, 0) + 1
            
        if not user_counts:
            return {
                "unique_users": 0,
                "max_steps_per_user": 0,
                "min_steps_per_user": 0,
                "avg_steps_per_user": 0
            }
            
        return {
            "unique_users": len(user_counts),
            "max_steps_per_user": max(user_counts.values()),
            "min_steps_per_user": min(user_counts.values()),
            "avg_steps_per_user": sum(user_counts.values()) / len(user_counts)
        }

    def _calculate_density_metrics(self, instance_details: Dict) -> Dict:
        """Calculate density-related metrics from instance details"""
        basic_metrics = instance_details.get('Basic Metrics', {})
        steps = basic_metrics.get('Total Steps', 0)
        users = basic_metrics.get('Total Users', 0)
        constraints = basic_metrics.get('Total Constraints', 0)
        
        # Avoid division by zero
        if steps * users == 0:
            return {
                "Auth Density": 0,
                "Constraint Density": 0,
                "Step-User Ratio": 0 if users == 0 else steps / users
            }
            
        # Get authorization count from constraint distribution
        auth_count = instance_details.get('Constraint Distribution', {}).get('Authorization', 0)
        
        return {
            "Auth Density": auth_count / (steps * users),
            "Constraint Density": constraints / (steps * users),
            "Step-User Ratio": steps / users
        }

    def _generate_stats_summary(self, instance_details: Dict, 
                              solver_result: Dict, 
                              active_constraints: Dict) -> Dict:
        """Generate comprehensive statistical summary"""
        return {
            "performance_metrics": {
                "execution_time": {
                    "value": solver_result.get('result_exe_time', 0),
                    "unit": "ms"
                },
                "is_sat": solver_result.get('sat', 'unsat') == 'sat',
                "solution_found": solver_result.get('sol', []) != []
            },
            "instance_metrics": {
                "steps": instance_details.get('Basic Metrics', {}).get('Total Steps', 0),
                "users": instance_details.get('Basic Metrics', {}).get('Total Users', 0),
                "constraints": instance_details.get('Basic Metrics', {}).get('Total Constraints', 0),
                "densities": instance_details.get('Density Metrics', {}),
                "constraint_distribution": instance_details.get('Constraint Distribution', {})
            },
            "constraint_metrics": {
                "active": active_constraints,
                "violations": solver_result.get('violations', {}),
                "distribution": instance_details.get('Constraint Distribution', {})
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
        """Flatten nested metadata structure for analysis"""
        flat = {}
        
        # Basic metadata
        flat['timestamp'] = metadata['timestamp']
        flat['instance_file'] = metadata['instance_file']
        flat['solver_type'] = metadata['solver_type']
        
        # Instance details
        if 'instance_details' in metadata:
            for section, metrics in metadata['instance_details'].items():
                if isinstance(metrics, dict):
                    for key, value in metrics.items():
                        flat[f'{section}_{key}'] = value
        
        # Solver results
        if 'solver_result' in metadata:
            for key, value in metadata['solver_result'].items():
                if key != 'sol':  # Skip the solution array
                    flat[f'result_{key}'] = value

        # Solution metrics
        if 'solution_metrics' in metadata:
            for category, metrics in metadata['solution_metrics'].items():
                if isinstance(metrics, dict):
                    for key, value in metrics.items():
                        flat[f'metric_{category}_{key}'] = value

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
