"""Conservative inline Span replacement-to-original-glyph boundary evidence.

This provider is independent of layout fullness and lexical word segmentation.
PAGE named properties are resolved locally. Selected Form properties are
inspection only; unproved scope/rendering never certifies boundaries.
"""
from __future__ import annotations

from collections import defaultdict
from bisect import bisect_right
import hashlib
import math
from typing import Any

from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdftypes import PDFObjRef, PDFStream
from pdfminer.psparser import PSLiteral, literal_name
from pdfminer.utils import PDFDocEncoding
from .named_actualtext_capture import NamedActualTextCapture

MAX_DEPTH = 32
MAX_GLYPHS = 500_000
MAX_LOGICAL_LENGTH = 64_000
CELL_SIZE = 64
MAX_PAINT_CELLS = 256


def _strict_text(value: Any) -> str | None:
    if not isinstance(value, bytes):
        return None
    try:
        if value.startswith(b'\xfe\xff'):
            text = value[2:].decode('utf-16-be')
        else:
            text = ''.join(PDFDocEncoding[c] for c in value)
        if (len(text) > MAX_LOGICAL_LENGTH or any(
                ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF
                or c in '\u200b\u200c\u200d\u2060\ufeff' for c in text)):
            return None
        return text
    except (UnicodeError, IndexError):
        return None


class _Device(PDFPageAggregator):
    def __init__(self, *args, named_capture=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.named_capture = named_capture
        self.named_witness = None
        self.resource_queries = self.resource_hops = self.resource_max_hops = 0
        self.contexts, self.stack, self.glyphs = [], [], []
        self.form_depth = 0
        self.unsafe_graphics = False
        self.render_mode = 0
        self.over_budget = False
        self.association_visits = 0
        self.figure_states = []
        self.sequence = 0
        self.glyph_sequence = []
        self.paints = []
        self.unbounded_paint_sequence = 0
        self.unbounded_paints = 0

    def begin_tag(self, tag, props=None):
        if len(self.stack) >= MAX_DEPTH:
            self.over_budget = True
            return
        name = literal_name(tag)
        if self.named_capture is not None and self.named_witness is not None and isinstance(props, dict) and 'ActualText' in props:
            capture = self.named_capture
            if not capture.context():
                self.over_budget = True
                self.stack.append({'closed': False, 'unknown': True, 'eligible': False,
                                   'ancestors': tuple(self.stack), 'glyphs': []})
                return
            actual = capture.strict(props['ActualText'])
            self.over_budget |= capture.exceeded
            context = {'closed': False, 'unknown': name != 'Span' or actual is None or 'OC' in props,
                       'actual': actual, 'ancestors': tuple(self.stack), 'glyphs': [], 'eligible': True,
                       'id': len(self.contexts), 'resource_witness': self.named_witness}
            self.contexts.append(context)
            self.stack.append(context)
            return
        unknown = name == 'OC' or (props is not None and not isinstance(props, dict))
        context = {'closed': False, 'unknown': unknown, 'actual': None,
                   'ancestors': tuple(self.stack), 'glyphs': [], 'eligible': True}
        if isinstance(props, dict) and 'ActualText' in props:
            context['actual'] = _strict_text(props['ActualText'])
            context['unknown'] = name != 'Span' or context['actual'] is None or 'OC' in props
            context['id'] = len(self.contexts)
            self.contexts.append(context)
        self.stack.append(context)

    def end_tag(self):
        if self.stack:
            self.stack.pop()['closed'] = True
        else:
            self.over_budget = True

    def render_string(self, textstate, seq, ncs, graphicstate):
        self.render_mode = getattr(textstate, 'render', None)
        return super().render_string(textstate, seq, ncs, graphicstate)

    def render_char(self, *args, **kwargs):
        advance = super().render_char(*args, **kwargs)
        glyph = self.cur_item._objs[-1]
        if len(self.glyphs) >= MAX_GLYPHS:
            self.over_budget = True
            return advance
        index = len(self.glyphs)
        self.sequence += 1
        self.glyph_sequence.append(self.sequence)
        self.glyphs.append(glyph)
        matrix = glyph.matrix
        upright = (glyph.upright and matrix[1] == matrix[2] == 0
                   and matrix[0] > 0 and matrix[3] > 0)
        for context in self.stack:
            if 'id' in context:
                context['glyphs'].append(index)
                self.association_visits += 1
                context['eligible'] &= bool(upright and self.render_mode == 0
                                            and not self.unsafe_graphics and not self.form_depth)
        return advance

    def begin_figure(self, *args, **kwargs):
        self.figure_states.append(self.unsafe_graphics)
        self.form_depth += 1
        return super().begin_figure(*args, **kwargs)

    def end_figure(self, *args, **kwargs):
        result = super().end_figure(*args, **kwargs)
        self.form_depth -= 1
        self.unsafe_graphics = self.figure_states.pop()
        return result

    def _unsupported_paint(self):
        for context in self.stack:
            if 'id' in context:
                context['eligible'] = False

    def render_image(self, *args, **kwargs):
        self._unsupported_paint()
        result = super().render_image(*args, **kwargs)
        self._record_paint(self.cur_item._objs[-1])
        return result

    def paint_path(self, *args, **kwargs):
        self._unsupported_paint()
        before = len(self.cur_item._objs)
        result = super().paint_path(*args, **kwargs)
        for item in self.cur_item._objs[before:]:
            self._record_paint(item)
        return result

    def _record_paint(self, item):
        self.sequence += 1
        if len(self.paints) >= MAX_GLYPHS:
            self.over_budget = True
        else:
            self.paints.append((self.sequence, item.bbox))

    def unsupported_paint(self):
        self._unsupported_paint()
        self.sequence += 1
        self.unbounded_paint_sequence = self.sequence
        self.unbounded_paints += 1


class _Interpreter(PDFPageInterpreter):
    """Unproved alpha/soft masks/clipping are local graphics-state blockers."""
    def render_contents(self, resources, streams, *args, **kwargs):
        # pdfminer inherits PAGE resources for absent/empty Form Resources.
        # Retain the invoked stream's own operand; the interpreter's fallback
        # dictionary is not proof of a selected native Form property.
        self._form_inspection_resources = None
        if self.device.form_depth:
            capture = self.device.named_capture
            if capture is not None:
                capture.inspection_complete = False
            if len(streams) == 1:
                self._form_inspection_resources = streams[0].get('Resources')
        return super().render_contents(resources, streams, *args, **kwargs)

    def init_state(self, ctm):
        super().init_state(ctm)
        self._unsafe_stack = []

    def process_page(self, page):
        capture = self.device.named_capture
        if capture is None:
            return super().process_page(page)
        capture.begin_page()
        completed = False
        try:
            result = super().process_page(page)
            completed = True
            return result
        finally:
            capture.end_page(completed)

    def do_BDC(self, tag, props):
        capture = self.device.named_capture
        witness = None
        if capture is not None and self.device.form_depth and isinstance(props, PSLiteral):
            # Keep the literal operand: a Form lookup is never a PAGE boundary
            # witness, and inspecting one selection cannot prove Form coverage.
            capture.inspection_complete = False
            if capture.context():
                own_resources = self._form_inspection_resources
                scope = (self.device.pageno, id(own_resources), 'FORM_INSPECTION_ONLY')
                resources = _resolve_form_inspection(own_resources, capture, scope)
                properties = _resolve_form_inspection(resources.get('Properties'), capture, scope) if isinstance(resources, dict) else None
                selected = _resolve_form_inspection(properties.get(literal_name(props)), capture, scope) if isinstance(properties, dict) else None
                if isinstance(selected, dict):
                    if 'ActualText' in selected:
                        capture.inspect(_resolve_form_inspection(selected['ActualText'], capture, scope))
                    else:
                        capture.actualtext_absent += 1
                elif isinstance(properties, dict) and literal_name(props) not in properties:
                    capture.selected_property_missing += 1
                else:
                    capture.selected_property_invalid += 1
        if capture is not None and isinstance(props, PSLiteral) and not self.device.form_depth:
            capture.named_selection_requests += 1
            self.device.resource_queries += 1
            hops = []
            scope = (self.device.pageno, id(self.resources))
            def resolve(value):
                seen = set()
                depth = 0
                while isinstance(value, PDFObjRef):
                    identity = (id(value.doc), value.objid)
                    if identity in seen or len(hops) == 8:
                        capture.resolution_failures += 1
                        capture.inspection_complete = False
                        return None
                    seen.add(identity)
                    hops.append(value.objid)
                    depth += 1
                    self.device.resource_max_hops = max(self.device.resource_max_hops, depth)
                    value = capture.reference(value, scope)
                return value
            resources = resolve(self.resources)
            properties = resolve(resources.get('Properties')) if isinstance(resources, dict) else None
            name = literal_name(props)
            selected = resolve(properties.get(name)) if isinstance(properties, dict) else None
            if isinstance(selected, dict):
                witness = {'name': name, 'object_reference_chain': list(hops),
                           'scope': 'CURRENT_INTERPRETER_RESOURCES', 'max_reference_depth': 8}
                if 'ActualText' in selected:
                    capture.inspect(resolve(selected['ActualText']))
                else:
                    capture.actualtext_absent += 1
                props = selected
            else:
                capture.inspection_complete = False
                if isinstance(properties, dict) and name not in properties:
                    capture.selected_property_missing += 1
                else:
                    capture.selected_property_invalid += 1
            self.device.resource_hops += len(hops)
        self.device.named_witness = witness
        try:
            super().do_BDC(tag, props)
        finally:
            self.device.named_witness = None
        if capture is not None:
            self.device.over_budget |= capture.exceeded

    def do_q(self):
        self._unsafe_stack.append(self.device.unsafe_graphics)
        super().do_q()

    def do_Q(self):
        if self._unsafe_stack:
            self.device.unsafe_graphics = self._unsafe_stack.pop()
        else:
            self.device.unsafe_graphics = True
        super().do_Q()

    def do_gs(self, name):
        # This phase does not certify ExtGState opacity/soft-mask semantics.
        self.device.unsafe_graphics = True

    def do_W(self):
        self.device.unsafe_graphics = True
        super().do_W()

    def do_W_a(self):
        self.device.unsafe_graphics = True
        super().do_W_a()

    def do_sh(self, name):
        # pdfminer does not expose shading bounds/opacity to the layout device.
        # Its unknown coverage cannot certify previously drawn source glyphs.
        self.device.unsupported_paint()
        super().do_sh(name)


def _key(text, x0, y0, x1, y1, font):
    return text, x0, y0, x1, y1, font


def _cells(box):
    if not all(math.isfinite(v) for v in box):
        return None
    x0, y0, x1, y1 = [math.floor(v / CELL_SIZE) for v in box]
    if x1 < x0 or y1 < y0 or (x1 - x0 + 1) * (y1 - y0 + 1) > MAX_PAINT_CELLS:
        return None
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def _occluded(device):
    """Source-local future-paint overlap; prior backgrounds do not hide text.

    Spatial bucket references are capped; chronological lists allow binary
    lookup instead of scanning preceding paint for every glyph. Complex input
    exceeding the explicit linear candidate budget has no provider proof.
    """
    buckets = defaultdict(list)
    references = checks = queries = 0
    for sequence, box in device.paints:
        cells = _cells(box)
        if cells is None:
            return None, {'unsupported_paint_bounds': True}
        for cell in cells:
            buckets[cell].append((sequence, box))
            references += 1
    hidden = set()
    for index, glyph in enumerate(device.glyphs):
        cells = _cells(glyph.bbox)
        if cells is None:
            hidden.add(index)
            continue
        for cell in cells:
            records = buckets.get(cell, [])
            queries += 1
            start = bisect_right(records, device.glyph_sequence[index], key=lambda item: item[0])
            for paint_index in range(start, len(records)):
                checks += 1
                if checks > MAX_DEPTH * max(1, len(device.glyphs)):
                    return None, {'paint_candidate_visits': checks, 'paint_budget_exceeded': True}
                x0, y0, x1, y1 = records[paint_index][1]
                if glyph.x0 < x1 and glyph.x1 > x0 and glyph.y0 < y1 and glyph.y1 > y0:
                    hidden.add(index)
                    break
            if index in hidden:
                break
    return hidden, {'paint_bucket_references': references, 'paint_candidate_visits': checks,
                    'paint_bucket_binary_queries': queries}


def _resolve_form_inspection(value, capture, scope):
    """Bound each selected lookup and share the document's capture budgets."""
    seen = set()
    while isinstance(value, PDFObjRef):
        identity = (id(value.doc), value.objid)
        if identity in seen or len(seen) == 8:
            capture.resolution_failures += 1
            capture.inspection_complete = False
            return None
        seen.add(identity)
        value = capture.reference(value, scope)
    return value


def _named_available(page, capture):
    capture.availability_queries += 1
    seen, hops = set(), 0
    def resolve(value):
        nonlocal hops
        while isinstance(value, PDFObjRef):
            identity = (id(value.doc), value.objid)
            if identity in seen or hops == 8:
                capture.resolution_failures += 1
                capture.inspection_complete = False
                return None
            seen.add(identity)
            hops += 1
            value = capture.reference(value, (page.page_number, 'AVAILABILITY'))
        return value
    resources = resolve(page.page_obj.resources)
    properties = resolve(resources.get('Properties')) if isinstance(resources, dict) else None
    if isinstance(properties, dict):
        return True
    # Check stream dictionaries only. The interpreter, rather than preflight,
    # follows invoked Form content; images alone must not admit a second pass.
    scope = (page.page_number, 'FORM_AVAILABILITY')
    resources = _resolve_form_inspection(page.page_obj.resources, capture, scope)
    xobjects = _resolve_form_inspection(resources.get('XObject'), capture, scope) if isinstance(resources, dict) else None
    if not isinstance(xobjects, dict):
        return False
    for value in xobjects.values():
        # Share the document context budget even for direct stream objects.
        if not capture.context():
            return False
        stream = _resolve_form_inspection(value, capture, scope)
        if not isinstance(stream, PDFStream):
            continue
        subtype = _resolve_form_inspection(stream.get('Subtype'), capture, scope)
        if isinstance(subtype, PSLiteral) and literal_name(subtype) == 'Form':
            return True
    return False


def inline_actualtext_edges(page, chars: list[dict[str, Any]], lines: list[list[dict[str, Any]]], *, excluded_glyphs=frozenset(), named_capture=None):
    """Return certified line-edge records and deterministic mapping accounting.

    Each source character is indexed once; nested associations are bounded by
    MAX_DEPTH. No per-boundary whole-page scans or duplicate logical text records.
    Exceptions/capabilities unavailable return no proof, without parse warnings.
    """
    capture = named_capture if named_capture is not None else NamedActualTextCapture()
    try:
        if not any(b'/ActualText' in stream.get_data() for stream in page.page_obj.contents) and not _named_available(page, capture):
            capture.inspection_unavailable_pages += 1
            return {}, {'version': 1, 'provider': 'INLINE_SPAN_ACTUALTEXT', 'certified_edges': 0,
                        'inspection_unavailable': True, 'document_capture_snapshot': capture.snapshot()}
        device = _Device(page.pdf.rsrcmgr, pageno=page.page_number, laparams=page.pdf.laparams, named_capture=capture)
        _Interpreter(page.pdf.rsrcmgr, device).process_page(page.page_obj)
        accounting = {'version': 1, 'provider': 'INLINE_SPAN_ACTUALTEXT',
                      'original_glyphs': len(chars), 'rendered_glyphs': len(device.glyphs),
                      'source_spans': len(device.contexts), 'association_visits': device.association_visits,
                      'max_depth': MAX_DEPTH, 'over_budget': device.over_budget,
                      'unbounded_paints': device.unbounded_paints,
                      'resource_queries': device.resource_queries, 'resource_reference_hops': device.resource_hops,
                      'resource_max_hops': device.resource_max_hops, 'resource_property_entries_scanned': 0,
                      'document_capture_snapshot': capture.snapshot()}
        if not chars or getattr(page, 'rotation', 0):
            accounting.update(certified_edges=0, inspection_only=True)
            return {}, accounting
        if device.over_budget:
            return {}, accounting
        if not any(context['eligible'] and not context['unknown'] and context['closed']
                   and not any(parent['unknown'] or not parent['closed'] for parent in context['ancestors'])
                   for context in device.contexts):
            accounting['certified_edges'] = 0
            return {}, accounting
        occluded, paint_accounting = _occluded(device)
        accounting.update(paint_accounting)
        if occluded is None:
            return {}, accounting
        page_keys = defaultdict(list)
        positions = {}
        original_ids = {id(char): i for i, char in enumerate(chars)}
        for line_index, line in enumerate(lines):
            for char_index, char in enumerate(line):
                positions[original_ids[id(char)]] = (line_index, char_index, len(line))
        for index, char in enumerate(chars):
            page_keys[_key(char['text'], char['x0'], char['y0'], char['x1'], char['y1'], char['fontname'])].append(index)
        mapped = []
        for glyph in device.glyphs:
            matches = page_keys[_key(glyph.get_text(), *glyph.bbox, glyph.fontname)]
            mapped.append(matches[0] if len(matches) == 1 else None)
        coverage = [0] * len(device.glyphs)
        for context in device.contexts:
            for index in context['glyphs']:
                coverage[index] += 1
        edges = {}
        for context in device.contexts:
            if (context['unknown'] or not context['closed'] or not context['eligible']
                    or any(parent['unknown'] or not parent['closed'] for parent in context['ancestors'])):
                continue
            if context['glyphs'] and device.glyph_sequence[context['glyphs'][0]] < device.unbounded_paint_sequence:
                continue
            logical, cursor, previous = context['actual'], 0, None
            proposals, valid = [], bool(context['glyphs'])
            for rendered_index in context['glyphs']:
                index = mapped[rendered_index]
                if (index is None or coverage[rendered_index] != 1 or index not in positions
                        or index in excluded_glyphs or rendered_index in occluded):
                    valid = False
                    break
                char = chars[index]
                if (len(char['text']) != 1 or not all(math.isfinite(float(char[k])) for k in ('x0', 'x1', 'top', 'bottom'))
                        or char['x0'] < 0 or char['x1'] > page.width or char['top'] < 0 or char['bottom'] > page.height):
                    valid = False
                    break
                if previous is not None:
                    old_line, old_pos, old_count = positions[previous]
                    new_line, new_pos, _ = positions[index]
                    if new_line == old_line and new_pos != old_pos + 1:
                        valid = False
                        break
                    if new_line != old_line:
                        if new_line != old_line + 1 or old_pos != old_count - 1 or new_pos != 0:
                            valid = False
                            break
                        start = cursor
                        separator = ' ' if logical[cursor:cursor + 1] == ' ' and not char['text'].isspace() else ''
                        cursor += len(separator)
                        proposals.append((previous, index, separator, start, cursor))
                if logical[cursor:cursor + 1] != char['text']:
                    valid = False
                    break
                cursor += 1
                previous = index
            if not valid or cursor != len(logical):
                continue
            digest = hashlib.sha256(logical.encode('utf-8')).hexdigest()
            for left, right, separator, start, end in proposals:
                # Whitespace already painted belongs to the existing SPACE provider.
                if chars[left]['text'].isspace() or chars[right]['text'].isspace():
                    continue
                edges[left] = {'version': 1, 'provider': 'INLINE_SPAN_ACTUALTEXT',
                               'page': page.page_number, 'invocation_id': context['id'],
                               'logical_sha256': digest, 'logical_boundary_span': [start, end],
                               'previous_glyph_index': left, 'following_glyph_index': right,
                               'separator': separator, 'coverage': 'EXACT_ORIGINAL_GLYPHS',
                               'balanced_scope': True, 'mcid_is_identity': False}
                if 'resource_witness' in context:
                    edges[left]['resource_source'] = context['resource_witness']
        accounting['certified_edges'] = len(edges)
        return edges, accounting
    except Exception:
        capture.inspection_complete = False
        return {}, {'version': 1, 'provider': 'INLINE_SPAN_ACTUALTEXT',
                    'unsupported': True, 'certified_edges': 0, 'document_capture_snapshot': capture.snapshot()}
