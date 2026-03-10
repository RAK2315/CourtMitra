import os
import time
import json
from groq import Groq, RateLimitError
from typing import List, Dict

MODEL = "llama-3.3-70b-versatile"
# Fallback to smaller/faster model if rate limit persists
FALLBACK_MODEL = "llama-3.1-8b-instant"


def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to .env or Streamlit secrets.")
    return Groq(api_key=api_key)


def _call_groq(client, messages: list, max_tokens: int, temperature: float = 0.3) -> str:
    """
    Call Groq with automatic retry + fallback model on rate limit.
    Tries: main model → wait 10s → retry → fallback model → wait 20s → error.
    """
    attempts = [
        (MODEL, 0),
        (MODEL, 10),
        (FALLBACK_MODEL, 5),
        (FALLBACK_MODEL, 20),
    ]
    last_error = None
    for model, wait in attempts:
        if wait > 0:
            time.sleep(wait)
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
            raise e  # non-rate-limit errors raise immediately

    raise RuntimeError(
        "Groq rate limit exceeded across all retries. "
        "Please wait 60 seconds and try again, or upgrade your Groq plan at console.groq.com."
    ) from last_error


def summarize_judgment(chunks: List[Dict], entities: Dict, language: str = "English") -> Dict:
    client = get_client()

    # Use only top 5 chunks and cap each at 600 chars to reduce token usage
    context = "\n\n".join([
        f"[{c['section']}]\n{c['content'][:600]}"
        for c in chunks[:5]
    ])

    lang_instruction = "Respond entirely in simple Hindi (Devanagari script)." if language == "Hindi" else ""

    prompt = f"""You are CourtMitra — explain this Indian court judgment to an ordinary citizen with no legal background.
Tone: warm, clear, like a knowledgeable friend. NOT robotic. Use real names. Be specific.

JUDGMENT EXCERPTS:
{context}

ENTITIES: Cases: {', '.join(entities.get('case_numbers', [])) or 'N/A'} | Acts: {', '.join(entities.get('acts_cited', [])[:3]) or 'N/A'} | IPC: {', '.join(entities.get('ipc_sections', [])) or 'N/A'}

{lang_instruction}

Respond ONLY with valid JSON (no markdown):
{{
  "case_type": "Criminal / Civil / Constitutional / Family / Labour / Consumer / Property",
  "plain_summary": "3-4 sentences, conversational, use names, say who won and why. Class 10 student should understand.",
  "key_issues": ["issue 1 in plain words", "issue 2", "issue 3"],
  "what_court_decided": "1 sentence — exactly what was ordered, plain words",
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

    # Cap chunks at 4, each at 500 chars
    context = "\n\n".join([c["content"][:500] for c in chunks[:4]])

    prompt = f"""Analyze this Indian court judgment and extract the judge's step-by-step reasoning chain.

JUDGMENT TEXT:
{context}

Respond ONLY with a valid JSON array (no markdown) of 4-6 steps:
[
  {{"step": 1, "label": "3-5 word title", "detail": "one plain English sentence", "type": "fact"}},
  {{"step": 2, "label": "3-5 word title", "detail": "one plain English sentence", "type": "issue"}},
  {{"step": 3, "label": "3-5 word title", "detail": "one plain English sentence", "type": "argument"}},
  {{"step": 4, "label": "3-5 word title", "detail": "one plain English sentence", "type": "law"}},
  {{"step": 5, "label": "3-5 word title", "detail": "one plain English sentence", "type": "decision"}}
]
Types: fact, issue, argument, law, decision only."""

    raw = _call_groq(client, [{"role": "user", "content": prompt}], max_tokens=700, temperature=0.2)
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return [
            {"step": 1, "label": "Facts Presented", "detail": "Parties presented their respective facts.", "type": "fact"},
            {"step": 2, "label": "Legal Issues", "detail": "Court identified the core legal questions.", "type": "issue"},
            {"step": 3, "label": "Law Applied", "detail": "Relevant statutes and precedents were considered.", "type": "law"},
            {"step": 4, "label": "Final Order", "detail": "Court delivered its judgment.", "type": "decision"},
        ]


def answer_question(question: str, chunks: List[Dict], language: str = "English") -> str:
    client = get_client()

    # Cap at 3 chunks, 400 chars each
    context = "\n\n".join([c["content"][:400] for c in chunks[:3]])
    lang_instruction = "Respond in simple Hindi." if language == "Hindi" else "Respond in simple English."

    prompt = f"""You are CourtMitra. Answer the question using ONLY information from the text below. If the answer isn't there, say so.

JUDGMENT EXCERPTS:
{context}

QUESTION: {question}

{lang_instruction}
Keep answer to 2-4 sentences. No legal advice."""

    return _call_groq(client, [{"role": "user", "content": prompt}], max_tokens=350)