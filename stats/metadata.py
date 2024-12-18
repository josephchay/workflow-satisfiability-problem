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
        """Update this method to include more comprehensive data"""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "instance_file": filename,
            "solver_type": solver_type,
            "instance_details": instance_details,
            "solver_result": solver_result,
            "active_constraints": active_constraints,
            "stats_summary": self._generate_stats_summary([instance_details, solver_result, active_constraints])
        }

        # Create unique filename for metadata
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metadata_filename = f"metadata_{timestamp}.json"
        
        filepath = os.path.join(self.metadata_dir, metadata_filename)
        with open(filepath, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        return filepath

    def _generate_stats_summary(self, data: List[Dict]) -> Dict:
        """Helper method to generate stats summary - replaces generate_stats_summary in visualize.py"""
        df = pd.DataFrame(data)
        
        def safe_stats(series):
            stats = series.agg(['mean', 'std', 'min', 'max']).to_dict()
            return {k: 0 if pd.isna(v) else v for k, v in stats.items()}
        
        return {
            "performance_metrics": {
                "execution_time": safe_stats(df['result_exe_time']),
                "solution_count": safe_stats(df['solution_count']),
                "unique_solutions": df['is_unique'].mean()
            },
            "instance_metrics": {
                "steps": safe_stats(df['number_of_steps']),
                "users": safe_stats(df['number_of_users']),
                "constraints": safe_stats(df['number_of_constraints']),
                "densities": {
                    "auth": safe_stats(df['auth_density']),
                    "constraint": safe_stats(df['constraint_density'])
                }
            },
            "constraint_metrics": {
                "distribution": {
                    c: safe_stats(df[f'{c}_constraints']) 
                    for c in ['authorization', 'separation_of_duty', 'binding_of_duty', 'at_most_k', 'one_team']
                }
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
            # No need to modify exe_time since it's already a float
            flat[f'result_{key}'] = value
                
        # Active constraints
        for key, value in metadata['active_constraints'].items():
            flat[f'constraint_{key}'] = value
        
        return flat

    def generate_visualizations(self):
        """Generate visualizations using saved metadata"""
        # Load all metadata
        all_metadata = self.load_all_metadata()
        
        if not all_metadata:
            print("No metadata found to generate visualizations")
            return
            
        # Import visualization code
        from stats import plot_all_metrics
        
        # Generate visualizations
        plot_all_metrics(all_metadata, self.visualizations_dir)

    def get_metadata_as_dataframe(self) -> pd.DataFrame:
        """Load all metadata and return as pandas DataFrame"""
        all_metadata = self.load_all_metadata()
        return pd.DataFrame(all_metadata)
