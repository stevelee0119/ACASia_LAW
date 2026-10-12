"""Comparison-only decoded/source offset projection; no product hook."""
from __future__ import annotations

import json
import re

from packages.llm_router import privacy
from packages.pii_engine.detector import detect


_STRINGS = re.compile(r'"(?:[^"\\]|\\.)*"')


def _decode_string(literal, origins):
    """Each decoded character requires its entire original spelling."""
    chars, spans, cursor = [], [], 1
    while cursor < len(literal) - 1:
        end = cursor + 1
        if literal[cursor] == '\\':
            end = cursor + (6 if literal[cursor + 1] == 'u' else 2)
            if literal[cursor + 1] == 'u':
                code = int(literal[cursor + 2:end], 16)
                if (0xD800 <= code <= 0xDBFF and literal[end:end + 2] == '\\u'
                        and 0xDC00 <= int(literal[end + 2:end + 6], 16) <= 0xDFFF):
                    end += 6
            char = json.loads('"' + literal[cursor:end] + '"')
        else:
            char = literal[cursor]
        assert len(char) == 1
        chars.append(char)
        spans.append((origins[cursor][0], origins[end - 1][1]))
        cursor = end
    decoded = ''.join(chars)
    assert decoded == json.loads(literal)
    return decoded, tuple(spans)


def _nodes(source, origins):
    # Parsing authorizes syntax interpretation only for this complete source;
    # neither keys nor scalar spellings authenticate a production consumer.
    if privacy._try_json_parse(source) is None:
        return
    for token in _STRINGS.finditer(source):
        value, mapped = _decode_string(token.group(), origins[token.start():token.end()])
        yield value, mapped
        yield from _nodes(value, mapped)


def projected_numeric_matches(source, ranges, rendered):
    """Inspect selected decoded runs; confirm every candidate survives masking.

    In the claim producer source is the actual post-mask complete text; in the
    argument producer ranges select before the actual cut→mask rendering.
    Omitted ranges are never concatenated into a synthetic numeric identifier.
    The exact raw support must still occur in the actual rendered leaf: this
    excludes removed/masked material without guessing a mask alignment.
    """
    assert type(source) is str and type(rendered) is str
    assert all(0 <= start <= end <= len(source) for start, end in ranges)
    origins = tuple((i, i + 1) for i in range(len(source)))
    found = []
    for text, mapped in _nodes(source, origins):
        run_start = None
        for index in range(len(text) + 1):
            retained = index < len(text) and any(
                start <= mapped[index][0] and mapped[index][1] <= end for start, end in ranges)
            if retained and run_start is None:
                run_start = index
            if not retained and run_start is not None:
                fragment = text[run_start:index]
                for match in detect(fragment):
                    if match.kind not in ("PHONE", "RRN") or match.confidence < 0.6:
                        continue
                    first = mapped[run_start + match.start][0]
                    last = mapped[run_start + match.end - 1][1]
                    raw_support = source[first:last]
                    # Require support to belong to one selected range and to
                    # survive the actual transform. A full source match alone
                    # is never sufficient.
                    if (any(start <= first and last <= end for start, end in ranges)
                            and raw_support in rendered):
                        found.append((match.kind, match.text, (first, last)))
                run_start = None
    return tuple(found)


def projection_json(source, ranges, rendered):
    return json.dumps([text for _, text, _ in projected_numeric_matches(source, ranges, rendered)], ensure_ascii=False)
