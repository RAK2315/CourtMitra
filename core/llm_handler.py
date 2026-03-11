import os
import time
import json
from groq import Groq, RateLimitError
from typing import List, Dict

# Models in priority order — each has separate rate limit quota
MODELS = [
    "llama-3.3-70b-versatile",   # best quality
    "llama-3.1-8b-instant",      # fast fallback
    "gemma2-9b-it",              # Google fallback
    "mixtral-8x7b-32768",        # Mistral fallback
]


def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to .env or Streamlit secrets.")
    return Groq(api_key=api_key)


def _call_groq(client, messages: list, max_tokens: int, temperature: float = 0.3) -> str:
    """
    Call Groq with automatic retry across multiple models.
    Tries each model with a short wait between attempts.
    """
    last_error = None
    for i, model in enumerate(MODELS):
        if i > 0:
            time.sleep(6)  # brief wait between model switches
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
            raise e

    raise RuntimeError(
        "All Groq models are rate limited. Please wait 60 seconds and try again."
    ) from last_error


def summarize_judgment(chunks: List[Dict], entities: Dict, language: str = "English") -> Dict:
    client = get_client()

    context = "\n\n".join([
        f"[{c['section']}]\n{c['content'][:600]}"
        for c in chunks[:5]
    ])

    lang_instruction = "Respond entirely in simple Hindi (Devanagari script)." if language == "Hindi" else ""

    prompt = f"""You are CourtMitra — explain this Indian court judgment to an ordinary Indian citizen with no legal background.
Tone: warm, clear, like a knowledgeable friend explaining over chai. NOT robotic. Use real names. Be specific.

STRICT RULES for plain_summary:
- Do NOT repeat the same fact twice in different words
- Each sentence must add NEW information
- Sentence 1: Who are the parties and what was the core dispute
- Sentence 2: What the lower court / previous proceedings decided
- Sentence 3: What the Supreme Court / High Court found and why
- Sentence 4: Final outcome — who won, what was ordered
- Use actual names from the judgment (e.g. "Randhir Singh", not "the petitioner")

JUDGMENT EXCERPTS:
{context}

ENTITIES:
- Cases: {', '.join(entities.get('case_numbers', [])) or 'N/A'}
- Acts: {', '.join(entities.get('acts_cited', [])[:3]) or 'N/A'}
- Articles: {', '.join(entities.get('statutes', [])[:3]) or 'N/A'}

{lang_instruction}

Respond ONLY with valid JSON (no markdown, no code fences):
{{
  "case_type": "one of: Criminal / Civil / Constitutional / Family / Labour / Consumer / Property / Service",
  "plain_summary": "exactly 4 sentences, each adding new info, no repetition, use real names",
  "key_issues": ["specific issue 1 in plain words", "specific issue 2", "specific issue 3"],
  "what_court_decided": "1 sentence — exactly what was ordered, any specific relief granted (amounts, directions)",
  "next_steps": ["step 1 for the person affected", "step 2", "step 3"],
  "important_warning": "one friendly reminder to consult a lawyer"
}}"""

    raw = _call_groq(client, [{"role": "user", "content": prompt}], max_tokens=900)
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "case_type": "Unknown",
            "plain_summary": raw,
            "key_issues": [],
            "what_court_decided": "",
            "next_steps": [],
            "important_warning": "Please consult a qualified lawyer for advice specific to your situation.",
        }


def build_reasoning_chain(chunks: List[Dict]) -> List[Dict]:
    client = get_client()

    context = "\n\n".join([c["content"][:500] for c in chunks[:4]])

    prompt = f"""Analyze this Indian court judgment and extract the judge's step-by-step reasoning and jurisdiction path.

JUDGMENT TEXT:
{context}

Respond ONLY with a valid JSON array (no markdown) of 5-7 steps covering:
1. Which court had original jurisdiction and under which Article/provision
2. What the lower court decided (if applicable)  
3. Key factual findings
4. Legal principle applied
5. Final decision and any further appeal avenue

Format:
[
  {{"step": 1, "label": "3-5 word title", "detail": "one plain English sentence", "type": "jurisdiction"}},
  {{"step": 2, "label": "3-5 word title", "detail": "one plain English sentence", "type": "fact"}},
  {{"step": 3, "label": "3-5 word title", "detail": "one plain English sentence", "type": "issue"}},
  {{"step": 4, "label": "3-5 word title", "detail": "one plain English sentence", "type": "argument"}},
  {{"step": 5, "label": "3-5 word title", "detail": "one plain English sentence", "type": "decision"}},
  {{"step": 6, "label": "Further Appeal", "detail": "If any party is aggrieved, they may approach [court] under [Article/provision]", "type": "appeal"}}
]
Types must be one of: jurisdiction, fact, issue, argument, law, decision, appeal"""

    raw = _call_groq(client, [{"role": "user", "content": prompt}], max_tokens=800, temperature=0.2)
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return [
            {"step": 1, "label": "Jurisdiction", "detail": "Court established jurisdiction over the matter.", "type": "jurisdiction"},
            {"step": 2, "label": "Facts Presented", "detail": "Parties presented their respective facts.", "type": "fact"},
            {"step": 3, "label": "Legal Issues", "detail": "Court identified the core legal questions.", "type": "issue"},
            {"step": 4, "label": "Law Applied", "detail": "Relevant statutes and precedents were considered.", "type": "law"},
            {"step": 5, "label": "Final Order", "detail": "Court delivered its judgment.", "type": "decision"},
        ]


def answer_question(question: str, chunks: List[Dict], full_text: str = "", language: str = "English") -> str:
    client = get_client()

    # Use more chunks + more content per chunk for specific fact questions
    chunk_context = "\n\n".join([c["content"][:700] for c in chunks[:6]])

    # Also include first 1500 chars of full text (headnote/facts section has specific figures)
    preamble = full_text[:1500] if full_text else ""

    context = f"HEADNOTE/OPENING:\n{preamble}\n\nRETRIEVED SECTIONS:\n{chunk_context}" if preamble else chunk_context

    lang_instruction = "Respond in simple Hindi." if language == "Hindi" else "Respond in simple English."

    prompt = f"""You are CourtMitra. Answer the question using ONLY the judgment text below.

IMPORTANT INSTRUCTIONS:
- Search carefully for specific numbers, pay scales (e.g. Rs. 210-270), amounts, dates, names
- If the answer contains specific figures, quote them exactly from the text
- Pay scales often appear as "Rs. XXX-YYY" format — look carefully
- If genuinely not present, say "This specific detail is not mentioned in the uploaded judgment"
- Do NOT say it's not there if figures are present — look harder first

JUDGMENT TEXT:
{context}

QUESTION: {question}

{lang_instruction}
Answer in 2-5 sentences. Quote specific figures if present. No legal advice."""

    return _call_groq(client, [{"role": "user", "content": prompt}], max_tokens=450)


def extract_legal_terms(text: str) -> Dict[str, str]:
    """Extract hard legal terms from judgment and return plain English explanations."""
    client = get_client()

    # Sample first 3000 chars — terms appear early in judgments
    sample = text[:3000]

    prompt = f"""You are CourtMitra. Extract up to 10 difficult legal terms or Latin phrases from this Indian court judgment text and explain each in plain simple English (1 sentence each). Focus on terms a non-lawyer would not understand.

JUDGMENT TEXT:
{sample}

Respond ONLY with valid JSON (no markdown):
{{
  "terms": [
    {{"term": "Ex parte", "explanation": "A decision made without hearing one side of the case."}},
    {{"term": "Writ of Mandamus", "explanation": "A court order telling a government body to do something it is legally required to do."}},
    {{"term": "Locus standi", "explanation": "The right to bring a case to court — you must have a direct interest in the matter."}}
  ]
}}

Only include terms actually present in the text. Return empty array if no hard terms found."""

    raw = _call_groq(client, [{"role": "user", "content": prompt}], max_tokens=600, temperature=0.2)
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"terms": []}