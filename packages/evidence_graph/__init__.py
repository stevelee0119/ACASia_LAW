"""Legal Evidence Graph package (P3 PR-12): Claim <-> Element <-> Authority <-> Exhibit <-> Span."""
from .analyzer import (
    analyze_evidence_graph,
    build_prerequisite_checklist,
    deduplicate_findings_by_graph,
)
from .builder import build_evidence_graph, default_requirement_rules
from .schema import (
    EdgeKind,
    GraphEdge,
    GraphNode,
    LegalEvidenceGraph,
    NodeKind,
)

__all__ = [
    "EdgeKind",
    "GraphEdge",
    "GraphNode",
    "LegalEvidenceGraph",
    "NodeKind",
    "analyze_evidence_graph",
    "build_evidence_graph",
    "build_prerequisite_checklist",
    "deduplicate_findings_by_graph",
    "default_requirement_rules",
]
