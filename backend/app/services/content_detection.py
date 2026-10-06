"""Classify a transcript segment as quran / hadith / general / uncertain.

A source reference is attached ONLY when a match reaches its threshold
(Quran 0.92, Hadith 0.85). Lower scores never produce a reference or a source match.

1. Quran match >= 0.92 (whole segment is the ayah text)           -> quran
2. Hadith match >= 0.85                                            -> hadith
3. Both 1 and 2 -> quran if its score is >= the hadith score, else uncertain (conflict)
4. Quran/Hadith text >= threshold embedded in longer speech, when the quote is
   substantial (>= MIN_EMBEDDED_QUOTE_CHARS), introduced ("قال الله تعالى"), or a
   verbatim ayah of >= 3 words; everyday formulas ("الحمد لله رب العالمين") and
   2-word coincidences ("ملك الناس") are ignored                     -> uncertain (mixed)
5. Quran score in [0.85, 0.92), whole segment                      -> uncertain, Quran-protected,
                                                                      no reference
6. Explicit quotation introducer without a source                   -> uncertain, no reference
7. Everything else (including 0.70-0.85 near-misses)               -> general
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.config import Settings
from app.models.enums import ContentType, VerificationStatus
from app.repositories.local_sources import LocalSourcesRepository, SourceCandidate
from app.services.arabic import match_key, normalize_arabic

_QUOTE_INTRODUCERS_QURAN = tuple(normalize_arabic(p) for p in (
    "قال الله تعالى", "قال تعالى", "يقول الله تعالى", "يقول الله عز وجل", "قال الله عز وجل", "قوله تعالى",
))
_QUOTE_INTRODUCERS_HADITH = tuple(normalize_arabic(p) for p in (
    "قال رسول الله", "قال النبي", "يقول النبي", "يقول رسول الله", "سمعت رسول الله", "عن النبي",
))


# Ayahs that double as everyday Islamic expressions. Inside longer speech they are a formula,
# not a Quran quotation; on their own the segment is still matched as Quran.
_EVERYDAY_FORMULAS = frozenset(match_key(p) for p in (
    "الحمد لله رب العالمين", "بسم الله الرحمن الرحيم", "الرحمن الرحيم", "انا لله وانا اليه راجعون",
    "حسبنا الله ونعم الوكيل", "ربنا اتنا في الدنيا حسنه وفي الاخره حسنه وقنا عذاب النار",
    "والعاقبه للمتقين", "سبحان الله", "ان الله غفور رحيم", "ان الله على كل شيء قدير",
))
MIN_VERBATIM_QUOTE_WORDS = 3


def _is_verbatim_quote(segment_key: str, source_key: str) -> bool:
    """The whole source appears word-for-word in the segment (e.g. "قل هو الله أحد" inside speech)."""
    return len(source_key.split()) >= MIN_VERBATIM_QUOTE_WORDS and f" {source_key} " in f" {segment_key} "


@dataclass
class Detection:
    content_type: ContentType
    verification_status: VerificationStatus
    best: SourceCandidate | None = None
    quran_candidates: list[SourceCandidate] = field(default_factory=list)
    hadith_candidates: list[SourceCandidate] = field(default_factory=list)
    reason: str = ""
    quran_suspected: bool = False   # True => AI translation is forbidden for this segment

    @property
    def all_candidates(self) -> list[SourceCandidate]:
        return sorted(self.quran_candidates + self.hadith_candidates, key=lambda c: c.score, reverse=True)


class ContentDetector:
    def __init__(self, sources: LocalSourcesRepository, settings: Settings) -> None:
        self.sources = sources
        self.settings = settings

    def detect(self, text: str) -> Detection:
        s = self.settings
        quran = self.sources.search_quran(text, limit=3)
        hadith = self.sources.search_hadith(text, limit=3)
        q = quran[0] if quran else None
        h = hadith[0] if hadith else None
        norm = normalize_arabic(text)
        quran_intro = any(p in norm for p in _QUOTE_INTRODUCERS_QURAN)
        hadith_intro = any(p in norm for p in _QUOTE_INTRODUCERS_HADITH)

        q_hit = bool(q and q.score >= s.quran_match_threshold and not q.is_mixed)
        h_hit = bool(h and h.score >= s.hadith_match_threshold and not h.is_mixed)
        seg_key = match_key(text)
        q_mixed = bool(q and q.is_mixed and q.score >= s.quran_match_threshold
                       and q.entry.key not in _EVERYDAY_FORMULAS
                       and (len(q.entry.key) >= s.min_embedded_quote_chars or quran_intro
                            or _is_verbatim_quote(seg_key, q.entry.key)))
        h_mixed = bool(h and h.is_mixed and h.score >= s.hadith_match_threshold
                       and (len(h.entry.key) >= s.min_embedded_quote_chars or hadith_intro))
        q_suspect = bool(q and not q.is_mixed and s.quran_suspect_threshold <= q.score < s.quran_match_threshold)
        common = dict(quran_candidates=quran, hadith_candidates=hadith)

        if q_hit and h_hit:
            # Hadiths often quote ayahs (e.g. the basmala). Classifying as Quran is the most protective
            # outcome (no AI translation, no TTS); only a stronger hadith match leaves it unsettled.
            if q.score >= h.score:  # type: ignore[union-attr]
                return Detection(ContentType.QURAN, VerificationStatus.VERIFIED, best=q,
                                 reason="quran_match_over_hadith", quran_suspected=True, **common)
            return Detection(ContentType.UNCERTAIN, VerificationStatus.CONFLICT, best=h,
                             reason="quran_and_hadith_match", quran_suspected=True, **common)
        if q_hit:
            return Detection(ContentType.QURAN, VerificationStatus.VERIFIED, best=q,
                             reason="quran_match", quran_suspected=True, **common)
        if h_hit:
            # A hadith that also closely resembles an ayah keeps Quran protection on.
            return Detection(ContentType.HADITH, VerificationStatus.VERIFIED, best=h,
                             reason="hadith_match", quran_suspected=q_suspect or q_mixed, **common)
        if q_mixed:
            return Detection(ContentType.UNCERTAIN, VerificationStatus.CANDIDATE, best=q,
                             reason="quran_quote_mixed_with_speech", quran_suspected=True, **common)
        if h_mixed:
            return Detection(ContentType.UNCERTAIN, VerificationStatus.CANDIDATE, best=h,
                             reason="hadith_quote_mixed_with_speech", quran_suspected=False, **common)
        if q_suspect:
            # Possibly a misheard recitation: keep it away from AI translation and TTS,
            # but do not claim any Quran reference below the threshold.
            return Detection(ContentType.UNCERTAIN, VerificationStatus.NOT_FOUND,
                             reason="possible_quran_below_threshold", quran_suspected=True, **common)
        if quran_intro or hadith_intro:
            return Detection(ContentType.UNCERTAIN, VerificationStatus.NOT_FOUND,
                             reason="quotation_without_source", quran_suspected=quran_intro, **common)
        return Detection(ContentType.GENERAL, VerificationStatus.NOT_FOUND, reason="general_speech", **common)
