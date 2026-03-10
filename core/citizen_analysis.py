import re
from datetime import datetime, timedelta
from typing import Dict, List
from groq import Groq
import os

# ── Fundamental Rights ────────────────────────────────────────────────────────
FUNDAMENTAL_RIGHTS = {
    "Article 14": ("Right to Equality", "Every person is equal before the law. Nobody can be treated differently without a valid reason."),
    "Article 19": ("Freedom of Speech & Expression", "Citizens have the right to speak freely, assemble peacefully, and move anywhere in India."),
    "Article 20": ("Protection Against Arbitrary Conviction", "No one can be punished for an act that wasn't a crime when it was done. No double punishment."),
    "Article 21": ("Right to Life & Personal Liberty", "No person can be deprived of their life or freedom except by a fair legal process."),
    "Article 21A": ("Right to Education", "Every child aged 6–14 has the right to free and compulsory education."),
    "Article 22": ("Protection Against Arbitrary Arrest", "Every arrested person has the right to know why they're arrested and to consult a lawyer."),
    "Article 23": ("Prohibition of Forced Labour", "Human trafficking and forced labour are banned."),
    "Article 24": ("Prohibition of Child Labour", "Children under 14 cannot work in factories, mines, or hazardous work."),
    "Article 25": ("Freedom of Religion", "Every person has the right to practice and propagate their religion."),
    "Article 32": ("Right to Constitutional Remedies", "Every citizen can approach the Supreme Court directly if their fundamental rights are violated."),
    "Article 226": ("High Court Writ Jurisdiction", "Citizens can approach the High Court to enforce their legal rights."),
    "Article 300A": ("Right to Property", "No person can be deprived of their property without the authority of law."),
}

# ── Appeal Deadlines ──────────────────────────────────────────────────────────
APPEAL_DEADLINES = {
    "Criminal": {
        "days": 90,
        "court": "Supreme Court of India",
        "section": "Section 374 CrPC",
        "note": "Appeal against conviction to Sessions Court within 30 days; to HC within 60 days; to SC within 90 days."
    },
    "Civil": {
        "days": 90,
        "court": "Higher Court",
        "section": "Order 41 CPC",
        "note": "First appeal to District Court within 30 days; second appeal to HC within 90 days of HC decree."
    },
    "Family": {
        "days": 90,
        "court": "High Court",
        "section": "Section 28 Hindu Marriage Act",
        "note": "Appeal against family court order to High Court within 90 days."
    },
    "Consumer": {
        "days": 30,
        "court": "State Consumer Commission",
        "section": "Section 41 Consumer Protection Act 2019",
        "note": "Appeal against District Commission order within 30 days to State Commission."
    },
    "Labour": {
        "days": 60,
        "court": "High Court",
        "section": "Section 217 Industrial Relations Code",
        "note": "Challenge Labour Court order in High Court within 60 days."
    },
    "Constitutional": {
        "days": 90,
        "court": "Supreme Court of India",
        "section": "Article 136",
        "note": "Special Leave Petition to Supreme Court within 90 days of HC judgment."
    },
    "Property": {
        "days": 90,
        "court": "High Court / Supreme Court",
        "section": "Order 41 CPC / Article 136",
        "note": "Appeal within 90 days. Limitation period may vary — consult a lawyer immediately."
    },
}


def detect_rights(text: str) -> List[Dict]:
    """Detect which fundamental rights are mentioned or implicated in the judgment."""
    found = []
    text_lower = text.lower()

    for article, (name, explanation) in FUNDAMENTAL_RIGHTS.items():
        article_lower = article.lower()
        article_num = article.replace("Article ", "")

        if (article_lower in text_lower or
            f"article {article_num}" in text_lower or
            f"art. {article_num}" in text_lower or
            f"art {article_num}" in text_lower):
            found.append({
                "article": article,
                "name": name,
                "explanation": explanation,
            })

    return found


def calculate_appeal_deadline(case_type: str, judgment_date_str: str) -> Dict:
    """Calculate appeal deadline from judgment date and case type."""
    deadline_info = APPEAL_DEADLINES.get(case_type, APPEAL_DEADLINES["Civil"])

    # Try to parse judgment date
    judgment_date = None
    date_formats = [
        "%d %B %Y", "%B %d, %Y", "%d/%m/%Y",
        "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y",
    ]

    # Clean the date string
    date_str = judgment_date_str.strip() if judgment_date_str else ""
    for fmt in date_formats:
        try:
            judgment_date = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue

    if judgment_date:
        deadline = judgment_date + timedelta(days=deadline_info["days"])
        today = datetime.now()
        days_left = (deadline - today).days

        return {
            "found_date": True,
            "judgment_date": judgment_date.strftime("%d %B %Y"),
            "deadline_date": deadline.strftime("%d %B %Y"),
            "days_left": days_left,
            "deadline_days": deadline_info["days"],
            "appeal_court": deadline_info["court"],
            "section": deadline_info["section"],
            "note": deadline_info["note"],
            "status": "expired" if days_left < 0 else "urgent" if days_left < 15 else "active",
        }
    else:
        return {
            "found_date": False,
            "deadline_days": deadline_info["days"],
            "appeal_court": deadline_info["court"],
            "section": deadline_info["section"],
            "note": deadline_info["note"],
            "status": "unknown",
        }


def detect_red_flags(text: str, chunks: List[Dict]) -> Dict:
    """Detect procedural red flags in the judgment."""
    from groq import RateLimitError
    import time

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    context = "\n\n".join([c["content"][:400] for c in chunks[:4]])

    prompt = f"""You are a legal analyst reviewing an Indian court judgment for procedural concerns.

JUDGMENT TEXT:
{context}

Analyze for: ex-parte orders, unexplained delays, inconsistent application of law, vague allegations accepted without scrutiny, contradictory findings, procedural violations, insufficient evidence.

Respond ONLY with valid JSON (no markdown):
{{
  "danger_score": <integer 0-100, where 0=perfectly fair, 100=severely concerning>,
  "flags": [
    {{"issue": "short title", "detail": "one sentence explanation", "severity": "high|medium|low"}}
  ],
  "overall_assessment": "one plain English sentence about fairness",
  "positive_observations": ["one thing court did right", "another positive"]
}}

Be objective. Empty flags array if no issues found."""

    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    for i, model in enumerate(models):
        if i > 0:
            time.sleep(8)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.2,
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except RateLimitError:
            continue
        except Exception:
            break

    return {
        "danger_score": 0,
        "flags": [],
        "overall_assessment": "Analysis unavailable — rate limit reached. Try again in a moment.",
        "positive_observations": [],
    }