"""Requested source ranges for attachment; no whole-engine CPU claim."""
import pytest

from tests.test_tk45_clause_effect_contract import LEAD, _trace_pipeline
from tests.test_tk45_authored_predicate_scope import LIMIT


@pytest.mark.parametrize('length', [8000, 16000, 32000])
def test_both_attachment_routes_request_bounded_source_ranges(monkeypatch, tmp_path, length):
    from packages.legal_engine import event_temporal_propositions as events

    requested = []
    per_route = {'_ATTACHMENT': [], '_AUXILIARY_ATTACHMENT': []}

    class Measured:
        def __init__(self, original, name):
            self.original = original
            self.name = name

        def fullmatch(self, text, start, end):
            requested.append(end - start)
            per_route[self.name].append(end - start)
            return self.original.fullmatch(text, start, end)

    for name in per_route:
        monkeypatch.setattr(events, name, Measured(getattr(events, name), name))
    block = LEAD + '상계의 의사표시를 해 놓은 이후 변제공탁을 완료하였으므로' + LIMIT + ' '
    text = block * (length // len(block))
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    assert all(per_route.values())
    assert sum(requested) <= len(text)
    assert max(requested) <= len(' 해 놓은 이후 ')
