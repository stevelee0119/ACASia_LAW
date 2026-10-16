"""Design-only selected Form inspection; no production imports this adapter."""
from pdfminer.pdftypes import PDFObjRef
from pdfminer.psparser import PSLiteral, literal_name

from packages.document_engine import actualtext_boundaries as provider
from test_tk44_actualtext_provider import _parse


OriginalInterpreter = provider._Interpreter
original_available = provider._named_available


def resolve(value, capture, scope):
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


class FormInspectionInterpreter(OriginalInterpreter):
    def do_BDC(self, tag, props):
        capture = self.device.named_capture
        if capture is not None and self.device.form_depth and isinstance(props, PSLiteral):
            # Inspection of a selected occurrence cannot certify all native
            # Form coverage or its visibility/semantic boundary.
            capture.inspection_complete = False
            if capture.context():
                scope = (self.device.pageno, id(self.resources), "FORM_INSPECTION_ONLY")
                resources = resolve(self.resources, capture, scope)
                properties = resolve(resources.get("Properties"), capture, scope) if isinstance(resources, dict) else None
                selected = resolve(properties.get(literal_name(props)), capture, scope) if isinstance(properties, dict) else None
                if isinstance(selected, dict):
                    if "ActualText" in selected:
                        capture.inspect(resolve(selected["ActualText"], capture, scope))
                    else:
                        capture.actualtext_absent += 1
                elif isinstance(properties, dict) and literal_name(props) not in properties:
                    capture.selected_property_missing += 1
                else:
                    capture.selected_property_invalid += 1
        # Keep the original literal operand. Never turn the Form's selected
        # dictionary into the PAGE provider's boundary-certification witness.
        return super().do_BDC(tag, props)


def candidate_available(page, capture):
    if original_available(page, capture):
        return True
    resources = resolve(page.page_obj.resources, capture, (page.page_number, "FORM_AVAILABILITY"))
    xobjects = resolve(resources.get("XObject"), capture, (page.page_number, "FORM_AVAILABILITY")) if isinstance(resources, dict) else None
    return isinstance(xobjects, dict) and bool(xobjects)


def parse_candidate(path, monkeypatch):
    with monkeypatch.context() as scoped:
        scoped.setattr(provider, "_Interpreter", FormInspectionInterpreter)
        scoped.setattr(provider, "_named_available", candidate_available)
        doc = _parse(path)
    # This is candidate output, not a claim about the current product scope.
    doc.structure["named_actualtext_inspection"]["inspection_scope"] = "SELECTED_PAGE_AND_FORM_CANDIDATE"
    return doc
