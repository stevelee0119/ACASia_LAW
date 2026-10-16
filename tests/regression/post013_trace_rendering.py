"""Public prototype instruments actual strip/mask execution, never replays it.

Only test-local engine instances are observed. A product renderer would emit
these tuples directly at its edit points, rather than install instrumentation.
"""
from __future__ import annotations


_CAP = object()


class Snapshot:
    __slots__ = ('__text',)

    def __init__(self, text):
        object.__setattr__(self, '_Snapshot__text', str(text))

    def __setattr__(self, name, value):
        raise AttributeError('Immutable snapshot')

    def __delattr__(self, name):
        raise AttributeError('Immutable snapshot')

    def __repr__(self):
        return '<source snapshot>'

    def __deepcopy__(self, memo):
        return '<source snapshot>'

    def _value(self):
        return self.__text


class TracedText(str):
    __slots__ = ('__snapshot', '__origins', '__observe')

    def __new__(cls, text, snapshot, origins, *, capability, observe=None):
        if capability is not _CAP:
            raise TypeError('Internal trace factory required')
        value = super().__new__(cls, text)
        object.__setattr__(value, '_TracedText__snapshot', snapshot)
        object.__setattr__(value, '_TracedText__origins', tuple(origins))
        object.__setattr__(value, '_TracedText__observe', observe)
        return value

    def __setattr__(self, name, value):
        raise AttributeError('Immutable traced text')

    def __delattr__(self, name):
        raise AttributeError('Immutable traced text')

    def __repr__(self):
        return '<source trace>'

    def __deepcopy__(self, memo):
        return '<source trace>'

    def __getitem__(self, key):
        text = super().__getitem__(key)
        if type(key) is not slice:
            return text
        mapped = self.__origins[key]
        if self.__observe is not None:
            self.__observe(str(text), tuple(mapped))
        return TracedText(text, self.__snapshot, mapped, capability=_CAP, observe=self.__observe)

    def __add__(self, other):
        if type(other) is TracedText:
            if other.__snapshot is not self.__snapshot:
                raise ValueError('Cross-snapshot join')
            origins = other.__origins
        else:
            origins = (None,) * len(other)
        return TracedText(str(self) + str(other), self.__snapshot, self.__origins + origins,
                          capability=_CAP, observe=self.__observe)

    def __radd__(self, other):
        return TracedText(str(other) + str(self), self.__snapshot, (None,) * len(other) + self.__origins,
                          capability=_CAP, observe=self.__observe)

    def _evidence(self):
        return self.__snapshot, self.__origins


def source_text(snapshot):
    text = snapshot._value()
    return TracedText(text, snapshot, tuple(range(len(text))), capability=_CAP)


def mask_once(pii, text):
    """Observe real _mask_matches slices and real pseudonym calls once.

    Actual event order is token-call → unchanged-slice → appended token, with
    one final tail slice. No matches means the actual original is returned.
    Reassembling recorded append operands is validation, not a new masking
    pass/detection/token allocation or a diff alignment.
    """
    assert type(text) is TracedText
    snapshot, origins = text._evidence()
    events, active = [], False
    original_mask = pii._mask_matches
    original_token = pii.store.pseudonym_for

    def observe(value, mapped):
        if active:
            events.append(('slice', value, mapped))

    def token(kind, value):
        result = original_token(kind, value)
        if active:
            events.append(('token', '[' + result + ']', None))
        return result

    def mask_matches(actual, matches):
        nonlocal active
        active = True
        try:
            return original_mask(actual, matches)
        finally:
            active = False

    observed = TracedText(str(text), snapshot, origins, capability=_CAP, observe=observe)
    pii._mask_matches, pii.store.pseudonym_for = mask_matches, token
    try:
        result = pii.mask_text(observed)  # Single actual detector/mask pass.
    finally:
        pii._mask_matches, pii.store.pseudonym_for = original_mask, original_token
    if not events:
        if str(result.masked_text) != str(text) or result.matches:
            raise ValueError('Unobserved transform')
        return TracedText(str(result.masked_text), snapshot, origins, capability=_CAP)
    pieces, mapped, cursor = [], [], 0
    while cursor + 1 < len(events):
        emitted, unchanged = events[cursor], events[cursor + 1]
        if emitted[0] != 'token' or unchanged[0] != 'slice':
            raise ValueError('Unexpected append event order')
        pieces.extend((unchanged[1], emitted[1]))
        mapped.extend(unchanged[2])
        mapped.extend((None,) * len(emitted[1]))
        cursor += 2
    if cursor != len(events) - 1 or events[cursor][0] != 'slice':
        raise ValueError('Missing tail append')
    pieces.append(events[cursor][1])
    mapped.extend(events[cursor][2])
    if ''.join(pieces) != str(result.masked_text):
        raise ValueError('Append events differ from actual renderer')
    return TracedText(str(result.masked_text), snapshot, tuple(mapped), capability=_CAP)


def strip_once(text, excluded):
    from packages.verification_engine.sanitized_input import strip_injections
    # Actual source slice + placeholder + source slice operations preserve
    # positional ownership through TracedText. No replacement algorithm copy.
    result = strip_injections(text, excluded)
    if type(result) is not TracedText:
        raise ValueError('Unattested strip result')
    return result
