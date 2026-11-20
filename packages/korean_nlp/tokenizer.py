"""Korean morphological tokenizer wrapper with deterministic regex fallback.

Uses `kiwipiepy` when available (lazy singleton per process) and falls back cleanly
to a zero-dependency deterministic eojeol/particle/ending splitter so CI and minimal
environments execute without runtime errors.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Token:
    form: str
    tag: str
    start: int
    end: int


# Common Korean legal compound nouns registered when Kiwi is active
LEGAL_USER_WORDS: Tuple[Tuple[str, str], ...] = (
    ("전원합의체", "NNG"),
    ("위법성조각", "NNG"),
    ("소멸시효", "NNG"),
    ("제소기간", "NNG"),
    ("원고적격", "NNG"),
    ("전심절차", "NNG"),
    ("판시사항", "NNG"),
    ("판결요지", "NNG"),
    ("준비서면", "NNG"),
    ("청구취지", "NNG"),
    ("청구원인", "NNG"),
    ("징벌적손해배상", "NNG"),
    ("부당이득", "NNG"),
    ("채무불이행", "NNG"),
    ("불법행위", "NNG"),
    ("권리남용", "NNG"),
    ("신의성실", "NNG"),
    ("기판력", "NNG"),
    ("항소이유서", "NNG"),
    ("상고이유서", "NNG"),
)

_PARTICLE_SUFFIX_RE = re.compile(
    r"^(?P<stem>.+?)(?P<josa>에서부터|으로부터|로부터|에게는|에서는|으로는|까지는|부터는|께서|에게|에서|으로|까지|부터|에도|에도|은|는|이|가|을|를|의|와|과|도|만|로)$"
)
_EOJEOL_RE = re.compile(r"\S+")


class LegalTokenizer:
    """Unified Korean tokenizer interface supporting Kiwi and deterministic regex fallback."""

    def __init__(self, *, use_kiwi: bool = True) -> None:
        self._kiwi = None
        self.backend = "regex_fallback"
        if use_kiwi:
            try:
                from kiwipiepy import Kiwi  # type: ignore

                kiwi = Kiwi()
                for word, tag in LEGAL_USER_WORDS:
                    try:
                        kiwi.add_user_word(word, tag, 0.0)
                    except Exception:
                        pass
                self._kiwi = kiwi
                self.backend = "kiwi"
            except Exception:
                self._kiwi = None
                self.backend = "regex_fallback"

    def tokenize(self, text: str) -> List[Token]:
        raw = str(text or "")
        if not raw.strip():
            return []
        if self._kiwi is not None:
            return [
                Token(form=t.form, tag=t.tag, start=t.start, end=t.start + t.len)
                for t in self._kiwi.tokenize(raw)
            ]
        return self._fallback_tokenize(raw)

    def content_lemmas(self, text: str) -> List[str]:
        """Return normalized content terms (nouns, predicates, numbers) for lexical retrieval."""
        tokens = self.tokenize(text)
        out: List[str] = []
        for tok in tokens:
            if tok.tag.startswith(("N", "V", "SL", "SN")) and len(tok.form) >= 1:
                out.append(tok.form)
        return out

    @staticmethod
    def _fallback_tokenize(text: str) -> List[Token]:
        tokens: List[Token] = []
        for match in _EOJEOL_RE.finditer(text):
            word = match.group(0)
            base_start = match.start()
            # Strip trailing punctuation cleanly
            stripped = word.rstrip(".,;:!?\"'()[]{}<>「」『』")
            if not stripped:
                tokens.append(Token(form=word, tag="SF", start=base_start, end=match.end()))
                continue
            josa_m = _PARTICLE_SUFFIX_RE.match(stripped) if len(stripped) >= 2 else None
            if josa_m and len(josa_m.group("stem")) >= 1:
                stem = josa_m.group("stem")
                josa = josa_m.group("josa")
                tokens.append(Token(form=stem, tag="NNG", start=base_start, end=base_start + len(stem)))
                tokens.append(
                    Token(
                        form=josa,
                        tag="JKS" if josa in ("이", "가", "께서") else "JX",
                        start=base_start + len(stem),
                        end=base_start + len(stripped),
                    )
                )
            else:
                tag = "SN" if stripped.isdigit() else "NNG"
                tokens.append(Token(form=stripped, tag=tag, start=base_start, end=base_start + len(stripped)))
        return tokens


@lru_cache(maxsize=2)
def get_tokenizer(*, use_kiwi: bool = True) -> LegalTokenizer:
    return LegalTokenizer(use_kiwi=use_kiwi)
