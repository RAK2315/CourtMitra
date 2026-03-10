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


# Words that spaCy wrongly classifies as persons or orgs
PERSON_NOISE = {
    "order", "rule", "section", "article", "act", "court", "bench",
    "appellant", "respondent", "petitioner", "plaintiff", "defendant",
    "judgment", "decree", "appeal", "petition", "hon", "honourable",
    "j.", "j", "cpc", "ipc", "crpc", "sub-rule", "clause", "schedule",
    "xli", "xlii", "xliii", "order xli", "per contra",
}

ORG_NOISE = {
    "rs.", "rs", "inr", "₹", "rule", "order", "section", "sub-rule",
    "xli", "xlii", "review petition", "civil appeal", "writ petition",
}

# Indian legal patterns
PATTERNS = {
    "case_numbers": [
        # Standard: Civil Appeal Nos. 5168-5169 of 2011
        r'\b(?:Civil Appeal|Criminal Appeal|Writ Petition|SLP|Special Leave Petition|'
        r'W\.P\.|C\.A\.|Crl\.A\.|Review Petition|First Appeal|'
        r'Civil Suit|Criminal Case)\s*(?:Nos?\.?)?\s*[\d\-]+(?:\s*(?:of|OF)\s*\d{4})?\b',
        # Short: 3075/2024 or 80/1996
        r'\b\d{1,6}\s*/\s*\d{4}\b',
        # INSC citations: 2026 INSC 211
        r'\b\d{4}\s+INSC\s+\d+\b',
    ],
    "ipc_sections": [
        r'\bSection\s+\d+[A-Z]?\s*(?:and\s+\d+[A-Z]?)?\s+(?:of\s+)?(?:IPC|I\.P\.C\.|Indian Penal Code)\b',
        r'\bIPC\s+[Ss]ection\s+\d+[A-Z]?\b',
        r'\bunder\s+[Ss]ections?\s+\d+[A-Z]?(?:\s*(?:and|,)\s*\d+[A-Z]?)*\s+(?:of\s+the\s+)?IPC\b',
    ],
    "acts_cited": [
        r'(?:The\s+)?[A-Z][A-Za-z\s]+Act,?\s*\d{4}',
        r'Code of Criminal Procedure|CrPC|Cr\.P\.C\.',
        r'Code of Civil Procedure|CPC|C\.P\.C\.',
        r'Constitution of India',
        r'Indian Evidence Act',
        r'Transfer of Property Act',
        r'Hindu Marriage Act',
        r'Order\s+XLI(?:\s+Rule\s+\d+)?',  # CPC Order citations
    ],
    "monetary_amounts": [
        r'Rs\.?\s*[\d,]+(?:\.\d{2})?(?:/-)?\s*(?:\(?rupees?\)?)?(?:\s*(?:lakhs?|crores?|thousands?))?',
        r'₹\s*[\d,]+(?:\.\d{2})?',
        r'INR\s*[\d,]+',
    ],
    "dates": [
        r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|'
        r'July|August|September|October|November|December),?\s+\d{4}\b',
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
    ],
}


def _is_noise(text: str, noise_set: set) -> bool:
    """Check if extracted entity is junk."""
    t = text.strip().lower()
    if len(t) <= 2:
        return True
    if any(n in t for n in noise_set):
        return True
    # Filter things starting with digits (Rs amounts misclassified as orgs)
    if re.match(r'^\d', t):
        return True
    return False


def extract_entities(text: str) -> Dict:
    """Extract legal entities from judgment text."""
    nlp = get_nlp()
    doc = nlp(text[:100000])

    # NER from spaCy — with noise filtering
    persons = []
    seen_persons = set()
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text.strip()
            name_lower = name.lower()
            if (len(name) > 3
                    and name_lower not in seen_persons
                    and not _is_noise(name, PERSON_NOISE)
                    and not any(c.isdigit() for c in name)):
                seen_persons.add(name_lower)
                persons.append(name)
                if len(persons) >= 8:
                    break

    orgs = []
    seen_orgs = set()
    for ent in doc.ents:
        if ent.label_ == "ORG":
            org = ent.text.strip()
            org_lower = org.lower()
            if (len(org) > 4
                    and org_lower not in seen_orgs
                    and not _is_noise(org, ORG_NOISE)):
                seen_orgs.add(org_lower)
                orgs.append(org)
                if len(orgs) >= 8:
                    break

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
                if item_clean and item_clean.lower() not in seen and len(item_clean) > 2:
                    seen.add(item_clean.lower())
                    cleaned.append(item_clean)
            results[key] = cleaned[:6]

    return results


def extract_judgment_outcome(text: str) -> str:
    """Try to detect outcome: allowed, dismissed, remanded, etc."""
    text_lower = text.lower()
    outcome_patterns = [
        (r'\bappeals?\s+(?:stand[s]?\s+)?dismissed\b', "Appeal Dismissed ❌"),
        (r'\bappeal\s+is\s+allowed\b', "Appeal Allowed ✅"),
        (r'\bappeals?\s+(?:are\s+)?allowed\b', "Appeal Allowed ✅"),
        (r'\bpetition\s+is\s+allowed\b', "Petition Allowed ✅"),
        (r'\bpetition\s+(?:stand[s]?\s+)?dismissed\b', "Petition Dismissed ❌"),
        (r'\bmatter\s+is\s+remanded\b', "Remanded to Lower Court 🔄"),
        (r'\bremanded\s+back\b', "Remanded to Lower Court 🔄"),
        (r'\bconviction\s+is\s+set\s+aside\b', "Conviction Set Aside ✅"),
        (r'\bconviction\s+upheld\b', "Conviction Upheld ❌"),
        (r'\bpartly\s+allowed\b', "Partly Allowed ⚖️"),
        (r'\bsuit\s+(?:is\s+)?dismissed\b', "Suit Dismissed ❌"),
        (r'\bsettled\b', "Settled 🤝"),
    ]
    for pattern, label in outcome_patterns:
        if re.search(pattern, text_lower):
            return label
    return "Outcome unclear — check judgment order"