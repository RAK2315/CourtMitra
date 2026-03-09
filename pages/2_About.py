import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="About — CourtMitra",
    page_icon="⚖️",
    layout="wide",
)

css_path = Path(__file__).parent.parent / "static" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<div class="courtmitra-header">
    <div>
        <div class="courtmitra-logo">⚖️ CourtMitra</div>
        <div class="courtmitra-tagline">AI Legal Companion for Every Indian</div>
    </div>
    <div class="courtmitra-badge">ABOUT THIS PROJECT</div>
</div>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:48px 20px 32px;">
    <div style="font-family:'Playfair Display',serif;font-size:2.6rem;
        color:#c9a84c;line-height:1.3;margin-bottom:16px;">
        Justice Should Not Require<br>a Law Degree
    </div>
    <div style="color:#7a8fa6;font-size:1.05rem;max-width:680px;
        margin:0 auto;line-height:1.9;">
        India has <b style="color:#d4c5a9">5 crore pending court cases</b>.
        When a judgment affects a person's land, custody, job, or freedom —
        it arrives as a 100-page document filled with Latin phrases and citations
        nobody understands. CourtMitra changes that.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Problem ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">The Problem We Solve</div>', unsafe_allow_html=True)
st.markdown("")

col1, col2, col3 = st.columns(3)
problems = [
    ("📄", "Inaccessible Judgments", "Court orders are written in dense legal English. A first-generation litigant cannot understand what happened in their own case."),
    ("💸", "Cost Barrier", "Paying ₹5,000+ just to get a lawyer to explain a judgment is not an option for most Indians."),
    ("⏰", "Missed Deadlines", "Without understanding what a judgment says, people miss appeal windows, compliance dates, and next steps."),
]
for col, (icon, title, desc) in zip([col1, col2, col3], problems):
    with col:
        st.markdown(f"""
        <div style="background:#0d1a2e;border:1px solid #1e3a5f;border-radius:10px;
            padding:24px;min-height:160px;">
            <div style="font-size:2rem;margin-bottom:12px;">{icon}</div>
            <div style="font-family:'Playfair Display',serif;color:#c9a84c;
                font-size:1rem;margin-bottom:8px;">{title}</div>
            <div style="color:#7a8fa6;font-size:13px;line-height:1.6;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ── Architecture ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">How It Works — The Architecture</div>', unsafe_allow_html=True)
st.markdown("<small style='color:#555'>This is NOT an API wrapper. The LLM touches ~20% of the pipeline.</small>", unsafe_allow_html=True)
st.markdown("")

components.html("""
<style>
  body { background:#0a1020; margin:0; padding:16px;
         font-family:'Segoe UI',sans-serif; }
  .row { display:flex; flex-wrap:wrap; gap:12px;
         align-items:center; justify-content:center; margin:6px 0; }
  .node { border-radius:8px; padding:14px 18px; text-align:center; min-width:130px; }
  .arrow { color:#c9a84c; font-size:18px; font-weight:bold; }
  .node-icon { font-size:1.4rem; }
  .node-label { font-size:10px; margin-top:5px; letter-spacing:1px; font-weight:700; }
  .node-sub { font-size:9px; margin-top:3px; color:#7a8fa6; }
  .down { text-align:center; color:#c9a84c; font-size:18px; margin:4px 0; }
  .out { border-radius:8px; padding:10px 14px; text-align:center;
         min-width:110px; background:#0d1a2e; border:1px solid #c9a84c; }
  .out-label { color:#c9a84c; font-size:11px; letter-spacing:1px; }
</style>

<div class="row">
  <div class="node" style="background:#1e3a5f;border:2px solid #4a9eff;">
    <div class="node-icon">📄</div>
    <div class="node-label" style="color:#4a9eff;">PDF UPLOAD</div>
    <div class="node-sub">PyMuPDF</div>
  </div>
  <div class="arrow">→</div>
  <div class="node" style="background:#1f3d2f;border:2px solid #22c55e;">
    <div class="node-icon">✂️</div>
    <div class="node-label" style="color:#22c55e;">LEGAL CHUNKER</div>
    <div class="node-sub">Section-aware splitter</div>
  </div>
  <div class="arrow">→</div>
  <div class="node" style="background:#3d2f1f;border:2px solid #f59e0b;">
    <div class="node-icon">🧠</div>
    <div class="node-label" style="color:#f59e0b;">EMBEDDINGS</div>
    <div class="node-sub">sentence-transformers (local)</div>
  </div>
  <div class="arrow">→</div>
  <div class="node" style="background:#2a1f3d;border:2px solid #a855f7;">
    <div class="node-icon">🗄️</div>
    <div class="node-label" style="color:#a855f7;">VECTOR STORE</div>
    <div class="node-sub">ChromaDB (local)</div>
  </div>
</div>

<div class="down">↓</div>

<div class="row">
  <div class="node" style="background:#1e3a5f;border:2px solid #4a9eff;">
    <div class="node-icon">🔍</div>
    <div class="node-label" style="color:#4a9eff;">ENTITY EXTRACT</div>
    <div class="node-sub">spaCy + regex (no LLM)</div>
  </div>
  <div class="arrow">+</div>
  <div class="node" style="background:#1f3d2f;border:2px solid #22c55e;">
    <div class="node-icon">📡</div>
    <div class="node-label" style="color:#22c55e;">RETRIEVAL</div>
    <div class="node-sub">Semantic search → top chunks</div>
  </div>
  <div class="arrow">→</div>
  <div class="node" style="background:#3d1f1f;border:2px solid #ef4444;">
    <div class="node-icon">🤖</div>
    <div class="node-label" style="color:#ef4444;">LLM (GROQ)</div>
    <div class="node-sub">Only sees retrieved chunks</div>
  </div>
</div>

<div class="down">↓</div>

<div class="row">
  <div class="out"><div class="out-label">📋 SUMMARY</div></div>
  <div class="out"><div class="out-label">🔗 FLOWCHART</div></div>
  <div class="out"><div class="out-label">🔍 SIMILAR CASES</div></div>
  <div class="out"><div class="out-label">💬 Q&amp;A</div></div>
</div>
""", height=380, scrolling=False)

st.markdown("---")

# ── Why not API wrapper ───────────────────────────────────────────────────────
st.markdown('<div class="section-header">Why This Is Not Just an API Wrapper</div>', unsafe_allow_html=True)
st.markdown("")

our_code = [
    ("✂️", "Legal-Aware Chunker", "Splits judgments by actual legal sections (FACTS / ISSUES / JUDGMENT / ORDER) — not generic text windows. Built from scratch."),
    ("🗄️", "Local Vector Database", "Every judgment is embedded and stored in ChromaDB locally. The LLM never sees the full document — only the semantically relevant chunks."),
    ("🔍", "Legal NER Without LLM", "IPC sections, acts, case numbers, amounts, dates — all extracted using spaCy + hand-crafted Indian legal regex. Zero hallucination possible here."),
    ("🔗", "Reasoning Flowchart Engine", "Parses the judge's logical chain and renders it as a visual step-by-step flowchart. GPT alone cannot produce this — it requires our graph construction code."),
    ("📊", "Similar Case Finder", "Cross-document semantic search across your entire indexed case library. Finds structurally similar judgments automatically."),
    ("🌐", "Hindi Output Pipeline", "Full translation pipeline that converts all outputs to Hindi — making justice accessible to non-English speakers across India."),
]

cols = st.columns(2)
for i, (icon, title, desc) in enumerate(our_code):
    with cols[i % 2]:
        st.markdown(f"""
        <div style="background:#0d1a2e;border:1px solid #1e3a5f;
            border-left:4px solid #c9a84c;border-radius:0 8px 8px 0;
            padding:16px 20px;margin:6px 0;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                <span style="font-size:1.3rem;">{icon}</span>
                <span style="font-family:'Playfair Display',serif;color:#c9a84c;
                    font-size:0.95rem;">{title}</span>
            </div>
            <div style="color:#7a8fa6;font-size:13px;line-height:1.6;
                padding-left:32px;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ── Tech Stack ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Tech Stack — Total Cost: ₹0</div>', unsafe_allow_html=True)
st.markdown("")

stack = [
    ("Groq (llama-3.3-70b)", "LLM backbone", "Free tier", "#ef4444"),
    ("sentence-transformers", "Local embeddings", "Free / local", "#22c55e"),
    ("ChromaDB", "Vector database", "Free / local", "#a855f7"),
    ("spaCy", "Legal NER", "Free / local", "#4a9eff"),
    ("PyMuPDF", "PDF extraction", "Free / local", "#f59e0b"),
    ("deep-translator", "Hindi translation", "Free", "#22c55e"),
    ("Streamlit", "Frontend UI", "Free", "#4a9eff"),
]

cols = st.columns(4)
for i, (tool, purpose, cost, color) in enumerate(stack):
    with cols[i % 4]:
        st.markdown(f"""
        <div style="background:#0d1a2e;border:1px solid #1e3a5f;border-radius:8px;
            padding:16px;margin:6px 0;text-align:center;">
            <div style="font-family:'JetBrains Mono',monospace;color:{color};
                font-size:0.75rem;font-weight:700;margin-bottom:6px;">{tool}</div>
            <div style="color:#9ab4cc;font-size:12px;">{purpose}</div>
            <div style="background:{color}22;color:{color};font-size:10px;
                padding:2px 8px;border-radius:10px;margin-top:8px;
                display:inline-block;">{cost}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ── SDGs ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">UN Sustainable Development Goals</div>', unsafe_allow_html=True)
st.markdown("")

sdgs = [
    ("16", "Peace, Justice & Strong Institutions", "Making legal systems accessible to every citizen regardless of income or education.", "#4a9eff"),
    ("10", "Reduced Inequalities", "Bridging the gap between those who can afford legal help and those who cannot.", "#a855f7"),
    ("4",  "Quality Education", "Helping citizens understand their legal rights and the justice system.", "#22c55e"),
]

cols = st.columns(3)
for col, (num, title, desc, color) in zip(cols, sdgs):
    with col:
        st.markdown(f"""
        <div style="background:#0d1a2e;border:2px solid {color};border-radius:10px;
            padding:24px;text-align:center;">
            <div style="font-family:'Playfair Display',serif;font-size:2.5rem;
                color:{color};font-weight:900;margin-bottom:8px;">SDG {num}</div>
            <div style="color:#d4c5a9;font-size:0.9rem;font-weight:600;
                margin-bottom:8px;">{title}</div>
            <div style="color:#7a8fa6;font-size:12px;line-height:1.6;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:32px 20px;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
        color:#555;letter-spacing:3px;margin-bottom:12px;">BUILT FOR</div>
    <div style="font-family:'Playfair Display',serif;font-size:1.4rem;color:#c9a84c;">
        Innovate Bharat Hackathon 2026
    </div>
    <div style="color:#555;font-size:13px;margin-top:6px;">
        Sharda School of Computing Science & Engineering · Greater Noida
    </div>
    <div style="margin-top:20px;font-family:'JetBrains Mono',monospace;
        font-size:0.7rem;color:#333;letter-spacing:2px;">
        TRACK: AI &amp; INTELLIGENT SYSTEMS (AIIS) · SDG 16 · SDG 10 · SDG 4
    </div>
</div>
""", unsafe_allow_html=True)