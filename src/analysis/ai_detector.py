"""Hybrid AI-generated-text detector for interview answers.

LLMs are unreliable when simply asked "is this AI?". This module computes
objective stylometric signals locally, turns them into a calibrated
heuristic AI-likelihood, and exposes helpers to BLEND that with the model's
own judgement. The blend is far more consistent and reliable than either
signal alone.

Signals used (each a known discriminator between spontaneous human speech and
generated/templated text):
  * burstiness        — humans vary sentence length a lot; AI is uniform.
  * personal voice    — first-person pronouns + past tense ("I built", "we").
  * concreteness      — numbers, %/$, proper-noun-ish tokens, tool names.
  * hedging/disfluency— "kind of", "honestly", "um", self-correction = human.
  * buzzword density  — "leverage synergy stakeholder holistic" = AI/templated.
  * list-likeness     — evenly structured "Firstly,/Secondly,/Moreover" = AI.
  * lexical variety   — type/token ratio extremes hint at generation.
"""

import re
import math

_BUZZWORDS = {
    "leverage", "synergy", "synergies", "stakeholder", "stakeholders",
    "holistic", "robust", "scalable", "seamless", "cutting-edge",
    "best-in-class", "value-add", "value", "deliver", "deliverables",
    "facilitate", "utilize", "utilise", "optimize", "optimise", "streamline",
    "paradigm", "ecosystem", "empower", "actionable", "alignment",
    "proactive", "passionate", "dynamic", "innovative", "comprehensive",
    "furthermore", "moreover", "additionally", "overall", "in conclusion",
}
_HEDGES = {
    "honestly", "actually", "basically", "kind of", "kinda", "sort of",
    "i guess", "i think", "i mean", "you know", "like", "well", "um", "uh",
    "maybe", "probably", "to be honest", "i remember", "i'd say",
}
_PERSONAL = {"i", "i'm", "i've", "i'd", "i'll", "my", "me", "we", "we're",
             "our", "us", "myself"}
_LIST_MARKERS = ("firstly", "secondly", "thirdly", "first,", "second,",
                 "finally,", "in conclusion", "to summarize", "to summarise")


def _sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _tokens(text):
    return re.findall(r"[A-Za-z'’\-]+", text.lower())


def heuristic_ai_likelihood(text):
    """Return (ai_likelihood 0-100, signals dict) from local stylometry."""
    text = (text or "").strip()
    words = _tokens(text)
    n = len(words)

    if n < 8:
        return 50, {"note": "answer too short for reliable stylometric analysis"}

    sents = _sentences(text) or [text]
    lengths = [len(_tokens(s)) for s in sents if _tokens(s)] or [n]
    mean_len = sum(lengths) / len(lengths)
    var = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std = math.sqrt(var)
    burstiness = std / mean_len if mean_len else 0  # high = human

    wordset = set(words)
    ttr = len(wordset) / n  # type-token ratio

    personal = sum(1 for w in words if w in _PERSONAL) / n
    buzz = sum(1 for w in words if w in _BUZZWORDS) / n
    numbers = len(re.findall(r"\b\d[\d.,%$]*\b", text)) / n
    low = text.lower()
    hedges = sum(low.count(h) for h in _HEDGES)
    hedge_rate = hedges / max(1, len(sents))
    list_like = sum(1 for m in _LIST_MARKERS if m in low)
    past_tense = len(re.findall(r"\b\w+ed\b", low)) / n

    # positive => more AI-like
    score = 50.0
    if burstiness < 0.25:
        score += 18
    elif burstiness < 0.45:
        score += 8
    else:
        score -= 12  # human

    if personal < 0.02:
        score += 16
    elif personal > 0.06:
        score -= 16

    if numbers > 0.01:
        score -= 10
    else:
        score += 6

    if buzz > 0.05:
        score += 16
    elif buzz > 0.025:
        score += 8

    if hedge_rate >= 1.0:
        score -= 14
    elif hedge_rate >= 0.4:
        score -= 7

    # AI essay style.
    score += min(list_like, 3) * 6

    if past_tense > 0.06:
        score -= 6

    if ttr > 0.85 and mean_len > 18:
        score += 8

    score = max(0, min(100, round(score)))
    signals = {
        "burstiness": round(burstiness, 2),
        "personal_voice": round(personal, 3),
        "concreteness_numbers": round(numbers, 3),
        "buzzword_density": round(buzz, 3),
        "hedge_rate": round(hedge_rate, 2),
        "list_scaffolding": list_like,
        "type_token_ratio": round(ttr, 2),
    }
    return score, signals


def blend(llm_ai_likelihood, text, llm_weight=0.55):
    """Blend the LLM's AI-likelihood with the local heuristic.

    Returns (final_ai_likelihood 0-100, heuristic_signals). For very short
    answers the heuristic is unreliable, so the LLM is trusted more.
    """
    heur, signals = heuristic_ai_likelihood(text)
    words = _tokens(text)
    try:
        llm = max(0, min(100, float(llm_ai_likelihood)))

    except (TypeError, ValueError):
        llm = 50.0

    if len(words) < 12:
        # Not enough text for stylometry — lean on the model.
        final = round(0.8 * llm + 0.2 * heur)

    else:
        final = round(llm_weight * llm + (1 - llm_weight) * heur)

    return max(0, min(100, final)), signals
