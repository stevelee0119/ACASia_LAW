"""Document-local, bounded PAGE and selected Form replacement capture.

Inspection coverage is a lifecycle result, not an optimistic default. Source
certification and inspection stay independent; complete Form coverage is
outside this provider's scope. Cached values never establish entity identity.
"""
from pdfminer.utils import PDFDocEncoding


class NamedActualTextCapture:
    MAX_REFERENCES=512
    MAX_REFERENCE_CACHE=64
    MAX_CONTEXTS=128
    MAX_DECODED_ENTRIES=64
    MAX_DECODED_CHARS=64000
    MAX_RAW_CACHE_BYTES=128000
    MAX_INSPECTION_STRINGS=50
    MAX_INSPECTION_CHARS=100000

    def __init__(self):
        self.references={};self.decoded={};self.inspection=[];self.inspected=set()
        self.reference_visits=self.reference_hits=self.reference_fetches=self.reference_requests=0
        self.contexts=self.context_attempts=self.decode_calls=self.decode_hits=0
        self.decoded_chars=self.raw_cache_bytes=self.retained_chars=0
        self.exceeded=False;self._inspection_ok=True
        self.inspection_attempted_pages=self.inspection_completed_pages=0
        self.inspection_failed_pages=self.inspection_active_pages=0
        self.inspection_unavailable_pages=self.named_selection_requests=0
        self.availability_queries=self.resolution_failures=0
        self.unsupported_actualtext_values=self.actualtext_absent=0
        self.selected_property_missing=self.selected_property_invalid=0

    @property
    def inspection_complete(self):
        return bool(self._inspection_ok and self.inspection_completed_pages>0
                    and self.inspection_attempted_pages==self.inspection_completed_pages
                    and not self.inspection_active_pages and not self.inspection_unavailable_pages)

    @inspection_complete.setter
    def inspection_complete(self,value):
        # Failure is sticky; only a finished lifecycle can derive success.
        if not value: self._inspection_ok=False

    def begin_page(self):
        self.inspection_attempted_pages+=1;self.inspection_active_pages+=1

    def end_page(self,completed):
        self.inspection_active_pages-=1
        if completed:self.inspection_completed_pages+=1
        else:self.inspection_failed_pages+=1;self._inspection_ok=False

    def inspection_state(self):
        if self.inspection_active_pages:return 'IN_PROGRESS'
        if not self.inspection_attempted_pages:
            return 'UNAVAILABLE_UNINSPECTED' if self.inspection_unavailable_pages else 'NOT_ATTEMPTED'
        if not self.inspection_complete:return 'INSPECTED_INCOMPLETE'
        if not self.decoded:return 'INSPECTED_NO_SELECTED_PAGE_NAMED_SOURCE'
        return 'INSPECTED_SUPPORTED'

    def fail(self):
        self.exceeded=True;self.inspection_complete=False

    def reference(self,ref,scope):
        self.reference_requests+=1
        if self.reference_visits==self.MAX_REFERENCES:
            self.fail();return None
        self.reference_visits+=1
        key=(scope,id(ref.doc),ref.objid)
        if key in self.references:
            self.reference_hits+=1;return self.references[key]
        if len(self.references)==self.MAX_REFERENCE_CACHE:
            self.fail();return None
        self.reference_fetches+=1
        try: value=ref.resolve()
        except Exception: value=None
        if value is None:
            self.resolution_failures+=1;self.inspection_complete=False
        self.references[key]=value
        return value

    def entry(self,raw):
        if not isinstance(raw,bytes):
            self.unsupported_actualtext_values+=1;self.inspection_complete=False;return None
        key=id(raw)
        if key in self.decoded:
            self.decode_hits+=1;return self.decoded[key][1]
        units=(len(raw)-2)//2 if raw.startswith(b'\xfe\xff') else len(raw)
        if (len(self.decoded)==self.MAX_DECODED_ENTRIES or units+self.decoded_chars>self.MAX_DECODED_CHARS
                or len(raw)+self.raw_cache_bytes>self.MAX_RAW_CACHE_BYTES):
            self.fail();return None
        self.decode_calls+=1
        try:
            text=raw[2:].decode('utf-16-be') if raw.startswith(b'\xfe\xff') else ''.join(PDFDocEncoding[c] for c in raw)
        except (UnicodeError,IndexError):
            text=None;self.inspection_complete=False
        strict=text if text is not None and not any(ord(c)<32 or 0xD800<=ord(c)<=0xDFFF or c in '\u200b\u200c\u200d\u2060\ufeff' for c in text) else None
        value=(text,strict)
        self.decoded[key]=(raw,value) # retain identity; no copied raw byte key
        self.raw_cache_bytes+=len(raw);self.decoded_chars+=len(text) if text else 0
        return value

    def inspect(self,raw):
        value=self.entry(raw)
        if value is None or value[0] is None: return
        text=value[0]
        if id(text) in self.inspected: return
        self.inspected.add(id(text))
        if len(text.strip())<8 and not any(c in text for c in '\u200b\u200c\u200d\ufeff'): return
        if len(self.inspection)==self.MAX_INSPECTION_STRINGS or self.retained_chars==self.MAX_INSPECTION_CHARS:
            self.inspection_complete=False;return
        end=min(len(text),2000,self.MAX_INSPECTION_CHARS-self.retained_chars)
        self.inspection.append(text[:end]);self.retained_chars+=end
        if end<len(text): self.inspection_complete=False

    def strict(self,raw):
        # Certification rejection is separate from inspection of the resolved
        # indirect string. Do not report it as a missed inspection source.
        if not isinstance(raw,bytes): return None
        value=self.entry(raw)
        return value[1] if value else None

    def context(self):
        self.context_attempts+=1
        if self.contexts==self.MAX_CONTEXTS:
            self.fail();return False
        self.contexts+=1;return True

    def snapshot(self):
        return dict(reference_requests=self.reference_requests,reference_visits=self.reference_visits,reference_fetches=self.reference_fetches,
                    reference_cache_hits=self.reference_hits,reference_cache_entries=len(self.references),
                    named_context_attempts=self.context_attempts,named_contexts=self.contexts,decode_calls=self.decode_calls,decode_cache_hits=self.decode_hits,
                    distinct_decoded_entries=len(self.decoded),decoded_chars=self.decoded_chars,
                    raw_cache_bytes=self.raw_cache_bytes,retained_inspection_strings=len(self.inspection),
                    retained_inspection_chars=self.retained_chars,budget_exceeded=self.exceeded,
                    inspection_complete=self.inspection_complete,availability_queries=self.availability_queries,
                    inspection_state=self.inspection_state(),
                    inspection_attempted_pages=self.inspection_attempted_pages,
                    inspection_completed_pages=self.inspection_completed_pages,
                    inspection_failed_pages=self.inspection_failed_pages,
                    inspection_active_pages=self.inspection_active_pages,
                    inspection_unavailable_pages=self.inspection_unavailable_pages,
                    named_selection_requests=self.named_selection_requests,
                    resolution_failures=self.resolution_failures,
                    unsupported_actualtext_values=self.unsupported_actualtext_values,
                    actualtext_absent=self.actualtext_absent,
                    selected_property_missing=self.selected_property_missing,
                    selected_property_invalid=self.selected_property_invalid,
                    inspection_scope='SELECTED_PAGE_AND_FORM_NAMED_PROPERTIES', version=1)
