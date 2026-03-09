# ⚖️ CourtMitra — AI Legal Companion for Every Indian

> *Justice, Explained Simply*

CourtMitra makes Indian court judgments understandable to ordinary citizens.
Upload any Supreme Court or High Court judgment PDF and get:

- **Plain-language summary** anyone can understand
- **Legal entity extraction** — acts, IPC sections, amounts, dates
- **Visual reasoning flowchart** — how the judge arrived at the decision
- **Similar case finder** — from your indexed document library
- **Q&A** — ask any question about the judgment

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
bash setup.sh
```

### 2. Set your API key
```bash
cp .env.example .env
# Edit .env and add your Groq API key (free at console.groq.com)
```

### 3. Run
```bash
streamlit run app.py
```

---

## 🏗️ Architecture

```
PDF Upload
    │
    ▼
PyMuPDF Extraction  →  Legal-Aware Chunker
    │
    ▼
sentence-transformers Embeddings  →  ChromaDB Vector Store
    │
    ▼
spaCy Entity Extractor  (IPC sections, acts, amounts, dates)
    │
    ▼
Groq LLM (llama3-70b)  ←  Retrieved chunks (NOT full text)
    │
    ├──► Plain Language Summary
    ├──► Reasoning Chain → HTML Flowchart
    └──► Q&A Engine
```

**The LLM is just one organ. The retrieval, extraction, and graph logic is our code.**

---

## 📁 Project Structure

```
courtmitra/
├── app.py                  # Streamlit UI
├── requirements.txt
├── setup.sh
├── .env.example
├── core/
│   ├── pdf_extractor.py    # PyMuPDF text extraction
│   ├── chunker.py          # Legal-aware section splitter
│   ├── embedder.py         # ChromaDB + sentence-transformers
│   ├── entity_extractor.py # spaCy + regex legal NER
│   ├── llm_handler.py      # Groq API (summarize, reasoning, Q&A)
│   ├── flowchart.py        # Reasoning chain HTML renderer
│   └── translator.py       # Hindi translation
├── static/
│   └── style.css           # Custom dark legal UI
├── data/sample_pdfs/       # Pre-load judgment PDFs here
└── vectorstore/            # ChromaDB persists here (auto-created)
```

---

## 🆓 All Free APIs & Tools

| Tool | Purpose | Cost |
|------|---------|------|
| Groq (llama3-70b) | LLM backbone | Free tier |
| sentence-transformers | Local embeddings | Free (local) |
| ChromaDB | Vector database | Free (local) |
| spaCy | NLP entity extraction | Free (local) |
| deep-translator | Hindi translation | Free |
| PyMuPDF | PDF extraction | Free |

**Total API cost: ₹0**

---

## 🎯 SDG Alignment

- **SDG 16** — Peace, Justice and Strong Institutions
- **SDG 10** — Reduced Inequalities  
- **SDG 4** — Quality Education

---

## ⚠️ Disclaimer

CourtMitra is for **informational and educational purposes only**.
It does not constitute legal advice. Always consult a qualified lawyer for advice specific to your situation.

---

*Built for Innovate Bharat Hackathon 2026 — Sharda University*
