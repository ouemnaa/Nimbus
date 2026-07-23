from typing import List
from ..schemas.architecture import ArchitectureSpecification, ResourceScope

class MermaidRenderer:
    def render(self, architecture: ArchitectureSpecification) -> str:
        lines = ["flowchart TD"]
        
        # Define subgraphs for VPC/Subnets
        vpc_resources = [r for r in architecture.resources if r.scope == ResourceScope.VPC]
        public_subnets = [r for r in architecture.resources if r.scope == ResourceScope.PUBLIC_SUBNET]
        private_subnets = [r for r in architecture.resources if r.scope == ResourceScope.PRIVATE_SUBNET]
        
        # Simplistic subgraph nesting (can be improved)
        # For now, let's just group by scope
        
        # Helper to format node
        def format_node(res):
            node_id = res.id.replace("-", "_")
            label = f'"{res.name} ({res.provider_type})"'
            if res.category == "DATABASE":
                return f'    {node_id}[({label})]'
            return f'    {node_id}["{label}"]'

        # Add nodes
        for res in architecture.resources:
            lines.append(format_node(res))
            
        # Add relationships
        for rel in architecture.relationships:
            src = rel.source_id.replace("-", "_")
            dst = rel.target_id.replace("-", "_")
            lines.append(f'    {src} -->|"{rel.label}"| {dst}')
            
        return "\n".join(lines)
