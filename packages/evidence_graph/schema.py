"""Schema definitions for Legal Evidence Graph (P3 PR-12)."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class NodeKind(str, Enum):
    LEGAL_CLAIM = "LEGAL_CLAIM"
    REQUIREMENT_ELEMENT = "REQUIREMENT_ELEMENT"
    FACT_ASSERTION = "FACT_ASSERTION"
    AUTHORITY_SOURCE = "AUTHORITY_SOURCE"
    EXHIBIT_EVIDENCE = "EXHIBIT_EVIDENCE"
    SOURCE_SPAN = "SOURCE_SPAN"


class EdgeKind(str, Enum):
    REQUIRES_ELEMENT = "REQUIRES_ELEMENT"
    ASSERTS_SATISFACTION = "ASSERTS_SATISFACTION"
    GROUNDED_IN_AUTHORITY = "GROUNDED_IN_AUTHORITY"
    PROVED_BY_EXHIBIT = "PROVED_BY_EXHIBIT"
    CONTRADICTS = "CONTRADICTS"
    UNDERMINES = "UNDERMINES"
    LOCATED_AT = "LOCATED_AT"


@dataclass
class GraphNode:
    node_id: str
    kind: NodeKind
    label: str
    document_id: Optional[str] = None
    status: str = "UNVERIFIED"
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d


@dataclass
class GraphEdge:
    edge_id: str
    kind: EdgeKind
    source_id: str
    target_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d


@dataclass
class LegalEvidenceGraph:
    document_id: str
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)
    _edge_keys: Set[tuple[str, str, str]] = field(default_factory=set, repr=False)

    def add_node(self, node: GraphNode) -> GraphNode:
        if node.node_id not in self.nodes:
            self.nodes[node.node_id] = node
        return self.nodes[node.node_id]

    def add_edge(self, kind: EdgeKind, source_id: str, target_id: str, **attrs: Any) -> Optional[GraphEdge]:
        if source_id not in self.nodes or target_id not in self.nodes:
            return None
        key = (kind.value, source_id, target_id)
        if key in self._edge_keys:
            return None
        self._edge_keys.add(key)
        edge = GraphEdge(
            edge_id=f"EDG_{len(self.edges) + 1}",
            kind=kind,
            source_id=source_id,
            target_id=target_id,
            attributes=attrs,
        )
        self.edges.append(edge)
        return edge

    def outgoing(self, node_id: str, *, kind: Optional[EdgeKind] = None) -> List[GraphEdge]:
        return [
            e for e in self.edges
            if e.source_id == node_id and (kind is None or e.kind == kind)
        ]

    def incoming(self, node_id: str, *, kind: Optional[EdgeKind] = None) -> List[GraphEdge]:
        return [
            e for e in self.edges
            if e.target_id == node_id and (kind is None or e.kind == kind)
        ]

    def connected_components(self, *, ignore_kinds: Optional[Set[NodeKind]] = None) -> List[List[str]]:
        """Return undirected connected components of node_ids (optionally ignoring SOURCE_SPAN hubs)."""
        ignored = ignore_kinds if ignore_kinds is not None else {NodeKind.SOURCE_SPAN}
        adj: Dict[str, Set[str]] = defaultdict(set)
        active_ids = [nid for nid, n in self.nodes.items() if n.kind not in ignored]
        active_set = set(active_ids)
        for e in self.edges:
            if e.source_id in active_set and e.target_id in active_set:
                adj[e.source_id].add(e.target_id)
                adj[e.target_id].add(e.source_id)

        visited: Set[str] = set()
        components: List[List[str]] = []
        for nid in sorted(active_ids):
            if nid in visited:
                continue
            comp: List[str] = []
            q = deque([nid])
            visited.add(nid)
            while q:
                cur = q.popleft()
                comp.append(cur)
                for nxt in sorted(adj.get(cur, ())):
                    if nxt not in visited:
                        visited.add(nxt)
                        q.append(nxt)
            components.append(comp)
        return components

    def summary(self) -> Dict[str, Any]:
        by_kind: Dict[str, int] = defaultdict(int)
        for n in self.nodes.values():
            by_kind[n.kind.value] += 1
        by_edge: Dict[str, int] = defaultdict(int)
        for e in self.edges:
            by_edge[e.kind.value] += 1
        return {
            "document_id": self.document_id,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes_by_kind": dict(sorted(by_kind.items())),
            "edges_by_kind": dict(sorted(by_edge.items())),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "summary": self.summary(),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }
