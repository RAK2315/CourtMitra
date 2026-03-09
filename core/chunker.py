import re
from typing import List, Dict


# Legal section headers commonly found in Indian court judgments
SECTION_PATTERNS = [
    r'(?i)(JUDGMENT|JUDGEMENT)',
    r'(?i)(ORDER)',
    r'(?i)(FACTS\s+OF\s+THE\s+CASE|BRIEF\s+FACTS)',
    r'(?i)(ISSUES?\s+FOR\s+CONSIDERATION|POINTS?\s+FOR\s+DETERMINATION)',
    r'(?i)(ARGUMENTS?\s+ADVANCED|SUBMISSIONS?\s+OF)',
    r'(?i)(ANALYSIS\s+AND\s+FINDINGS?|DISCUSSION)',
    r'(?i)(CONCLUSION)',
    r'(?i)(OPERATIVE\s+ORDER|DIRECTIONS?)',
    r'(?i)(BACKGROUND)',
    r'(?i)(HELD\s*:)',
]


def split_into_legal_sections(text: str) -> List[Dict]:
    """
    Split text into legal sections based on common judgment structure.
    Returns list of dicts with 'section', 'content', 'index'.
    """
    sections = []
    lines = text.split('\n')

    current_section = "PREAMBLE"
    current_content = []
    section_index = 0

    for line in lines:
        matched = False
        for pattern in SECTION_PATTERNS:
            if re.search(pattern, line.strip()):
                # Save previous section
                if current_content:
                    sections.append({
                        "section": current_section,
                        "content": "\n".join(current_content).strip(),
                        "index": section_index,
                    })
                    section_index += 1
                current_section = line.strip()[:60]
                current_content = []
                matched = True
                break
        if not matched:
            current_content.append(line)

    # Add final section
    if current_content:
        sections.append({
            "section": current_section,
            "content": "\n".join(current_content).strip(),
            "index": section_index,
        })

    return [s for s in sections if len(s["content"]) > 100]


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Chunk text into overlapping windows for embedding.
    Used when legal section splitting doesn't yield clean results.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def smart_chunk(text: str) -> List[Dict]:
    """
    Try legal section splitting first.
    Fall back to sliding window if not enough sections found.
    """
    sections = split_into_legal_sections(text)

    if len(sections) >= 3:
        # Legal sections found — use them
        result = []
        for sec in sections:
            # If a section is too long, sub-chunk it
            if len(sec["content"].split()) > 900:
                sub_chunks = chunk_text(sec["content"], chunk_size=800, overlap=100)
                for j, sc in enumerate(sub_chunks):
                    result.append({
                        "section": f"{sec['section']} (part {j+1})",
                        "content": sc,
                        "index": sec["index"],
                    })
            else:
                result.append(sec)
        return result
    else:
        # Fallback to sliding window
        chunks = chunk_text(text)
        return [{"section": f"Chunk {i}", "content": c, "index": i}
                for i, c in enumerate(chunks)]
