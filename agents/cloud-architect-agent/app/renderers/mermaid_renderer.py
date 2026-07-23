import re
from typing import Dict, List
from ..schemas.architecture import (
    ArchitectureSpecification,
    DiagramVisibility,
    Resource,
    ResourceCategory,
    ResourceScope,
)


class MermaidRenderer:
    def render(self, architecture: ArchitectureSpecification) -> Dict[str, str]:
        return {
            "simple": self.render_simple(architecture),
            "advanced": self.render_advanced(architecture),
        }

    def render_simple(self, architecture: ArchitectureSpecification) -> str:
        resources = [res for res in architecture.resources if res.diagram_visibility == DiagramVisibility.HIGH_LEVEL]
        visible_ids = {res.id for res in resources}

        lines = ["flowchart LR", '    user["User / Client"]']
        for resource in resources:
            lines.append(self._format_node(resource, technical=False))

        entrypoint = next((res for res in resources if res.category == ResourceCategory.LOAD_BALANCING), None)
        if entrypoint:
            lines.append(f"    user --> {self._node_id(entrypoint.id)}")

        for relationship in architecture.relationships:
            if relationship.source_id in visible_ids and relationship.target_id in visible_ids:
                lines.append(self._format_edge(relationship.source_id, relationship.target_id, relationship.label))

        return "\n".join(lines)

    def render_advanced(self, architecture: ArchitectureSpecification) -> str:
        resources = [res for res in architecture.resources if res.diagram_visibility != DiagramVisibility.HIDDEN]
        public_resources = self._resources_for_public_zone(resources)
        private_app_resources = self._resources_for_private_app_zone(resources)
        private_data_resources = self._resources_for_private_data_zone(resources)
        root_resources = [
            res for res in resources
            if res not in public_resources
            and res not in private_app_resources
            and res not in private_data_resources
            and res.scope not in {ResourceScope.VPC}
        ]
        vpc_resource = next((res for res in resources if res.scope == ResourceScope.VPC), None)

        lines = ["flowchart TB", '    internet["Internet"]', '    subgraph aws["AWS Region"]']
        vpc_label = self._escape_label(vpc_resource.name) if vpc_resource else "Application VPC"
        lines.append(f'        subgraph vpc["{vpc_label}"]')

        if public_resources:
            lines.extend(self._format_subgraph("public", "Public Subnets", public_resources))
        if private_app_resources:
            lines.extend(self._format_subgraph("private_app", "Private Application Subnets", private_app_resources))
        if private_data_resources:
            lines.extend(self._format_subgraph("private_data", "Private Data Subnets", private_data_resources))

        for resource in root_resources:
            lines.append(self._indent(self._format_node(resource, technical=True), 2))

        lines.append("        end")
        lines.append("    end")

        for edge in self._advanced_edges(architecture, resources):
            lines.append(edge)

        return "\n".join(lines)

    def _advanced_edges(self, architecture: ArchitectureSpecification, resources: List[Resource]) -> List[str]:
        visible_ids = {resource.id for resource in resources}
        lines: List[str] = []
        entrypoint = next((res for res in resources if res.category == ResourceCategory.LOAD_BALANCING), None)
        if entrypoint:
            lines.append(f"    internet --> {self._node_id(entrypoint.id)}")

        for relationship in architecture.relationships:
            if relationship.source_id in visible_ids and relationship.target_id in visible_ids:
                lines.append(self._format_edge(relationship.source_id, relationship.target_id, relationship.label))

        nat_resources = [res for res in resources if "nat" in f"{res.name} {res.provider_type}".lower()]
        outbound_sources = [
            res for res in resources
            if res.category in {ResourceCategory.CONTAINER, ResourceCategory.COMPUTE}
            and res.diagram_visibility != DiagramVisibility.HIDDEN
        ]
        if nat_resources:
            nat_id = self._node_id(nat_resources[0].id)
            for resource in outbound_sources:
                lines.append(f"    {self._node_id(resource.id)} -. outbound .-> {nat_id}")

        return lines

    def _resources_for_public_zone(self, resources: List[Resource]) -> List[Resource]:
        results: List[Resource] = []
        for resource in resources:
            resource_text = f"{resource.name} {resource.provider_type}".lower()
            if resource.scope == ResourceScope.PUBLIC_SUBNET or "nat" in resource_text or resource.category == ResourceCategory.LOAD_BALANCING:
                results.append(resource)
        return results

    def _resources_for_private_app_zone(self, resources: List[Resource]) -> List[Resource]:
        results: List[Resource] = []
        for resource in resources:
            if resource.scope == ResourceScope.PRIVATE and resource.category in {ResourceCategory.CONTAINER, ResourceCategory.COMPUTE}:
                results.append(resource)
                continue
            if resource.category in {ResourceCategory.CONTAINER, ResourceCategory.COMPUTE} and resource.diagram_visibility != DiagramVisibility.HIDDEN:
                results.append(resource)
        return results

    def _resources_for_private_data_zone(self, resources: List[Resource]) -> List[Resource]:
        results: List[Resource] = []
        for resource in resources:
            if resource.category == ResourceCategory.DATABASE:
                results.append(resource)
                continue
            if resource.scope == ResourceScope.PRIVATE_SUBNET and resource.category == ResourceCategory.NETWORK:
                results.append(resource)
        return results

    def _format_subgraph(self, graph_id: str, title: str, resources: List[Resource]) -> List[str]:
        lines = [f'            subgraph {graph_id}["{title}"]']
        for resource in resources:
            lines.append(self._indent(self._format_node(resource, technical=True), 3))
        lines.append("            end")
        return lines

    def _format_node(self, resource: Resource, technical: bool) -> str:
        node_id = self._node_id(resource.id)
        label = self._technical_label(resource) if technical else self._simple_label(resource)
        if resource.category == ResourceCategory.DATABASE:
            return f'    {node_id}[("{label}")]'
        return f'    {node_id}["{label}"]'

    def _format_edge(self, source_id: str, target_id: str, label: str) -> str:
        source = self._node_id(source_id)
        target = self._node_id(target_id)
        clean_label = self._escape_label(label)
        return f'    {source} -->|"{clean_label}"| {target}'

    def _simple_label(self, resource: Resource) -> str:
        return self._escape_label(resource.name)

    def _technical_label(self, resource: Resource) -> str:
        provider_label = resource.provider_type.replace("_", " ").replace("-", " ").upper()
        return self._escape_label(f"{resource.name}<br/>{provider_label}")

    def _node_id(self, value: str) -> str:
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", value)
        sanitized = re.sub(r"_+", "_", sanitized).strip("_")
        return sanitized or "node"

    def _escape_label(self, value: str) -> str:
        text = value.replace('"', "").replace("[", "(").replace("]", ")")
        text = text.replace("{", "(").replace("}", ")").replace("|", "/")
        return text.strip()

    def _indent(self, text: str, level: int) -> str:
        prefix = "    " * level
        stripped = text.lstrip()
        return f"{prefix}{stripped}"
