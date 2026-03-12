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

## Why This Matters

Imagine you are a daily-wage driver in Delhi. You fought a case for 5 years. The judgment finally arrives — 40 pages of English you cannot read. You don't know if you won. You don't know what to do next. You don't know you have 90 days to appeal before the deadline closes forever.

**This is not a rare situation. It happens every day across India.**

- 80% of Indians cannot afford a lawyer for follow-up consultations
- Most High Court and Supreme Court judgments are written for lawyers, not for the people they affect
- Missing an appeal deadline because you didn't understand the judgment is a tragedy that CourtMitra can prevent

CourtMitra does in 10 seconds what would otherwise cost ₹2,000–5,000 and a trip to a lawyer's office:
- Tells you in plain Hindi or English what the judgment means for you
- Tells you exactly what to do next and by when
- Explains every hard legal term in simple language
- Shows you the judge's reasoning step by step so you can understand *why* the decision was made

**The law is written for everyone. CourtMitra makes sure everyone can actually read it.**

---

## What It Does

Upload any Supreme Court or High Court judgment PDF and get:

| Feature | What you see |
|---|---|
| **📋 Plain Summary** | 4 sentences anyone can understand, using real names from the case |
| **🗂️ Legal Entities** | Statutes, articles, acts, case numbers, amounts, dates — extracted without AI hallucination |
| **🔗 Reasoning Chain** | Visual step-by-step flowchart of how the judge arrived at the decision |
| **🔍 Similar Cases** | Other judgments in your database that are structurally similar |
| **💬 Q&A** | Ask any question — answers come only from the document, no hallucination |
| **🛡️ Your Rights** | Appeal deadline countdown, fundamental rights involved, AI fairness score (0–100) |
| **📖 Glossary** | Hard legal terms from this specific judgment explained in plain English + 15 common Indian legal terms always available |
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
```

### Step 3 — Add your API keys
Copy `.env.example` to `.env` and fill in your keys:
```
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here   # optional but recommended as fallback
```

| Key | Where to get it | Cost |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | Free, 2 minutes, no credit card |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) | Free, 15 req/min, 1M tokens/day |

### Step 4 — Run
```bash
streamlit run app.py
```

### Pre-download embedding model (do this at home, not on hackathon WiFi)
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

---

## Project Structure

```
CourtMitra/
├── app.py                      # Main Streamlit app (7 tabs)
├── requirements.txt
├── packages.txt                # Streamlit Cloud system deps
├── .env.example                # Template for API keys
│
├── core/
│   ├── pdf_extractor.py        # Extracts and cleans text from PDF using PyMuPDF
│   ├── chunker.py              # Splits judgment by legal sections (FACTS/ISSUES/ORDER)
│   ├── embedder.py             # Embeds chunks into ChromaDB vector store locally
│   ├── entity_extractor.py     # Extracts statutes, acts, articles, amounts using spaCy + regex
│   ├── llm_handler.py          # Groq + Gemini API calls with 4-model fallback chain
│   ├── flowchart.py            # Builds visual reasoning flowchart HTML
│   ├── citizen_analysis.py     # Appeal deadlines, fundamental rights, fairness assessment
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
 │   (statutes, articles, acts, case numbers, amounts, dates)
 │   — zero LLM involvement, zero hallucination possible
 │
 ├─► Semantic search retrieves top relevant chunks for each query
 │
 └─► LLM receives ONLY retrieved chunks + prompt
     → outputs summary, reasoning steps, answers
     (LLM never sees the full document — can't hallucinate case facts)

     ↓
     Reasoning steps → our line parser → visual HTML flowchart
     Appeal deadline → our rule engine → exact date + court + section
     Fundamental rights → our pattern matcher → Article explanations
```

**The LLM touches ~20% of the pipeline. We built the other 80%.**

### AI Fallback Chain — Zero Downtime
```
Groq llama-3.3-70b → Groq llama-3.1-8b → Groq gemma2-9b → Groq mixtral-8x7b → Google Gemini 1.5 Flash
```
If any model hits a rate limit, the next one is tried automatically. All free tier.

---

## Tech Stack — Total Cost ₹0

| Tool | Purpose | Cost |
|---|---|---|
| Groq (llama-3.3-70b + 3 fallbacks) | Primary LLM | Free tier |
| Google Gemini 1.5 Flash | Final LLM fallback | Free (15 rpm, 1M tokens/day) |
| sentence-transformers/all-MiniLM-L6-v2 | Local embeddings | Free, runs locally |
| ChromaDB | Vector database | Free, local |
| spaCy en_core_web_sm | Legal NER | Free, local |
| PyMuPDF | PDF text extraction | Free |
| deep-translator | Hindi translation | Free |
| Streamlit | Frontend + hosting | Free |

---

## Supported Documents

Works best with:
- Supreme Court of India judgments
- High Court judgments  
- District Court orders
- Consumer forum rulings
- Labour tribunal orders
- Service matter judgments (CAT, Administrative Tribunals)

Download free PDFs from:
- [indiankanoon.org](https://indiankanoon.org) — largest free Indian case law database
- [sci.gov.in/judgments](https://sci.gov.in/judgments) — Supreme Court official
- [scholar.google.com](https://scholar.google.com) → Case law tab

---

## What Makes It Different

Most "legal AI" at hackathons is just `ChatGPT.summarize(pdf)`. CourtMitra has 7 tabs of genuinely distinct functionality:

- **No hallucination on facts** — entities extracted by regex/spaCy, Q&A grounded by RAG
- **Visual reasoning flowchart** — LLM writes plain sentences, our parser builds the graph
- **Appeal deadline calculator** — real Indian legal deadlines (CPC, CrPC, Article 136) with correct court and section
- **Fundamental rights explainer** — Articles 14, 19, 21, 22, 32, 226 detected and explained in plain language
- **Fairness score (0–100)** — procedural red flag detection with HIGH/MEDIUM/LOW severity
- **Cross-case similarity** — semantic search across your entire indexed case library
- **Legal glossary** — case-specific hard terms explained + 15 common Indian legal terms always available

---

## SDG Alignment

- **SDG 16** — Peace, Justice and Strong Institutions: making judgments accessible to all citizens
- **SDG 10** — Reduced Inequalities: removing the knowledge gap between lawyers and ordinary people
- **SDG 4** — Quality Education: teaching people what their constitutional rights actually mean

---

## Built For

**Innovate Bharat Hackathon 2026**  
Sharda School of Computing Science & Engineering, Greater Noida  
Track: AI & Intelligent Systems (AIIS)

---

> ⚠️ CourtMitra is for informational purposes only and does not constitute legal advice. Always consult a qualified lawyer for advice specific to your situation.