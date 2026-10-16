"""Preserve the approved public b1e baseline of the design-only comparisons.

The named provider is now a real product capability. The original spike's
baseline must still mean b1e, without rewriting UNKNOWN expectations to match
the new product. This adapter is test-only and never imported by packages.
"""
from pytest import MonkeyPatch
from packages.document_engine import actualtext_boundaries as provider,pdf_parser
from test_tk44_actualtext_provider import _parse as current_parse
from tk44_b1e_actualtext_baseline import inline_actualtext_edges as baseline_provider

PUBLIC_BASE='b1e506f2eab2b830cb8fb7fd074d22dcdc3be589'
CANONICAL_INTERPRETER=provider._Interpreter
CANONICAL_DEVICE=provider._Device


def _parse(path):
    # An already-active test prototype remains the proposal under comparison.
    if (pdf_parser.inline_actualtext_edges is not provider.inline_actualtext_edges
            or provider._Interpreter is not CANONICAL_INTERPRETER
            or provider._Device is not CANONICAL_DEVICE):
        return current_parse(path)
    def edges(*args,named_capture=None,**kwargs):
        return baseline_provider(*args,**kwargs)
    with MonkeyPatch.context() as patch:
        patch.setattr(pdf_parser,'inline_actualtext_edges',edges)
        return current_parse(path)
