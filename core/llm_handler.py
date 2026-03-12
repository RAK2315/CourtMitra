import os
import re
import time
import json
from typing import List, Dict

# ── Groq setup ────────────────────────────────────────────────────────────────
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]

# ── Gemini setup ──────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-1.5-flash"   # free tier: 15 rpm, 1M tokens/day


def _get_groq_client():
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set.")
    return Groq(api_key=api_key)


def _call_gemini(messages: list, max_tokens: int, temperature: float = 0.3) -> str:
    """Call Google Gemini as fallback."""
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config=genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
    )
    # Gemini doesn't use system role — prepend system content to first user message
    parts = []
    for m in messages:
        if m["role"] == "system":
            parts.insert(0, f"INSTRUCTIONS: {m['content']}\n\n")
        else:
            parts.append(m["content"])
    prompt = "\n".join(parts)
    response = model.generate_content(prompt)
    return response.text.strip()


def _clean_json(raw: str) -> str:
    """Aggressively extract JSON from model output."""
    # Remove markdown code fences
    raw = re.sub(r'```(?:json)?', '', raw).replace('```', '').strip()
    # Find first { and last } — extract just the JSON object
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        return raw[start:end+1]
    # Try array
    start = raw.find('[')
    end = raw.rfind(']')
    if start != -1 and end != -1 and end > start:
        return raw[start:end+1]
    return raw


def _call_llm(messages: list, max_tokens: int, temperature: float = 0.3) -> str:
    """
    Try Groq models first, then fall back to Gemini.
    Each Groq model has a separate rate limit quota.
    """
    from groq import RateLimitError

    last_error = None

    # Try all Groq models first
    client = _get_groq_client()
    for i, model in enumerate(GROQ_MODELS):
        if i > 0:
            time.sleep(5)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except RateLimitError as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue  # try next model on any error

    # All Groq models failed — try Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            time.sleep(3)
            return _call_gemini(messages, max_tokens, temperature)
        except Exception as e:
            last_error = e

    raise RuntimeError(
        "All AI models are currently rate limited. Please wait 60 seconds and try again."
    ) from last_error


# ── Public functions ──────────────────────────────────────────────────────────

def summarize_judgment(chunks: List[Dict], entities: Dict, language: str = "English") -> Dict:
    context = "\n\n".join([
        f"[{c['section']}]\n{c['content'][:600]}"
        for c in chunks[:5]
    ])
    lang_instruction = "Respond entirely in simple Hindi (Devanagari script)." if language == "Hindi" else ""

    prompt = f"""You are CourtMitra — explain this Indian court judgment to an ordinary Indian citizen with no legal background.
Tone: warm, clear, like a knowledgeable friend. NOT robotic. Use real names. Be specific.

STRICT RULES for plain_summary:
- Do NOT repeat the same fact twice
- Each sentence must add NEW information
- Sentence 1: Who are the parties and what was the core dispute
- Sentence 2: What the lower court / previous proceedings decided
- Sentence 3: What the Supreme/High Court found and why
- Sentence 4: Final outcome — who won, what was ordered
- Use actual names from the judgment, not "the appellant" or "the petitioner"

JUDGMENT EXCERPTS:
{context}

ENTITIES:
- Cases: {', '.join(entities.get('case_numbers', [])) or 'N/A'}
- Acts: {', '.join(entities.get('acts_cited', [])[:3]) or 'N/A'}
- Articles: {', '.join(entities.get('statutes', [])[:3]) or 'N/A'}

{lang_instruction}

YOU MUST respond ONLY with a valid JSON object. No explanation before or after. No markdown. Start with {{ and end with }}:
{{
  "case_type": "one of: Criminal / Civil / Constitutional / Family / Labour / Consumer / Property / Service",
  "plain_summary": "exactly 4 sentences, each adding new info, no repetition, use real names",
  "key_issues": ["specific issue 1 in plain words", "specific issue 2", "specific issue 3"],
  "what_court_decided": "1 sentence — exactly what was ordered, any specific relief granted",
  "next_steps": ["step 1 for the person affected", "step 2", "step 3"],
  "important_warning": "one friendly reminder to consult a lawyer"
}}"""

    messages = [
        {"role": "system", "content": "You are a JSON API. You output ONLY valid JSON with no explanation, no markdown, no code fences. Your entire response must be parseable by json.loads()."},
        {"role": "user", "content": prompt}
    ]
    raw = _call_llm(messages, max_tokens=900)
    cleaned = _clean_json(raw)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Second attempt: fix trailing commas
        try:
            fixed = re.sub(r',\s*([}\]])', r'\1', cleaned)
            return json.loads(fixed)
        except Exception:
            pass

    # Third attempt: try to extract fields manually from raw text
    # This handles cases where model returns JSON with unescaped quotes inside strings
    try:
        # Replace newlines inside strings before parsing
        cleaned2 = re.sub(r'\n', ' ', cleaned)
        cleaned2 = re.sub(r',\s*([}\]])', r'\1', cleaned2)
        return json.loads(cleaned2)
    except Exception:
        pass

    # Last resort: return raw text as plain summary so user sees something useful
    # Strip any JSON-like wrapper if present
    summary_text = raw
    for key in ['"plain_summary":', 'plain_summary:']:
        if key in raw:
            try:
                start = raw.index(key) + len(key)
                chunk = raw[start:].strip().lstrip('"').lstrip("'")
                end = chunk.index('"')
                summary_text = chunk[:end]
                break
            except Exception:
                pass

    return {
        "case_type": "Unknown",
        "plain_summary": summary_text[:800] if len(summary_text) > 10 else "Could not generate summary — please try again.",
        "key_issues": [],
        "what_court_decided": "",
        "next_steps": [],
        "important_warning": "Please consult a qualified lawyer for advice specific to your situation.",
    }


def build_reasoning_chain(chunks: List[Dict]) -> List[Dict]:
    context = "\n\n".join([c["content"][:500] for c in chunks[:4]])

    prompt = f"""Analyze this Indian court judgment and extract the judge's step-by-step reasoning and jurisdiction path.

JUDGMENT TEXT:
{context}

YOU MUST respond ONLY with a valid JSON array. No explanation before or after. Start with [ and end with ]:
[
  {{"step": 1, "label": "3-5 word title", "detail": "one plain English sentence", "type": "jurisdiction"}},
  {{"step": 2, "label": "3-5 word title", "detail": "one plain English sentence", "type": "fact"}},
  {{"step": 3, "label": "3-5 word title", "detail": "one plain English sentence", "type": "issue"}},
  {{"step": 4, "label": "3-5 word title", "detail": "one plain English sentence", "type": "argument"}},
  {{"step": 5, "label": "3-5 word title", "detail": "one plain English sentence", "type": "decision"}},
  {{"step": 6, "label": "Further Appeal", "detail": "If aggrieved, the party may approach [court] under [Article/provision].", "type": "appeal"}}
]
Types: jurisdiction, fact, issue, argument, law, decision, appeal only. 5-7 steps total."""

    messages = [
        {"role": "system", "content": "You are a JSON API. Output ONLY a valid JSON array. No explanation, no markdown, no code fences."},
        {"role": "user", "content": prompt}
    ]
    raw = _call_llm(messages, max_tokens=800, temperature=0.2)
    cleaned = _clean_json(raw)

    try:
        return json.loads(cleaned)
    except Exception:
        return [
            {"step": 1, "label": "Jurisdiction", "detail": "Court established jurisdiction over the matter.", "type": "jurisdiction"},
            {"step": 2, "label": "Facts Presented", "detail": "Parties presented their respective facts.", "type": "fact"},
            {"step": 3, "label": "Legal Issues", "detail": "Court identified the core legal questions.", "type": "issue"},
            {"step": 4, "label": "Law Applied", "detail": "Relevant statutes and precedents considered.", "type": "law"},
            {"step": 5, "label": "Final Order", "detail": "Court delivered its judgment.", "type": "decision"},
        ]


def answer_question(question: str, chunks: List[Dict], full_text: str = "", language: str = "English") -> str:
    chunk_context = "\n\n".join([c["content"][:700] for c in chunks[:6]])
    preamble = full_text[:1500] if full_text else ""
    context = f"HEADNOTE/OPENING:\n{preamble}\n\nRETRIEVED SECTIONS:\n{chunk_context}" if preamble else chunk_context
    lang_instruction = "Respond in simple Hindi." if language == "Hindi" else "Respond in simple English."

    prompt = f"""You are CourtMitra. Answer the question using ONLY the judgment text below.

IMPORTANT:
- Search carefully for specific numbers, pay scales (e.g. Rs. 210-270), amounts, dates, names
- If figures are present, quote them exactly
- Pay scales appear as "Rs. XXX-YYY" — look carefully
- If genuinely not present, say "This specific detail is not mentioned in the uploaded judgment"

JUDGMENT TEXT:
{context}

QUESTION: {question}

{lang_instruction}
Answer in 2-5 sentences. Quote specific figures if present. No legal advice."""

    return _call_llm([{"role": "user", "content": prompt}], max_tokens=450)


def extract_legal_terms(text: str) -> Dict:
    """Extract hard legal terms from judgment and explain in plain English."""
    sample = text[:3000]

    prompt = f"""You are CourtMitra. Extract up to 10 difficult legal terms or Latin phrases from this Indian court judgment and explain each in plain simple English (1 sentence each). Focus on terms a non-lawyer would not understand.

JUDGMENT TEXT:
{sample}

YOU MUST respond ONLY with valid JSON. No text before or after. Start with {{ end with }}:
{{
  "terms": [
    {{"term": "Ex parte", "explanation": "A decision made without hearing one side of the case."}},
    {{"term": "Writ of Mandamus", "explanation": "A court order telling a government body to do something it is legally required to do."}}
  ]
}}

Only include terms actually present in the text. Return empty array if no hard terms found."""

    raw = _call_llm([{"role": "user", "content": prompt}], max_tokens=600, temperature=0.2)
    cleaned = _clean_json(raw)
    try:
        return json.loads(cleaned)
    except Exception:
        return {"terms": []}