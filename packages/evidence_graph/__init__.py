"""Legal Evidence Graph package (P3 PR-12): Claim <-> Element <-> Authority <-> Exhibit <-> Span."""
from .builder import build_evidence_graph
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
    "build_evidence_graph",
]
