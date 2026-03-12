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
PERSON_NOISE_WORDS = {
    "order", "rule", "section", "article", "act", "court", "bench",
    "appellant", "respondent", "petitioner", "plaintiff", "defendant",
    "judgment", "decree", "appeal", "petition", "honourable",
    "cpc", "ipc", "crpc", "sub-rule", "clause", "schedule",
    "survey", "no.", "hereinafter", "per contra", "supra",
    "xli", "xlii", "xliii", "xliv", "viz", "vide",
    "misc", "code", "facts", "annexure", "exhibit",
    "municipal", "nagar", "colony", "street", "road", "village",
    "azad", "bazar", "chowk", "ward", "taluka", "tehsil", "district",
    # Indian states and cities misread as persons
    "kerala", "punjab", "haryana", "gujarat", "maharashtra", "karnataka",
    "pradesh", "bengal", "rajasthan", "bihar", "odisha", "assam",
    "bharat", "hindustan", "india",
    "kanpur", "lucknow", "mumbai", "delhi", "chennai", "kolkata",
    "moradabad", "gwalior", "nagpur", "patna", "agra", "varanasi",
    # Common English/legal words misread as persons
    "body", "cane", "sugar", "state", "party", "board", "trust",
    "fund", "bank", "union", "authority", "principles", "principle",
    "commission", "committee", "tribunal", "forum", "bench",
    "division", "single", "full", "larger", "constitution",
    "government", "ministry", "department", "directorate",
}

ORG_NOISE_WORDS = {
    "rs.", "rs", "inr", "rule", "order", "section", "sub-rule",
    "xli", "review petition", "civil appeal", "writ petition",
    "appellate jurisdiction", "apellate jurisdiction",
    "hereinafter", "civil suit no",
    "rupees", "lacs", "lakhs", "crores",
    "municipal no", "plot no", "survey no", "flat no", "ward no",
    "date:", "digitally signed", "reason:",
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
    if name.isupper() and ' ' not in name and len(name) < 6:
        return True
    return False


def _is_org_noise(org: str) -> bool:
    o = org.lower()
    if len(o) <= 4:
        return True
    if any(word in o for word in ORG_NOISE_WORDS):
        return True
    if re.match(r'^\d', o):
        return True
    if org.isupper() and len(org) > 25:
        return True
    if org.strip() in {"Date", "No", "No.", "J", "J.", "Facts", "FACTS", "Motor", "State", "Bench"}:
        return True
    # Single all-caps word = legal citation abbreviation or name fragment (FACLR, REDDY, BENCH)
    if re.match(r'^[A-Z]{3,12}$', org.strip()):
        return True
    if re.search(r'\([A-Z]$', org):
        return True
    if re.match(r'(?:original\s+suit|civil\s+suit|criminal\s+case)\s+no', o):
        return True
    words = org.strip().split()
    if (org.isupper() and len(words) == 2
            and all(w.isalpha() for w in words)
            and not any(w.lower() in {"ltd", "pvt", "inc", "corp", "co"} for w in words)):
        return True
    return False


# ── Patterns ──────────────────────────────────────────────────────────────────
CASE_NUMBER_PATTERNS = [
    r'\b(?:Civil Appeal|Criminal Appeal|Writ Petition|SLP|Special Leave Petition|'
    r'W\.P\.|C\.A\.|Crl\.A\.|Review Petition|First Appeal|Civil Suit|Criminal Case|'
    r'CRL\.A\.|CRL\.P\.|W\.P\.\(C\))\s*(?:Nos?\.?)?\s*[\d][\d\-]*'
    r'(?:\s*(?:of|OF)\s*\d{4})?\b',
    r'\b\d{1,6}\s*/\s*\d{4}\b',
    r'\b\d{4}\s+INSC\s+\d+\b',
]

IPC_SECTION_PATTERNS = [
    r'\bSections?\s+\d+[A-Z]?(?:\s*,\s*\d+[A-Z]?)*(?:\s+and\s+\d+[A-Z]?)?\s+'
    r'(?:of\s+(?:the\s+)?)?(?:IPC|I\.P\.C\.|Indian Penal Code)\b',
    r'\bIPC\s+[Ss]ections?\s+\d+[A-Z]?\b',
    r'\bSections?\s+\d+[A-Z]?\s*(?:,\s*\d+[A-Z]?\s*)*(?:and\s+\d+[A-Z]?\s+)?'
    r'of\s+(?:the\s+)?(?:IPC|Indian Penal Code)\b',
    r'\bSections?\s+\d+[A-Z]?(?:\s*[,&]\s*\d+[A-Z]?)+\s+(?:and\s+\d+[A-Z]\s+)?'
    r'of\s+(?:the\s+)?IPC\b',
    r'\bsection\s+\d+[A-Z]?\s+of\s+(?:the\s+)?I\.P\.C\.\b',
]

ACT_PATTERNS = [
    r'\b(?:The\s+)?[A-Z][A-Za-z]{2,}(?:\s+[A-Za-z]{2,}){0,6}\s+Act,?\s*\d{4}\b',
    r'\bCode of Criminal Procedure\b|\bCrPC\b|\bCr\.P\.C\.\b',
    r'\bCode of Civil Procedure\b|\bCPC\b|\bC\.P\.C\.\b',
    r'\bConstitution of India\b',
    r'\bIndian Evidence Act\b',
    r'\bTransfer of Property Act\b',
    r'\bHindu Marriage Act\b',
]

# Statutes = Constitutional Articles + key CPC/CrPC provisions
STATUTE_PATTERNS = [
    # Article 14, Art. 21, Art. 39(d) etc.
    r'\b(?:Article|Art\.)\s*\d+[A-Z]?(?:\s*\(\w+\))?\b',
    # Order XLI Rule 27 CPC
    r'\bOrder\s+[IVXLCDM]+\s+Rule\s+\d+[A-Z]?\b',
    # Section 482 CrPC / Section 300A IPC style cross-refs
    r'\bSection\s+\d+[A-Z]?\s+(?:of\s+(?:the\s+)?)?(?:CrPC|Cr\.P\.C\.|CPC|C\.P\.C\.)\b',
]

# Cited cases: "Name v. Name, (YYYY) N SCC NNN" or "AIR YYYY SC NNN"
CITED_CASE_PATTERNS = [
    r'[A-Z][A-Za-z\s\.]+v\.\s*[A-Z][A-Za-z\s\.]+,\s*(?:\(\d{4}\)\s*\d+\s*SCC\s*\d+|AIR\s*\d{4}\s*SC\s*\d+)',
    r'[A-Z][A-Za-z\s\.]+vs\.?\s*[A-Z][A-Za-z\s\.]+\s+on\s+\d+\s+\w+,\s*\d{4}',
]

AMOUNT_PATTERNS = [
    # Comma-formatted: Rs.2,000/- or Rs.1,00,000  (capital Rs only)
    r'Rs\.?\s*\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?(?:/-)?',
    # 4+ digits: Rs.5000 or Rs.50000
    r'Rs\.?\s*\d{4,}(?:\.\d{1,2})?(?:/-)?',
    # With unit: Rs.5 lakhs / Rs.2 crores
    r'Rs\.?\s*\d+(?:\.\d{2})?\s*(?:lakhs?|crores?)',
    r'₹\s*\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?',
    r'₹\s*\d{4,}',
    r'INR\s+\d{4,}',
    # Pay scale: Rs. 210-270 or Rs.260-400 — capital Rs, 3-digit ranges only
    r'Rs\.?\s*\d{3,4}-\d{3,4}\b',
]

DATE_PATTERNS = [
    # 22 February, 1982 or 1st January, 1973
    r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|'
    r'July|August|September|October|November|December),?\s+\d{4}\b',
    # DD/MM/YYYY only — NOT DD-MM-YYYY (avoids matching pay scale ranges like 8-350)
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    # Month DD, YYYY: February 22, 1982
    r'\b(?:January|February|March|April|May|June|July|August|September|'
    r'October|November|December)\s+\d{1,2},?\s+\d{4}\b',
    # ISO: 2024-03-12
    r'\b20\d{2}-\d{2}-\d{2}\b',
]


def extract_entities(text: str) -> Dict:
    # Strip digital signature blocks before NLP
    text = re.sub(
        r'Digitally\s+[Ss]igned\s+by\s+.{0,80}?(?=\n|\Z)',
        '', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'Signature\s+Not\s+Verified.{0,300}?(?=\n\n|\Z)',
        '', text, flags=re.IGNORECASE | re.DOTALL
    )

    nlp = get_nlp()
    doc = nlp(text[:100000])

    # ── spaCy NER ─────────────────────────────────────────────────────────────
    persons, seen_p = [], set()
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text.strip()
            if not _is_person_noise(name):
                # Normalize for dedup: lowercase, collapse spaces
                norm = re.sub(r'\s+', ' ', name.lower())
                # Check if this name is a substring of an already-seen name (O. CHINNAPPA vs O. Chinnappa Reddy)
                already_covered = any(
                    norm in seen or seen in norm
                    for seen in seen_p
                )
                if not already_covered:
                    seen_p.add(norm)
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
        "statutes": [],
        "acts_cited": [],
        "cited_cases": [],
        "monetary_amounts": [],
        "key_dates": [],
    }

    for p in CASE_NUMBER_PATTERNS:
        results["case_numbers"].extend(re.findall(p, text, re.IGNORECASE))

    for p in IPC_SECTION_PATTERNS:
        results["ipc_sections"].extend(re.findall(p, text, re.IGNORECASE))

    for p in STATUTE_PATTERNS:
        results["statutes"].extend(re.findall(p, text))  # no IGNORECASE — must be capitalised

    for p in ACT_PATTERNS:
        results["acts_cited"].extend(re.findall(p, text))  # no IGNORECASE — act names are capitalised

    for p in CITED_CASE_PATTERNS:
        results["cited_cases"].extend(re.findall(p, text, re.IGNORECASE))

    for p in AMOUNT_PATTERNS[:6]:  # Rs. and ₹ patterns — no IGNORECASE (Rs must be capital)
        results["monetary_amounts"].extend(re.findall(p, text))
    # Pay scale pattern separately
    results["monetary_amounts"].extend(re.findall(AMOUNT_PATTERNS[6], text))

    for p in DATE_PATTERNS:
        results["key_dates"].extend(re.findall(p, text, re.IGNORECASE))

    # ── Deduplicate (prefix-aware) ────────────────────────────────────────────
    for key in results:
        if not isinstance(results[key], list):
            continue
        seen_norms, cleaned_list = set(), []
        for item in results[key]:
            item = item.strip()
            if not item or len(item) <= 2:
                continue
            norm = _normalize(item)

            # For statutes: normalize Art./Article so Art. 32 == Article 32
            if key == "statutes":
                norm = re.sub(r'\bart\.?\s+', 'article ', norm)
                norm = re.sub(r'\s+', ' ', norm).strip()

            # For amounts: normalize Rs./Rs so Rs. 210-270 == Rs.210-270
            if key == "monetary_amounts":
                norm = re.sub(r'rs\.?\s*', 'rs ', norm).strip()

            if any(norm[:28] == s[:28] for s in seen_norms):
                continue
            seen_norms.add(norm)
            cleaned_list.append(item)
            if len(cleaned_list) >= 6:
                break
        results[key] = cleaned_list

    return results


def extract_judgment_outcome(text: str) -> str:
    text_lower = text.lower()
    patterns = [
        (r'\bappeals?\s+(?:stand[s]?\s+)?dismissed\b',   "Appeal Dismissed ❌"),
        (r'\bappeal\s+is\s+(?:hereby\s+)?allowed\b',      "Appeal Allowed ✅"),
        (r'\bappeals?\s+(?:are\s+|hereby\s+)?allowed\b',  "Appeal Allowed ✅"),
        (r'\bpetition\s+is\s+(?:hereby\s+)?allowed\b',    "Petition Allowed ✅"),
        (r'\bpetition\s+(?:stand[s]?\s+)?dismissed\b',    "Petition Dismissed ❌"),
        (r'\bsuit\s+(?:is\s+|stand[s]?\s+)?dismissed\b',  "Suit Dismissed ❌"),
        (r'\bmatter\s+is\s+remanded\b',                    "Remanded to Lower Court 🔄"),
        (r'\bremanded\s+back\b',                           "Remanded to Lower Court 🔄"),
        (r'\bconviction\s+(?:is\s+)?set\s+aside\b',       "Conviction Set Aside ✅"),
        (r'\bconviction\s+upheld\b',                       "Conviction Upheld ❌"),
        (r'\bpartly\s+allowed\b',                          "Partly Allowed ⚖️"),
        (r'\bpetition\s+allowed\b',                        "Petition Allowed ✅"),
        (r'\bsettled\b',                                   "Settled 🤝"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, text_lower):
            return label
    return "Outcome unclear — check judgment order"