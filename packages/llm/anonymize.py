"""Anonymisierung vor LLM-Calls.

Niemals Klartext-Patientendaten an OpenRouter senden. Diese Stub-Implementierung
ist absichtlich konservativ — sie redacted alles, was wie ein Name, Geburtsdatum,
Adresse oder Telefonnummer aussieht. Echte Implementierung in Phase 2 ergänzt
NER mit deutschem spaCy-Modell.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PHONE_RE = re.compile(r"(?<!\d)(\+?\d{2,4}[\s/-]?)?\d{3,5}[\s/-]?\d{3,8}(?!\d)")
DATE_RE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
ZIP_CITY_RE = re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+\b")
# Sehr defensives Namens-Pattern: Großbuchstabe gefolgt von 2+ Kleinbuchstaben,
# zweimal hintereinander mit Leerzeichen → vermutlich Name.
NAME_RE = re.compile(r"\b([A-ZÄÖÜ][a-zäöüß]{2,})\s([A-ZÄÖÜ][a-zäöüß]{2,})\b")


@dataclass
class Anonymized:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)

    def reveal(self, text: str) -> str:
        """Tauscht Tokens nach LLM-Antwort zurück."""
        for token, original in self.mapping.items():
            text = text.replace(token, original)
        return text


def anonymize(text: str) -> Anonymized:
    mapping: dict[str, str] = {}
    counter = {"NAME": 0, "PHONE": 0, "DATE": 0, "ADDR": 0}

    def token(kind: str) -> str:
        counter[kind] += 1
        return f"[[{kind}_{counter[kind]}]]"

    def replace(pattern: re.Pattern[str], kind: str, current: str) -> str:
        def sub(m: re.Match[str]) -> str:
            t = token(kind)
            mapping[t] = m.group(0)
            return t

        return pattern.sub(sub, current)

    out = text
    out = replace(NAME_RE, "NAME", out)
    out = replace(PHONE_RE, "PHONE", out)
    out = replace(DATE_RE, "DATE", out)
    out = replace(ZIP_CITY_RE, "ADDR", out)
    return Anonymized(text=out, mapping=mapping)
