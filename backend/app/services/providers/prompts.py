"""Prompt construction shared by OpenAI and Gemini translation providers."""
from __future__ import annotations

import json

from app.services.providers.base import TranslationRequest

LANGUAGE_NAMES = {"ar": "Arabic", "en": "English", "fr": "French", "ur": "Urdu", "id": "Indonesian",
                  "tr": "Turkish", "es": "Spanish", "de": "German", "ms": "Malay", "bn": "Bengali"}

SYSTEM_PROMPT = (
    "You are a professional translator of Islamic educational content for video subtitles and dubbing. "
    "Translate faithfully and clearly. Rules:\n"
    "- Never invent, add or remove religious meaning. Do not add honorifics that are not spoken.\n"
    "- Keep established Islamic terms consistent with the glossary when provided.\n"
    "- Output only the translation of the given segment, not of the surrounding context.\n"
    "- Do not include any Arabic script in the translation.\n"
    "- If the segment appears to quote the Quran, do NOT translate that part: replace it with "
    "[QURAN] and mention it in notes.\n"
    'Respond with a JSON object: {"translation": string, "notes": string|null}.'
)

_MODE_GUIDANCE = {
    "faithful": "Prioritise precise, complete meaning over brevity.",
    "timed": "Keep it concise so it can be spoken in about the same time as the original segment.",
    "simplified": "Use simple, accessible wording for a general audience while keeping the meaning exact.",
}


def build_user_prompt(req: TranslationRequest) -> str:
    target = LANGUAGE_NAMES.get(req.target_language, req.target_language)
    source = LANGUAGE_NAMES.get(req.source_language, req.source_language)
    parts = [f"Translate the segment from {source} to {target}.",
             _MODE_GUIDANCE.get(req.dubbing_mode, _MODE_GUIDANCE["timed"])]
    if req.duration_seconds:
        parts.append(f"The spoken segment lasts {req.duration_seconds:.1f} seconds.")
    if req.mode == "constrained" and req.reference_text:
        parts.append(
            "This segment quotes the following verified hadith. Your translation must stay consistent with it"
            + (" and with its published translation." if req.reference_translation else ".")
        )
        parts.append(f"Verified hadith (Arabic): {req.reference_text}")
        if req.reference_translation:
            parts.append(f"Published translation: {req.reference_translation}")
    elif req.mode == "unverified":
        parts.append("This segment may contain a religious quotation whose source could not be verified. "
                     "Translate literally and note any uncertainty.")
    if req.glossary:
        parts.append("Glossary: " + json.dumps(req.glossary, ensure_ascii=False))
    if req.context_before:
        parts.append(f"Previous segment (context only): {req.context_before}")
    if req.context_after:
        parts.append(f"Next segment (context only): {req.context_after}")
    parts.append(f"Segment to translate: {req.text}")
    return "\n".join(parts)


def parse_translation_json(raw: str) -> tuple[str, str | None]:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return raw, None
        data = json.loads(raw[start:end + 1])
    text = str(data.get("translation") or "").strip()
    notes = data.get("notes")
    return text, (str(notes).strip() if notes else None)
