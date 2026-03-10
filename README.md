# ⚖️ CourtMitra
### AI Legal Companion for Every Indian

> *Upload any court judgment PDF. Get a plain-language explanation in seconds.*

**Live Demo:** [courtmitra.streamlit.app](https://courtmitra.streamlit.app)

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://courtmitra.streamlit.app)

---

## What is CourtMitra?

India has 5 crore pending court cases. When a judgment comes out — even one that affects someone's land, job, or custody — it's written in dense legal English, 50–200 pages long, full of Latin phrases and case citations that nobody understands.

A first-generation litigant has two options:
- Pay ₹5,000+ for a lawyer to explain it
- Understand nothing and miss their next step deadline

**CourtMitra is option 3.** Free, instant, in their language.

---

## What It Does

Upload any Supreme Court or High Court judgment PDF and get:

| Feature | What you see |
|---|---|
| **📋 Plain Summary** | 3–4 sentences anyone can understand, using real names |
| **🗂️ Legal Entities** | Acts cited, IPC sections, case numbers, amounts, dates — extracted without AI |
| **🔗 Reasoning Chain** | Visual flowchart of how the judge arrived at the decision |
| **🔍 Similar Cases** | Other judgments in your database that are structurally similar |
| **💬 Q&A** | Ask any question — answers come only from the document, no hallucination |
| **🛡️ Your Rights** | Appeal deadline countdown, fundamental rights involved, AI fairness score (0–100) |
| **🌐 Hindi Output** | Toggle the entire output to Hindi |

---

## How to Run Locally

### Step 1 — Clone the repo
```bash
git clone https://github.com/RAK2315/CourtMitra.git
cd CourtMitra
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Step 3 — Add your API key
Create a `.env` file in the root folder:
```
GROQ_API_KEY=your_key_here
```
Get a free key at [console.groq.com](https://console.groq.com) — takes 2 minutes, no credit card.

### Step 4 — Run
```bash
streamlit run app.py
```

---

## Project Structure

```
CourtMitra/
├── app.py                      # Main Streamlit app
├── requirements.txt
├── packages.txt                # Streamlit Cloud system deps
├── .env.example                # Template for API key
│
├── core/
│   ├── pdf_extractor.py        # Extracts text from PDF using PyMuPDF
│   ├── chunker.py              # Splits judgment by legal sections (FACTS/ISSUES/ORDER)
│   ├── embedder.py             # Embeds chunks into ChromaDB vector store
│   ├── entity_extractor.py     # Extracts IPC sections, acts, dates using spaCy + regex
│   ├── llm_handler.py          # Calls Groq API for summary, reasoning chain, Q&A
│   ├── flowchart.py            # Builds visual reasoning flowchart from LLM output
│   └── translator.py           # Translates output to Hindi
│
├── pages/
│   └── 2_About.py              # About page explaining architecture
│
└── static/
    └── style.css               # Custom dark legal UI theme
```

---

## Architecture — Why This Is Not an API Wrapper

Most "legal AI" projects at hackathons are just `ChatGPT.summarize(pdf)`. CourtMitra is different:

```
PDF
 │
 ├─► PyMuPDF extracts raw text
 │
 ├─► Legal-aware chunker splits by section headers
 │   (FACTS / ISSUES / ARGUMENTS / JUDGMENT / ORDER)
 │   — NOT generic 500-token windows
 │
 ├─► sentence-transformers embeds chunks locally
 │   → stored in ChromaDB (runs on your machine, free)
 │
 ├─► spaCy + regex extracts legal entities
 │   (IPC sections, acts, case numbers, amounts, dates)
 │   — zero LLM involvement here, zero hallucination possible
 │
 ├─► Semantic search retrieves top relevant chunks
 │
 └─► Groq LLM receives ONLY retrieved chunks + prompt
     → outputs summary, reasoning steps, answers
     (LLM never sees full document, can't hallucinate case facts)

     ↓
     Reasoning steps → our graph code → visual flowchart
     (GPT alone cannot produce this)
```

**The LLM touches ~20% of the pipeline. We built the other 80%.**

---

## Tech Stack — Total Cost ₹0

| Tool | Purpose |
|---|---|
| Groq (llama-3.3-70b) | LLM — free tier, extremely fast |
| sentence-transformers | Local embeddings — runs on your machine |
| ChromaDB | Vector database — local, no cloud needed |
| spaCy | Legal NER — local |
| PyMuPDF | PDF text extraction |
| deep-translator | Hindi translation — free |
| Streamlit | Frontend |

---

## Supported Documents

Works best with:
- Supreme Court of India judgments
- High Court judgments
- District Court orders
- Consumer forum rulings
- Labour tribunal orders

Download free PDFs from:
- [scholar.google.com](https://scholar.google.com) → Case law tab
- [sci.gov.in/judgments](https://sci.gov.in/judgments)

---

## What Makes It Different

Most "legal AI" at hackathons is just `ChatGPT.summarize(pdf)`. CourtMitra has 6 tabs of genuinely distinct functionality:

- **No hallucination on facts** — entities extracted by regex, Q&A grounded by RAG
- **Visual reasoning flowchart** — requires our graph construction code, not just a prompt
- **Appeal deadline calculator** — real legal deadlines with the correct court and section of law
- **Fundamental rights explainer** — Articles 14, 19, 21, 22, 32 detected and explained in plain language
- **Fairness score (0–100)** — procedural red flag detection with HIGH/MEDIUM/LOW severity
- **Cross-case similarity** — semantic search across your entire indexed case library

---

## SDG Alignment

- **SDG 16** — Peace, Justice and Strong Institutions
- **SDG 10** — Reduced Inequalities
- **SDG 4** — Quality Education

---

## Built For

**Innovate Bharat Hackathon 2026**
Sharda School of Computing Science & Engineering, Greater Noida
Track: AI & Intelligent Systems (AIIS)

---

> ⚠️ CourtMitra is for informational purposes only and does not constitute legal advice. Always consult a qualified lawyer for advice specific to your situation.