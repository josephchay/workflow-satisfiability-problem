import json
import os
import os.path
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Optional


class MetadataHandler:
    """Handles saving and loading of WSP solution metadata"""
    
    def __init__(self, output_dir: str = "results/metadata"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def save_result_metadata(self, 
                       instance_details: Dict[str, Any],
                       solver_result: Dict[str, Any],
                       solver_type: str,
                       active_constraints: Dict[str, bool],
                       filename: str) -> str:
        """Save complete metadata for a WSP instance solution."""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "instance": {
                "filename": filename,
                "details": instance_details
            },
            "solver": {
                "type": solver_type,
                "active_constraints": active_constraints,
                "results": solver_result
            },
            "metrics": {
                "solving_time_ms": solver_result.get('exe_time', 0),
                "solution_found": solver_result.get('sat') == 'sat',
                "solution_unique": solver_result.get('is_unique', None),
                "constraint_violations": len(solver_result.get('violations', [])) if solver_result.get('sat') == 'sat' else 0,
            }
        }
        
        output_file = os.path.join(
            self.output_dir,
            f"{os.path.splitext(filename)[0]}_metadata.json"
        )
        
        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        return output_file
        
    def load_result_metadata(self, filename: str) -> Optional[Dict]:
        """Load metadata from file"""
        filepath = os.path.join(self.output_dir, filename)
        if not os.path.exists(filepath):
            return None
            
        with open(filepath) as f:
            return json.load(f)
            
    def load_all_results(self) -> List[Dict]:
        """Load all metadata files in output directory"""
        results = []
        for filename in os.listdir(self.output_dir):
            if filename.endswith('_metadata.json'):
                metadata = self.load_result_metadata(filename)
                if metadata:
                    results.append(metadata)
        return results
        
    def get_comparison_data(self, filenames: List[str]) -> Dict[str, List]:
        """Load metadata for instances, handling UNSAT cases"""
        comparison_data = defaultdict(list)
        
        for filename in filenames:
            metadata = self.load_result_metadata(
                f"{os.path.splitext(filename)[0]}_metadata.json"
            )
            if metadata:
                # Basic instance info - always available
                comparison_data['filenames'].append(metadata['instance']['filename'])
                comparison_data['num_steps'].append(metadata['instance']['details']['Total Steps'])
                comparison_data['num_users'].append(metadata['instance']['details']['Total Users'])
                comparison_data['num_constraints'].append(metadata['instance']['details']['Total Constraints'])
                
                # Solution status and metrics
                comparison_data['solving_times'].append(metadata['metrics']['solving_time_ms'])
                comparison_data['solutions_found'].append(metadata['metrics']['solution_found'])
                comparison_data['uniqueness'].append(metadata['metrics']['solution_unique'])
                comparison_data['violations'].append(metadata['metrics'].get('constraint_violations', 0))
                
                # Get constraint distribution
                constraints = metadata['instance']['details'].get('Constraint Distribution', {})
                for constraint_type, count in constraints.items():
                    key = f'constraint_{constraint_type.lower().replace(" ", "_")}'
                    comparison_data[key].append(count)
                    
        return dict(comparison_data)
