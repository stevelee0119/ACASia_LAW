"""Print aggregate PDF boundary observations without source text or identifiers."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.document_engine import parse_document
from scripts.path_guard import INPUT_ROOTS, contained_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    signals, reasons, modes = Counter(), Counter(), Counter()
    for path in args.paths:
        source = contained_path(path, *INPUT_ROOTS)  # TK-175: 저장소·임시 폴더·사용자 홈 안의 문서만
        doc = parse_document(str(source), document_id="boundary-instrumentation",
                             filename=source.name, mime_type="application/pdf",
                             sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        for page in doc.pages:
            for block in page.blocks:
                observations = block.attributes.get("boundary_observations", [])
                if observations:
                    modes[block.attributes.get("char_wrap_state", "UNKNOWN")] += 1
                for observation in observations:
                    signals[observation["boundary_signal"]] += 1
                    reasons[observation["reason"]] += 1
    total = sum(signals.values())
    print(json.dumps({"documents": len(args.paths), "boundaries": total,
                      "signals": dict(signals), "signal_ratios": {
                          key: value / total for key, value in signals.items()
                      }, "reasons": dict(reasons), "char_wrap_states": dict(modes)}, indent=2))


if __name__ == "__main__":
    main()
