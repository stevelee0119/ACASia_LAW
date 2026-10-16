"""Private immutable render evidence, emitted during the actual edit execution."""
from __future__ import annotations

MAX_SOURCE_CHARS = 65536
MAX_TRACE_CHARS = 131072
_CAP = object()


class _Piece:
    __slots__ = ('__source', '__ranges', '__rendered', '__origins', '__status')

    def __init__(self, source, ranges, rendered, origins, status, *, capability):
        if capability is not _CAP:
            raise TypeError('Internal render capture required')
        for key, value in zip(('source', 'ranges', 'rendered', 'origins', 'status'),
                              (source, ranges, rendered, origins, status)):
            object.__setattr__(self, '_Piece__' + key, value)

    def __setattr__(self, name, value):
        raise AttributeError('Immutable render capture')

    def __delattr__(self, name):
        raise AttributeError('Immutable render capture')

    def __repr__(self):
        return '<excerpt render capture>'

    def __deepcopy__(self, memo):
        return '<excerpt render capture>'

    def _data(self):
        return self.__source, self.__ranges, self.__rendered, self.__origins, self.__status


def _abstain_piece(rendered, status):
    if isinstance(rendered, str):
        rendered = str(rendered)  # Freeze a str subclass exactly as JSON renders it.
    return _Piece(None, None, rendered, None, status, capability=_CAP)


def capture_slice(source, start, end, rendered):
    if type(source) is not str or type(rendered) is not str:
        return _abstain_piece(rendered, 'INVALID_TRACE')
    if len(source) > MAX_SOURCE_CHARS:
        return _abstain_piece(rendered, 'ABSTAIN_CAPTURE_LIMIT')
    return _Piece(source, ((start, end),), rendered, tuple(range(start, end)), 'CAPTURED', capability=_CAP)


class _EditTrace:
    """Mutable execution-local accumulator; never stored on a request."""
    def __init__(self, source, start, end):
        self.source, self.ranges = source, ((start, end),)
        self.origins, self.parts = tuple(range(start, end)), []
        self.exhausted = False

    def _exhaust(self):
        self.exhausted = True
        self.origins, self.parts = (), []

    def replace(self, start, end, inserted):
        if self.exhausted:
            return
        if len(self.origins) - (end - start) + inserted > MAX_TRACE_CHARS:
            self._exhaust()
            return
        self.origins = self.origins[:start] + (None,) * inserted + self.origins[end:]

    def keep(self, start, end):
        if self.exhausted:
            return
        if len(self.parts) + end - start > MAX_TRACE_CHARS:
            self._exhaust()
            return
        self.parts.extend(self.origins[start:end])

    def insert(self, length):
        if self.exhausted:
            return
        if len(self.parts) + length > MAX_TRACE_CHARS:
            self._exhaust()
            return
        self.parts.extend((None,) * length)

    def finish_mask(self):
        if self.exhausted:
            return
        self.origins, self.parts = tuple(self.parts), []

    def seal(self, rendered):
        if self.exhausted:
            return _abstain_piece(rendered, 'ABSTAIN_CAPTURE_LIMIT')
        return _Piece(self.source, self.ranges, rendered, self.origins, 'CAPTURED', capability=_CAP)


class _ModelInputRenderer:
    __slots__ = ('__pii', '__excluded', '__original')

    def __init__(self, pii, excluded, original):
        object.__setattr__(self, '_ModelInputRenderer__pii', pii)
        object.__setattr__(self, '_ModelInputRenderer__excluded', tuple(excluded))
        object.__setattr__(self, '_ModelInputRenderer__original', original)

    def __setattr__(self, name, value):
        raise AttributeError('Immutable model renderer')

    def __delattr__(self, name):
        raise AttributeError('Immutable model renderer')

    def __repr__(self):
        return '<model input renderer>'

    def __call__(self, text):
        from packages.verification_engine.sanitized_input import strip_injections
        text = strip_injections(text, self.__excluded)
        return text if self.__original else self.__pii.mask_text(text).masked_text

    def _excerpt(self, source, end):
        from packages.verification_engine.sanitized_input import strip_injections
        text = source[:end]  # Same actual cut, before stripping/masking.
        if type(source) is not str or len(source) > MAX_SOURCE_CHARS:
            rendered = self(text)
            return rendered, _abstain_piece(rendered, 'ABSTAIN_CAPTURE_LIMIT')
        trace = _EditTrace(source, 0, min(end, len(source)))
        text = strip_injections(text, self.__excluded, _trace=trace)
        rendered = text if self.__original else self.__pii.mask_text(text, _trace=trace).masked_text
        return rendered, trace.seal(rendered)


def model_input_renderer(pii, excluded, *, original=False):
    return _ModelInputRenderer(pii, excluded, original)


def render_argument_context(hide, source):
    if type(hide) is _ModelInputRenderer:
        return hide._excerpt(source, 1000)
    rendered = hide(source[:1000])
    return rendered, _abstain_piece(rendered, 'ABSTAIN_NO_TRACE')
