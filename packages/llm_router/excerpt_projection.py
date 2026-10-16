"""Decode only surviving selected PHONE/RRN units; never infer scalar names."""
from __future__ import annotations

import re
import json

from packages.pii_engine.detector import detect

def _decode_string(literal, origins):
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
        if len(char) != 1:
            raise ValueError('Unsupported decoded unit')
        chars.append(char)
        spans.append((origins[cursor][0], origins[end - 1][1]))
        cursor = end
    return ''.join(chars), tuple(spans)


_NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
_HEX = frozenset('0123456789abcdefABCDEF')


def _string_end(text, start):
    cursor = start + 1
    while cursor < len(text):
        char = text[cursor]
        if char == '"':
            return cursor + 1
        if ord(char) < 32:
            raise ValueError('Control character')
        if char == '\\':
            cursor += 1
            if cursor >= len(text):
                raise ValueError('Unfinished escape')
            if text[cursor] == 'u':
                if len(text[cursor + 1:cursor + 5]) != 4 or any(c not in _HEX for c in text[cursor + 1:cursor + 5]):
                    raise ValueError('Unicode escape')
                cursor += 4
            elif text[cursor] not in '"\\/bfnrt':
                raise ValueError('Unknown escape')
        cursor += 1
    raise ValueError('Unfinished string')


def _validated_tokens(text):
    """JSON syntax stack, not Python recursive object construction."""
    todo, tokens, cursor, steps = ['EOF', 'VALUE'], [], 0, 0
    while todo:
        steps += 1
        if steps > 8 * len(text) + 64:
            raise RuntimeError('Work budget')
        while cursor < len(text) and text[cursor] in ' \n\t\r':
            cursor += 1
        state = todo.pop()
        char = text[cursor] if cursor < len(text) else ''
        if state == 'EOF':
            if cursor != len(text):
                raise ValueError('Trailing content')
        elif state in ('KEY', 'OBJECT_FIRST'):
            if state == 'OBJECT_FIRST' and char == '}':
                cursor += 1
                continue
            if char != '"':
                raise ValueError('Object key')
            end = _string_end(text, cursor)
            tokens.append((cursor, end))
            cursor = end
            todo.append('COLON')
        elif state == 'COLON':
            if char != ':':
                raise ValueError('Colon')
            cursor += 1
            todo.extend(('OBJECT_AFTER', 'VALUE'))
        elif state in ('OBJECT_AFTER', 'ARRAY_AFTER'):
            closing = '}' if state == 'OBJECT_AFTER' else ']'
            if char == closing:
                cursor += 1
            elif char == ',':
                cursor += 1
                todo.append('KEY' if state == 'OBJECT_AFTER' else 'ARRAY_VALUE')
            else:
                raise ValueError('Comma or end')
        elif state in ('ARRAY_FIRST', 'ARRAY_VALUE'):
            if state == 'ARRAY_FIRST' and char == ']':
                cursor += 1
            else:
                todo.extend(('ARRAY_AFTER', 'VALUE'))
        elif state == 'VALUE':
            if char == '"':
                end = _string_end(text, cursor)
                tokens.append((cursor, end))
                cursor = end
            elif char in ('{', '['):
                cursor += 1
                todo.append('OBJECT_FIRST' if char == '{' else 'ARRAY_FIRST')
            elif any(text.startswith(literal, cursor) for literal in ('true', 'false', 'null')):
                cursor += next(len(literal) for literal in ('true', 'false', 'null') if text.startswith(literal, cursor))
            else:
                number = _NUMBER.match(text, cursor)
                if number is None:
                    raise ValueError('Value')
                cursor = number.end()
    return tuple(tokens)


def _mapped_nodes(source):
    agenda = [(source, tuple((i, i + 1) for i in range(len(source))))]
    remaining, nodes = 8 * len(source) + 64, []
    while agenda:
        text, origins = agenda.pop()
        remaining -= len(text)
        if remaining < 0:
            return 'ABSTAIN_WORK', ()
        try:
            tokens = _validated_tokens(text)
        except ValueError:
            if text is source:
                return 'ABSTAIN_UNSUPPORTED', ()
            continue  # An ordinary decoded string is not another JSON layer.
        except RuntimeError:
            return 'ABSTAIN_WORK', ()
        for start, end in tokens:
            value, mapped = _decode_string(text[start:end], origins[start:end])
            nodes.append((value, mapped))
            agenda.append((value, mapped))
    return 'READY', tuple(nodes)


def _validated_trace(source, ranges, rendered, output_origins):
    """Validate immutable capability data before any decoder abstention.

    Only exact built-in types are read. Mutable/arbitrary collections cannot
    execute iteration/comparison hooks and become decoder-error fallbacks.
    Empty selection is represented by an explicit zero-width range.
    """
    if type(source) is not str or type(rendered) is not str or type(ranges) is not tuple or not ranges:
        return 'INVALID_TRACE', None
    previous_end = 0
    for pair in ranges:
        if type(pair) is not tuple or len(pair) != 2:
            return 'INVALID_TRACE', None
        start, end = pair
        if type(start) is not int or type(end) is not int or not previous_end <= start <= end <= len(source):
            return 'INVALID_TRACE', None
        previous_end = end
    if output_origins is None:
        return 'ABSTAIN_NO_TRACE', None  # Explicit opaque renderer, not malformed present data.
    if type(output_origins) is not tuple or len(rendered) != len(output_origins):
        return 'INVALID_TRACE', None
    source_to_output, previous = {}, -1
    for output, origin in enumerate(output_origins):
        if origin is None:
            continue  # Inserted/replaced characters have no source owner.
        if (type(origin) is not int or not previous < origin < len(source)
                or source[origin] != rendered[output]
                or not any(start <= origin < end for start, end in ranges)):
            return 'INVALID_TRACE', None
        previous = origin
        source_to_output[origin] = output
    return 'VALID_TRACE', source_to_output


def occurrence_projection(source, ranges, rendered, output_origins):
    """Return safe status/matches; never authenticate via substring existence."""
    status, source_to_output = _validated_trace(source, ranges, rendered, output_origins)
    if status != 'VALID_TRACE':
        return status, ()
    # Decoder exceptions are eligible to abstain only after valid capability
    # structure, types, ranges and source→rendered correspondence are proven.
    try:
        status, nodes = _mapped_nodes(source)
        if status != 'READY':
            return status, ()
        found = []
        for text, mapped in nodes:
            run_start, prior_last = None, None
            for index in range(len(text) + 1):
                owned = False
                if index < len(text):
                    first, last = mapped[index]
                    output = source_to_output.get(first)
                    owned = output is not None and all(
                        source_to_output.get(raw) == output + raw - first for raw in range(first, last))
                    consecutive = prior_last is None or output == prior_last + 1
                else:
                    consecutive = False
                if run_start is not None and (not owned or not consecutive):
                    for match in detect(text[run_start:index]):
                        if match.kind in ('PHONE', 'RRN') and match.confidence >= 0.6:
                            first = mapped[run_start + match.start][0]
                            last = mapped[run_start + match.end - 1][1]
                            found.append((match.kind, match.text, (first, last)))
                    run_start = None
                if owned:
                    if run_start is None:
                        run_start = index
                    prior_last = source_to_output[mapped[index][1] - 1]
                else:
                    prior_last = None
        return 'READY', tuple(found)
    except (ValueError, TypeError, KeyError, IndexError, RecursionError, OverflowError):
        return 'ABSTAIN_DECODER', ()
