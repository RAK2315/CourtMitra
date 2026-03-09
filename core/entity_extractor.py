import re
from typing import Dict, List
import spacy

_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            _nlp = spacy.load("en_core_web_sm")
    return _nlp


# Indian legal patterns
PATTERNS = {
    "case_numbers": [
        r'\b(Civil Appeal|Criminal Appeal|Writ Petition|SLP|Special Leave Petition|'
        r'W\.P\.|C\.A\.|Crl\.A\.)[\s\(]*No[\s\.]*\d+[\s/\-]*(?:of\s*)?\d{4}\b',
        r'\b\d{1,5}\s*/\s*\d{4}\b',
    ],
    "ipc_sections": [
        r'\bSection\s+\d+[A-Z]?\s*(?:and\s+\d+[A-Z]?)?\s+(?:of\s+)?(?:IPC|I\.P\.C\.|Indian Penal Code)\b',
        r'\bIPC\s+[Ss]ection\s+\d+[A-Z]?\b',
        r'\bunder\s+[Ss]ection\s+\d+[A-Z]?\b',
    ],
    "acts_cited": [
        r'(?:The\s+)?[A-Z][A-Za-z\s]+Act,?\s*\d{4}',
        r'Code of Criminal Procedure|CrPC|Cr\.P\.C\.',
        r'Code of Civil Procedure|CPC|C\.P\.C\.',
        r'Constitution of India',
        r'Indian Evidence Act',
        r'Transfer of Property Act',
        r'Hindu Marriage Act',
    ],
    "monetary_amounts": [
        r'Rs\.?\s*[\d,]+(?:\.\d{2})?(?:\s*(?:lakhs?|crores?|thousands?))?',
        r'₹\s*[\d,]+(?:\.\d{2})?',
        r'INR\s*[\d,]+',
    ],
    "dates": [
        r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|'
        r'July|August|September|October|November|December),?\s+\d{4}\b',
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
    ],
}


def extract_entities(text: str) -> Dict:
    """Extract legal entities from judgment text."""
    nlp = get_nlp()
    doc = nlp(text[:100000])  # spaCy limit

    # NER from spaCy
    persons = list(set([
        ent.text.strip() for ent in doc.ents
        if ent.label_ == "PERSON" and len(ent.text.strip()) > 3
    ]))[:8]

    orgs = list(set([
        ent.text.strip() for ent in doc.ents
        if ent.label_ == "ORG" and len(ent.text.strip()) > 3
    ]))[:8]

    # Pattern-based extraction
    results = {
        "persons_mentioned": persons,
        "organizations": orgs,
        "case_numbers": [],
        "ipc_sections": [],
        "acts_cited": [],
        "monetary_amounts": [],
        "key_dates": [],
    }

    for pattern in PATTERNS["case_numbers"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        results["case_numbers"].extend(matches)

    for pattern in PATTERNS["ipc_sections"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        results["ipc_sections"].extend(matches)

    for pattern in PATTERNS["acts_cited"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        results["acts_cited"].extend(matches)

    for pattern in PATTERNS["monetary_amounts"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        results["monetary_amounts"].extend(matches)

    for pattern in PATTERNS["dates"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        results["key_dates"].extend(matches)

    # Deduplicate and clean
    for key in results:
        if isinstance(results[key], list):
            seen = set()
            cleaned = []
            for item in results[key]:
                item_clean = item.strip()
                if item_clean and item_clean.lower() not in seen:
                    seen.add(item_clean.lower())
                    cleaned.append(item_clean)
            results[key] = cleaned[:6]  # cap at 6 per category

    return results


def extract_judgment_outcome(text: str) -> str:
    """Try to detect outcome: allowed, dismissed, remanded, etc."""
    text_lower = text.lower()
    outcome_patterns = [
        (r'\bappeal\s+is\s+allowed\b', "Appeal Allowed ✅"),
        (r'\bappeal\s+is\s+dismissed\b', "Appeal Dismissed ❌"),
        (r'\bpetition\s+is\s+allowed\b', "Petition Allowed ✅"),
        (r'\bpetition\s+is\s+dismissed\b', "Petition Dismissed ❌"),
        (r'\bmatter\s+is\s+remanded\b', "Remanded to Lower Court 🔄"),
        (r'\bremanded\s+back\b', "Remanded to Lower Court 🔄"),
        (r'\bconviction\s+is\s+set\s+aside\b', "Conviction Set Aside ✅"),
        (r'\bconviction\s+upheld\b', "Conviction Upheld ❌"),
        (r'\bpartly\s+allowed\b', "Partly Allowed ⚖️"),
        (r'\bsettled\b', "Settled 🤝"),
    ]
    for pattern, label in outcome_patterns:
        if re.search(pattern, text_lower):
            return label
    return "Outcome unclear — check judgment order"
