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


# ── Noise word sets ───────────────────────────────────────────────────────────
# Any spaCy PERSON entity whose text contains these words is discarded
PERSON_NOISE_WORDS = {
    "order", "rule", "section", "article", "act", "court", "bench",
    "appellant", "respondent", "petitioner", "plaintiff", "defendant",
    "judgment", "decree", "appeal", "petition", "honourable",
    "cpc", "ipc", "crpc", "sub-rule", "clause", "schedule",
    "survey", "no.", "hereinafter", "per contra", "supra",
    "xli", "xlii", "xliii", "xliv", "viz", "vide",
}

# Any spaCy ORG entity whose text contains these words is discarded
ORG_NOISE_WORDS = {
    "rs.", "rs", "inr", "rule", "order", "section", "sub-rule",
    "xli", "review petition", "civil appeal", "writ petition",
    "appellate jurisdiction", "apellate jurisdiction",
    "hereinafter", "civil suit no",
}


def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    return s


def _is_person_noise(name: str) -> bool:
    n = name.lower()
    if len(n) <= 3:
        return True
    if any(c.isdigit() for c in name):
        return True
    if any(word in n for word in PERSON_NOISE_WORDS):
        return True
    # Discard single-word all-caps that aren't real names (e.g. "DATE", "VERSUS")
    if name.isupper() and ' ' not in name and len(name) < 6:
        return True
    return False


def _is_org_noise(org: str) -> bool:
    o = org.lower()
    if len(o) <= 4:
        return True
    if any(word in o for word in ORG_NOISE_WORDS):
        return True
    # Starts with digit
    if re.match(r'^\d', o):
        return True
    # PDF header: all caps + very long
    if org.isupper() and len(org) > 25:
        return True
    # Single word "Date" or "No" misclassified
    if org.strip() in {"Date", "No", "No.", "J", "J."}:
        return True
    return False


# ── Regex patterns ────────────────────────────────────────────────────────────
CASE_NUMBER_PATTERNS = [
    # Civil/Criminal Appeal Nos. 5168-5169 of 2011
    r'\b(?:Civil Appeal|Criminal Appeal|Writ Petition|SLP|Special Leave Petition|'
    r'W\.P\.|C\.A\.|Crl\.A\.|Review Petition|First Appeal|Civil Suit|Criminal Case|'
    r'CRL\.A\.|CRL\.P\.|W\.P\.\(C\))\s*(?:Nos?\.?)?\s*[\d][\d\-]*'
    r'(?:\s*(?:of|OF)\s*\d{4})?\b',
    # 3075/2024 style
    r'\b\d{1,6}\s*/\s*\d{4}\b',
    # 2026 INSC 211 style
    r'\b\d{4}\s+INSC\s+\d+\b',
]

IPC_SECTION_PATTERNS = [
    r'\bSections?\s+\d+[A-Z]?(?:\s*,\s*\d+[A-Z]?)*(?:\s+and\s+\d+[A-Z]?)?\s+'
    r'(?:of\s+(?:the\s+)?)?(?:IPC|I\.P\.C\.|Indian Penal Code)\b',
    r'\bIPC\s+[Ss]ections?\s+\d+[A-Z]?\b',
    r'\bSections?\s+\d+[A-Z]?\s*(?:,\s*\d+[A-Z]?\s*)*(?:and\s+\d+[A-Z]?\s+)?'
    r'of\s+(?:the\s+)?(?:IPC|Indian Penal Code)\b',
    # Sections 341, 323, 498A and 34 of the IPC
    r'\bSections?\s+\d+[A-Z]?(?:\s*[,&]\s*\d+[A-Z]?)+\s+(?:and\s+\d+[A-Z]\s+)?'
    r'of\s+(?:the\s+)?IPC\b',
]

ACT_PATTERNS = [
    r'(?:The\s+)?[A-Z][A-Za-z\s]{3,40}Act,?\s*\d{4}',
    r'Code of Criminal Procedure|CrPC|Cr\.P\.C\.',
    r'Code of Civil Procedure|CPC|C\.P\.C\.',
    r'Constitution of India',
    r'Indian Evidence Act',
    r'Transfer of Property Act',
    r'Hindu Marriage Act',
]

# Rs. must be followed by at least 3 digits (so Rs.2,000 matches, rs, and rs.3 don't)
AMOUNT_PATTERNS = [
    r'Rs\.?\s*\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?(?:/-)?',   # Rs.2,000/- or Rs.1,00,000
    r'Rs\.?\s*\d{4,}(?:\.\d{1,2})?(?:/-)?',                 # Rs.5000 or Rs.50000
    r'Rs\.?\s*\d+(?:\.\d{2})?\s*(?:lakhs?|crores?)',        # Rs.5 lakhs
    r'₹\s*\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?',
    r'₹\s*\d{4,}',
    r'INR\s+\d{4,}',
]

DATE_PATTERNS = [
    r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|'
    r'July|August|September|October|November|December),?\s+\d{4}\b',
    r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
]


def extract_entities(text: str) -> Dict:
    nlp = get_nlp()
    doc = nlp(text[:100000])

    # ── spaCy NER ─────────────────────────────────────────────────────────────
    persons, seen_p = [], set()
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text.strip()
            if not _is_person_noise(name) and name.lower() not in seen_p:
                seen_p.add(name.lower())
                persons.append(name)
                if len(persons) >= 7:
                    break

    orgs, seen_o = [], set()
    for ent in doc.ents:
        if ent.label_ == "ORG":
            org = ent.text.strip()
            if not _is_org_noise(org) and org.lower() not in seen_o:
                seen_o.add(org.lower())
                orgs.append(org)
                if len(orgs) >= 7:
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

    # ── Regex extraction ──────────────────────────────────────────────────────
    for p in CASE_NUMBER_PATTERNS:
        results["case_numbers"].extend(re.findall(p, text, re.IGNORECASE))

    for p in IPC_SECTION_PATTERNS:
        results["ipc_sections"].extend(re.findall(p, text, re.IGNORECASE))

    for p in ACT_PATTERNS:
        results["acts_cited"].extend(re.findall(p, text, re.IGNORECASE))

    for p in AMOUNT_PATTERNS:
        results["monetary_amounts"].extend(re.findall(p, text, re.IGNORECASE))

    for p in DATE_PATTERNS:
        results["key_dates"].extend(re.findall(p, text, re.IGNORECASE))

    # ── Deduplicate (prefix-aware) ────────────────────────────────────────────
    for key in results:
        if not isinstance(results[key], list):
            continue
        seen_norms, cleaned = set(), []
        for item in results[key]:
            item = item.strip()
            if not item or len(item) <= 2:
                continue
            norm = _normalize(item)
            # Skip if already have something with same 28-char prefix
            if any(norm[:28] == s[:28] for s in seen_norms):
                continue
            seen_norms.add(norm)
            cleaned.append(item)
            if len(cleaned) >= 6:
                break
        results[key] = cleaned

    return results


def extract_judgment_outcome(text: str) -> str:
    text_lower = text.lower()
    patterns = [
        (r'\bappeals?\s+(?:stand[s]?\s+)?dismissed\b',     "Appeal Dismissed ❌"),
        (r'\bappeal\s+is\s+(?:hereby\s+)?allowed\b',        "Appeal Allowed ✅"),
        (r'\bappeals?\s+(?:are\s+|hereby\s+)?allowed\b',    "Appeal Allowed ✅"),
        (r'\bpetition\s+is\s+(?:hereby\s+)?allowed\b',      "Petition Allowed ✅"),
        (r'\bpetition\s+(?:stand[s]?\s+)?dismissed\b',      "Petition Dismissed ❌"),
        (r'\bsuit\s+(?:is\s+|stand[s]?\s+)?dismissed\b',    "Suit Dismissed ❌"),
        (r'\bmatter\s+is\s+remanded\b',                      "Remanded to Lower Court 🔄"),
        (r'\bremanded\s+back\b',                             "Remanded to Lower Court 🔄"),
        (r'\bconviction\s+(?:is\s+)?set\s+aside\b',         "Conviction Set Aside ✅"),
        (r'\bconviction\s+upheld\b',                         "Conviction Upheld ❌"),
        (r'\bpartly\s+allowed\b',                            "Partly Allowed ⚖️"),
        (r'\bsettled\b',                                     "Settled 🤝"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, text_lower):
            return label
    return "Outcome unclear — check judgment order"