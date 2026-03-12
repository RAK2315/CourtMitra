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

    prompt = f"""You are CourtMitra. Explain this Indian court judgment to an ordinary citizen in plain language.

RULES:
- Use real names, not "the petitioner" or "the appellant"
- 4 sentences in plain_summary, each adding NEW info (no repetition)
- Sentence 1: parties + dispute, Sentence 2: lower court/background, Sentence 3: what this court found, Sentence 4: final outcome

JUDGMENT:
{context}

ENTITIES: Cases={', '.join(entities.get('case_numbers', [])) or 'N/A'} | Acts={', '.join(entities.get('acts_cited', [])[:2]) or 'N/A'}

{lang_instruction}

JSON only (no markdown, start with {{):
{{"case_type":"Criminal/Civil/Constitutional/Family/Labour/Consumer/Property/Service","plain_summary":"4 sentences","key_issues":["issue1","issue2","issue3"],"what_court_decided":"1 sentence with specific relief","next_steps":["step1","step2","step3"],"important_warning":"consult a lawyer"}}"""

    messages = [
        {"role": "system", "content": "You are a JSON API. You output ONLY valid JSON with no explanation, no markdown, no code fences. Your entire response must be parseable by json.loads()."},
        {"role": "user", "content": prompt}
    ]
    raw = _call_llm(messages, max_tokens=1000)
    cleaned = _clean_json(raw)

    def _try_parse(s):
        """Try multiple JSON repair strategies."""
        for attempt in [
            s,
            re.sub(r',\s*([}\]])', r'\1', s),                    # trailing commas
            re.sub(r'\n', ' ', s),                                 # newlines in strings
            re.sub(r',\s*([}\]])', r'\1', re.sub(r'\n', ' ', s)), # both
        ]:
            try:
                return json.loads(attempt)
            except Exception:
                continue
        return None

    result = _try_parse(cleaned)
    if result and isinstance(result, dict):
        # Fill any missing keys with defaults
        result.setdefault("case_type", "Unknown")
        result.setdefault("plain_summary", "")
        result.setdefault("key_issues", [])
        result.setdefault("what_court_decided", "")
        result.setdefault("next_steps", [])
        result.setdefault("important_warning", "Please consult a qualified lawyer.")
        return result

    # If JSON is truncated (model hit token limit), try to recover by closing it
    truncated = cleaned.rstrip().rstrip(',')
    # Count open brackets to close
    opens = truncated.count('{') - truncated.count('}')
    arr_opens = truncated.count('[') - truncated.count(']')
    if opens > 0 or arr_opens > 0:
        recovery = truncated
        recovery += ']' * arr_opens + '}' * opens
        result = _try_parse(recovery)
        if result and isinstance(result, dict):
            result.setdefault("case_type", "Unknown")
            result.setdefault("plain_summary", "")
            result.setdefault("key_issues", [])
            result.setdefault("what_court_decided", "")
            result.setdefault("next_steps", [])
            result.setdefault("important_warning", "Please consult a qualified lawyer.")
            return result

    # Absolute last resort — extract plain_summary from raw text at minimum
    summary_text = ""
    m = re.search(r'"plain_summary"\s*:\s*"(.*?)(?<!\\)"', cleaned, re.DOTALL)
    if m:
        summary_text = m.group(1).replace('\\"', '"')

    case_type = "Unknown"
    m2 = re.search(r'"case_type"\s*:\s*"([^"]+)"', cleaned)
    if m2:
        case_type = m2.group(1)

    return {
        "case_type": case_type,
        "plain_summary": summary_text or raw[:600],
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

def build_reasoning_chain(chunks: List[Dict]) -> List[Dict]:
    context = "\n\n".join([c["content"][:400] for c in chunks[:3]])

    prompt = f"""Analyze this Indian court judgment. Return 6 reasoning steps as a JSON array.

JUDGMENT TEXT:
{context}

Each step needs: step (number), label (3-5 words), detail (one specific sentence using real names/facts from THIS case — not generic), type (one of: jurisdiction/fact/issue/law/decision/appeal).

Step 1=jurisdiction (which court, which Article), Step 2=fact, Step 3=issue, Step 4=law, Step 5=decision, Step 6=appeal avenue.

BAD detail: "Court established jurisdiction." GOOD detail: "Randhir Singh filed Writ Petition No.4676 of 1978 directly in the Supreme Court under Article 32."

JSON array only, no other text:"""

    messages = [
        {"role": "system", "content": "You are a JSON API. Output ONLY a valid JSON array. No explanation, no markdown, no code fences. Use only straight double quotes. Do not use quotes inside string values."},
        {"role": "user", "content": prompt}
    ]
    raw = _call_llm(messages, max_tokens=1000, temperature=0.2)
    cleaned = _clean_json(raw)

    def _try_parse_list(s):
        for attempt in [
            s,
            re.sub(r',\s*([}\]])', r'\1', s),
            re.sub(r'\n', ' ', s),
            re.sub(r',\s*([}\]])', r'\1', re.sub(r'\n', ' ', s)),
        ]:
            try:
                result = json.loads(attempt)
                if isinstance(result, list) and len(result) > 0:
                    return result
            except Exception:
                continue
        return None

    result = _try_parse_list(cleaned)
    if result:
        return result

    # Try truncation recovery — close any open brackets
    truncated = cleaned.rstrip().rstrip(',')
    # Remove last incomplete object if it exists
    last_complete = truncated.rfind('}')
    if last_complete != -1:
        truncated = truncated[:last_complete+1]
        opens = truncated.count('[') - truncated.count(']')
        recovery = truncated + ']' * max(opens, 1)
        result = _try_parse_list(recovery)
        if result:
            return result

    # Final fallback
    return [
        {"step": 1, "label": "Parse Error", "detail": "Reasoning chain could not be loaded — try clicking 'Reasoning Chain' tab again.", "type": "jurisdiction"},
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
    """Extract genuinely hard legal terms from judgment — skip well-known ones."""
    sample = text[:3000]

    prompt = f"""You are CourtMitra. Extract up to 8 genuinely obscure legal terms, Latin phrases, or case-specific jargon from this Indian court judgment. Explain each in one plain simple English sentence.

SKIP these common ones — they are already in our reference section:
- Article numbers (Article 14, 21, 32 etc.)
- SCC, AIR, SC, HC, CPC, IPC, CrPC, SLP
- petition, appeal, writ, order, judgment, decree, affidavit

FOCUS on things like:
- Latin phrases: ex parte, res judicata, locus standi, inter alia, suo motu
- Obscure procedural jargon: doctrine of parity, equal protection, directive principle
- Case-specific abbreviations: EB (Efficiency Bar in pay scales), N.T. Driver
- Domain terms specific to this case type

JUDGMENT TEXT:
{sample}

YOU MUST respond ONLY with valid JSON. No text before or after:
{{
  "terms": [
    {{"term": "Directive Principle", "explanation": "A constitutional guideline directing the government toward social justice — not directly enforceable in court but used to interpret laws."}},
    {{"term": "Doctrine of Parity", "explanation": "The legal principle that employees doing identical work must receive the same pay, regardless of which department they belong to."}}
  ]
}}

Return empty terms array if no genuinely obscure terms are found."""

    raw = _call_llm([{"role": "user", "content": prompt}], max_tokens=600, temperature=0.2)
    cleaned = _clean_json(raw)
    try:
        return json.loads(cleaned)
    except Exception:
        return {"terms": []}