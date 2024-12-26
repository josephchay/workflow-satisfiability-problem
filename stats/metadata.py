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
        
    def save(self, instance_details: Dict[str, Any],
                    solver_result: Dict[str, Any],
                    solver_type: str,
                    active_constraints: Dict[str, bool],
                    filename: str) -> str:
        """Save complete metadata for a WSP instance solution."""
        # Extract authorization from solution if available
        authorization_analysis = {}
        if solver_result.get('sat') == 'sat' and solver_result.get('sol'):
            per_step = defaultdict(list)
            per_user = defaultdict(list)
            for assign in solver_result['sol']:
                step = assign['step']
                user = assign['user']
                per_step[f's{step}'].append(f'u{user}')
                per_user[f'u{user}'].append(f's{step}')
            authorization_analysis = {
                'per_step': dict(per_step),
                'per_user': dict(per_user)
            }

        constraint_distribution = instance_details.get('constraint_distribution', {})        

        # Get constraint counts directly
        constraint_types = {
            'authorizations': instance_details.get('Authorization', 0), 
            'separation_of_duty': instance_details.get('Separation Of Duty', 0),
            'binding_of_duty': instance_details.get('Binding Of Duty', 0),
            'at_most_k': instance_details.get('At Most K', 0),
            'one_team': instance_details.get('One Team', 0),
            'super_user_at_least': instance_details.get('Super User At Least', 0),
            'wang_li': instance_details.get('Wang Li', 0),
            'assignment_dependent': instance_details.get('Assignment Dependent', 0)
        }
        
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "instance": {
                "filename": filename,
                "details": {
                    **instance_details,
                    "authorization_analysis": authorization_analysis,
                    "workload_distribution": {
                        "avg_steps_per_user": float(instance_details.get("Step-User Ratio", 0)),
                        "max_steps_per_user": float(instance_details.get("Max Steps Per User", 0)),
                        "utilization_percentage": float(instance_details.get("Authorization Density", "0").rstrip('%'))
                    },
                    "constraint_distribution": constraint_distribution,
                    "constraint_types": constraint_types,
                }
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
    
    def load(self, filename: str) -> Optional[Dict]:
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
                metadata = self.load(filename)
                if metadata:
                    results.append(metadata)
        return results
        
    def get_comparison_data(self, filenames: List[str]) -> Dict[str, List]:
        """Load metadata for instances, handling UNSAT cases"""
        comparison_data = defaultdict(list)
        
        for filename in filenames:
            metadata = self.load(
                f"{os.path.splitext(filename)[0]}_metadata.json"
            )
            if metadata:
                # Basic instance info
                comparison_data['filenames'].append(metadata['instance']['filename'])
                comparison_data['num_steps'].append(metadata['instance']['details']['Total Steps'])
                comparison_data['num_users'].append(metadata['instance']['details']['Total Users'])
                comparison_data['num_constraints'].append(metadata['instance']['details']['Total Constraints'])
                
                # Constraint types
                constraint_types = metadata['instance']['details'].get('constraint_types', {})
                for ctype, count in constraint_types.items():
                    comparison_data[f'constraint_{ctype}'].append(count)

                # Get active constraints
                active = metadata['solver']['active_constraints']
                for ctype, is_active in active.items():
                    comparison_data[f'constraint_{ctype}_active'].append(1 if is_active else 0)

                # Solution status and metrics
                comparison_data['solving_times'].append(metadata['metrics']['solving_time_ms'])
                comparison_data['solutions_found'].append(metadata['metrics']['solution_found'])
                comparison_data['uniqueness'].append(metadata['metrics']['solution_unique'])
                comparison_data['violations'].append(metadata['metrics'].get('constraint_violations', 0))
                
                # Authorization details
                auth_analysis = metadata['instance']['details'].get('authorization_analysis', {})
                comparison_data['authorization_analysis'].append(auth_analysis)
                
                # Workload distribution
                workload = metadata['instance']['details'].get('workload_distribution', {})
                for metric in ['avg_steps_per_user', 'max_steps_per_user', 'utilization_percentage']:
                    comparison_data[metric].append(workload.get(metric, 0))
                
                # Constraint details - now using active constraints
                constraints = metadata['solver']['active_constraints']
                for constraint_type, is_active in constraints.items():
                    comparison_data[f'constraint_{constraint_type}'].append(1 if is_active else 0)
                
                # Violations if solution exists
                if metadata['metrics']['solution_found']:
                    comparison_data['constraint_violations'].append(
                        len(metadata['solver']['results'].get('violations', []))
                    )
        
        return dict(comparison_data)
