import os
from groq import Groq
from typing import List, Dict

MODEL = "llama-3.3-70b-versatile"


def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in environment variables.")
    return Groq(api_key=api_key)


def summarize_judgment(chunks: List[Dict], entities: Dict, language: str = "English") -> Dict:
    """
    Generate a structured plain-language summary of the judgment.
    Returns dict with summary, key_issues, next_steps, case_type.
    """
    client = get_client()

    context = "\n\n".join([
        f"[{c['section']}]\n{c['content']}"
        for c in chunks[:6]
    ])

    lang_instruction = ""
    if language == "Hindi":
        lang_instruction = "Respond entirely in simple Hindi (Devanagari script)."

    prompt = f"""You are CourtMitra — you explain Indian court judgments to ordinary Indian citizens who have no legal background.

Your tone is: warm, clear, like a knowledgeable friend explaining over chai. NOT robotic. NOT formal legal language.
Use real names of people if mentioned. Be specific about what actually happened.

JUDGMENT EXCERPTS:
{context}

EXTRACTED ENTITIES:
- Case Numbers: {', '.join(entities.get('case_numbers', [])) or 'Not found'}
- Acts Cited: {', '.join(entities.get('acts_cited', [])) or 'Not found'}
- IPC Sections: {', '.join(entities.get('ipc_sections', [])) or 'Not found'}
- Amounts: {', '.join(entities.get('monetary_amounts', [])) or 'Not found'}

{lang_instruction}

Respond ONLY with a valid JSON object in this exact format (no markdown, no extra text):
{{
  "case_type": "one of: Criminal / Civil / Constitutional / Family / Labour / Consumer / Property",
  "plain_summary": "3-4 sentences in simple conversational language. Use names. Say WHO did WHAT, what the lower court decided, why the Supreme Court disagreed, and what the final result is. A Class 10 student should understand this completely.",
  "key_issues": ["specific issue 1 in plain words", "specific issue 2", "specific issue 3"],
  "what_court_decided": "1 punchy sentence — exactly what was ordered, using plain words not legal jargon",
  "next_steps": ["concrete step 1 for the person affected", "concrete step 2", "concrete step 3"],
  "important_warning": "one friendly line reminding them to consult a lawyer for their specific situation"
}}"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.3,
    )

    import json
    raw = response.choices[0].message.content.strip()
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
    """
    Extract the logical reasoning chain from the judgment.
    Returns a list of reasoning steps for flowchart rendering.
    """
    client = get_client()

    context = "\n\n".join([c["content"] for c in chunks[:5]])

    prompt = f"""You are analyzing an Indian court judgment to extract the judge's step-by-step reasoning chain.

JUDGMENT TEXT:
{context}

Respond ONLY with a valid JSON array (no markdown, no extra text) of 4-7 reasoning steps:
[
  {{"step": 1, "label": "short step title", "detail": "one sentence explanation", "type": "fact"}},
  {{"step": 2, "label": "short step title", "detail": "one sentence explanation", "type": "issue"}},
  {{"step": 3, "label": "short step title", "detail": "one sentence explanation", "type": "argument"}},
  {{"step": 4, "label": "short step title", "detail": "one sentence explanation", "type": "law"}},
  {{"step": 5, "label": "short step title", "detail": "one sentence explanation", "type": "decision"}}
]

Types must be one of: fact, issue, argument, law, decision
Make labels SHORT (3-5 words max). Details must be simple plain English."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.2,
    )

    import json
    raw = response.choices[0].message.content.strip()
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
    """Answer a specific question about the judgment using retrieved chunks."""
    client = get_client()

    context = "\n\n".join([c["content"] for c in chunks[:4]])

    lang_instruction = "Respond in simple Hindi." if language == "Hindi" else "Respond in simple English."

    prompt = f"""You are CourtMitra. Answer the following question about this court judgment using ONLY information from the provided text. If the answer is not in the text, say so clearly.

JUDGMENT EXCERPTS:
{context}

QUESTION: {question}

{lang_instruction}
Keep your answer concise (2-4 sentences). Do not add legal advice."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()