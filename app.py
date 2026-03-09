import streamlit as st
import os
import tempfile
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CourtMitra — AI Legal Companion",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load CSS ─────────────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "static" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Imports after page config ─────────────────────────────────────────────────
from core.pdf_extractor import extract_text_from_pdf, clean_text
from core.chunker import smart_chunk
from core.embedder import embed_chunks, retrieve_similar, find_similar_cases, list_indexed_documents
from core.entity_extractor import extract_entities, extract_judgment_outcome
from core.llm_handler import summarize_judgment, build_reasoning_chain, answer_question
from core.flowchart import build_html_flowchart

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="courtmitra-header">
    <div>
        <div class="courtmitra-logo">⚖️ CourtMitra</div>
        <div class="courtmitra-tagline">AI Legal Companion for Every Indian</div>
    </div>
    <div class="courtmitra-badge">POWERED BY RAG + LLM</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗂️ Settings")

    if not os.getenv("GROQ_API_KEY"):
        st.markdown("""
        <div style='background:#1a0a00;border:1px solid #c9a84c;border-radius:6px;
            padding:10px 12px;font-size:12px;color:#c9a84c;margin-bottom:12px;'>
            ⚠️ Add <b>GROQ_API_KEY</b> to your <b>.env</b> file to begin.
        </div>
        """, unsafe_allow_html=True)

    language = st.selectbox("Output Language", ["English", "Hindi"])

    st.markdown("---")
    st.markdown("### 📚 Indexed Cases")
    indexed = list_indexed_documents()
    if indexed:
        for doc in indexed:
            st.markdown(f"<small>📄 {doc}</small>", unsafe_allow_html=True)
    else:
        st.markdown("<small style='color:#555'>No cases indexed yet</small>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:11px;color:#555;line-height:1.6'>
    <b style='color:#c9a84c'>How it works:</b><br>
    1. Upload a court judgment PDF<br>
    2. AI extracts & indexes content<br>
    3. Get plain-language summary<br>
    4. See judge's reasoning visually<br>
    5. Find similar past cases<br><br>
    <b style='color:#c9a84c'>⚠️ Disclaimer:</b><br>
    CourtMitra is for informational purposes only. Always consult a qualified lawyer for legal advice.
    </div>
    """, unsafe_allow_html=True)

# ── Main Area ─────────────────────────────────────────────────────────────────
if not os.getenv("GROQ_API_KEY"):
    st.markdown("""
    <div class="warning-box">
    ⚠️ <b>Groq API Key Required</b> — Add <code>GROQ_API_KEY=your_key</code> to your <b>.env</b> file and restart the app.
    Get a free key at <a href="https://console.groq.com" style="color:#c9a84c">console.groq.com</a>
    </div>
    """, unsafe_allow_html=True)

# ── File Upload ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📄 Upload Court Judgment</div>', unsafe_allow_html=True)

col_upload, col_info = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader(
        "Upload a Supreme Court / High Court judgment PDF",
        type=["pdf"],
        help="Indian court judgment PDFs from indiankanoon.org or sci.gov.in work best"
    )

with col_info:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">Supported Sources</div>
        <div style="font-size:13px;color:#9ab4cc;margin-top:6px;">
        📌 Supreme Court of India<br>
        📌 High Courts<br>
        📌 District Courts<br>
        📌 Consumer Forums<br>
        📌 Labour Tribunals
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Process ───────────────────────────────────────────────────────────────────
if uploaded_file and os.getenv("GROQ_API_KEY"):

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    doc_name = uploaded_file.name.replace(".pdf", "")

    # ── Processing Pipeline ──
    with st.spinner("🔍 Extracting and analyzing judgment..."):
        
        # Step 1: Extract
        raw_text = extract_text_from_pdf(tmp_path)
        text = clean_text(raw_text)

        # Step 2: Chunk
        chunks = smart_chunk(text)

        # Step 3: Embed & Store
        embed_chunks(chunks, doc_name)

        # Step 4: Retrieve top chunks for analysis
        top_chunks = retrieve_similar(
            "facts issues judgment order decision held",
            top_k=6,
            doc_name=doc_name
        )
        if not top_chunks:
            top_chunks = [{"section": c["section"], "content": c["content"]} for c in chunks[:6]]

        # Step 5: Extract entities
        entities = extract_entities(text)
        outcome = extract_judgment_outcome(text)

    st.success(f"✅ Indexed {len(chunks)} sections from **{doc_name}**")
    st.markdown("---")

    # ── Stats Row ─────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Pages Processed</div>
            <div class="stat-value">{len(raw_text)//2000 + 1}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Sections Found</div>
            <div class="stat-value">{len(chunks)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        acts_count = len(entities.get("acts_cited", []))
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Acts Cited</div>
            <div class="stat-value">{acts_count}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        outcome_class = (
            "outcome-allowed" if "Allowed" in outcome
            else "outcome-dismissed" if "Dismissed" in outcome
            else "outcome-other"
        )
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Outcome</div>
            <div style="margin-top:6px">
                <span class="{outcome_class}" style="font-size:12px;padding:4px 10px">{outcome}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Summary", "🗂️ Entities", "🔗 Reasoning Chain", "🔍 Similar Cases", "💬 Ask a Question"
    ])

    # ── TAB 1: Summary ────────────────────────────────────────────────────────
    with tab1:
        st.markdown('<div class="section-header">Plain Language Summary</div>', unsafe_allow_html=True)

        with st.spinner("Generating summary..."):
            summary = summarize_judgment(top_chunks, entities, language)

        # Case type badge
        case_type = summary.get("case_type", "Unknown")
        st.markdown(f"""
        <div style="margin-bottom:16px;">
            <span style="background:#1e3a5f;color:#4a9eff;font-size:12px;font-weight:700;
                padding:4px 14px;border-radius:20px;letter-spacing:1px;">
                {case_type} Case
            </span>
        </div>
        """, unsafe_allow_html=True)

        # Summary card
        plain_summary = summary.get("plain_summary", "")
        st.markdown(f"""
        <div class="summary-card">
            <div style="font-family:'Playfair Display',serif;font-size:1.05rem;
                line-height:1.8;color:#d4c5a9;">
                {plain_summary}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_issues, col_steps = st.columns(2)

        with col_issues:
            st.markdown('<div class="section-header" style="font-size:1rem;">⚖️ Key Issues</div>', unsafe_allow_html=True)
            for issue in summary.get("key_issues", []):
                st.markdown(f"""
                <div style="background:#0d1a2e;border-left:3px solid #a855f7;
                    padding:10px 14px;margin:6px 0;border-radius:0 6px 6px 0;
                    font-size:13px;color:#d4c5a9;">
                    {issue}
                </div>
                """, unsafe_allow_html=True)

        with col_steps:
            st.markdown('<div class="section-header" style="font-size:1rem;">🚶 What To Do Next</div>', unsafe_allow_html=True)
            for i, step in enumerate(summary.get("next_steps", []), 1):
                st.markdown(f"""
                <div style="background:#0d1a2e;border-left:3px solid #22c55e;
                    padding:10px 14px;margin:6px 0;border-radius:0 6px 6px 0;
                    font-size:13px;color:#d4c5a9;">
                    <span class="step-badge">{i}</span>{step}
                </div>
                """, unsafe_allow_html=True)

        # Court decision
        decided = summary.get("what_court_decided", "")
        if decided:
            st.markdown(f"""
            <div style="background:#0a1628;border:2px solid #c9a84c;border-radius:8px;
                padding:16px 20px;margin:16px 0;text-align:center;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;
                    color:#7a8fa6;letter-spacing:2px;margin-bottom:8px;">COURT DECIDED</div>
                <div style="font-family:'Playfair Display',serif;font-size:1.1rem;
                    color:#c9a84c;">{decided}</div>
            </div>
            """, unsafe_allow_html=True)

        # Warning
        warning = summary.get("important_warning", "")
        if warning:
            st.markdown(f'<div class="warning-box">⚠️ {warning}</div>', unsafe_allow_html=True)

    # ── TAB 2: Entities ───────────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="section-header">Extracted Legal Entities</div>', unsafe_allow_html=True)
        st.markdown("<small style='color:#555'>Automatically extracted using NLP — no AI hallucination, direct pattern matching</small>", unsafe_allow_html=True)
        st.markdown("")

        entity_config = [
            ("case_numbers",      "📁 Case Numbers",      "#4a9eff"),
            ("acts_cited",        "📜 Acts Cited",        "#f59e0b"),
            ("ipc_sections",      "⚖️ IPC / Sections",    "#a855f7"),
            ("monetary_amounts",  "💰 Amounts",           "#22c55e"),
            ("key_dates",         "📅 Key Dates",         "#ef4444"),
            ("persons_mentioned", "👤 Persons",           "#9ab4cc"),
            ("organizations",     "🏛️ Organizations",     "#c9a84c"),
        ]

        cols = st.columns(2)
        for i, (key, label, color) in enumerate(entity_config):
            items = entities.get(key, [])
            with cols[i % 2]:
                pills = " ".join([
                    f'<span class="entity-pill" style="border-color:{color};color:{color}">{item}</span>'
                    for item in items
                ]) if items else f'<span style="color:#555;font-size:12px">None detected</span>'

                st.markdown(f"""
                <div style="background:#0d1a2e;border:1px solid #1e3a5f;border-radius:8px;
                    padding:14px;margin:6px 0;">
                    <div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7rem;
                        color:{color};letter-spacing:2px;margin-bottom:8px;">{label}</div>
                    <div>{pills}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 3: Reasoning Chain ────────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="section-header">Judge\'s Reasoning Chain</div>', unsafe_allow_html=True)
        st.markdown("<small style='color:#555'>How the judge arrived at the decision — step by step</small>", unsafe_allow_html=True)
        st.markdown("")

        with st.spinner("Building reasoning chain..."):
            reasoning = build_reasoning_chain(top_chunks)

        flowchart_html = build_html_flowchart(reasoning)
        import streamlit.components.v1 as components
        components.html(
            f"""
            <style>
                body {{ background: #080c14; margin: 0; padding: 8px;
                        font-family: 'Segoe UI', sans-serif; }}
            </style>
            {flowchart_html}
            """,
            height=120 + len(reasoning) * 130,
            scrolling=False,
        )

        # Raw reasoning as expandable
        with st.expander("📊 View raw reasoning data (JSON)"):
            st.json(reasoning)

    # ── TAB 4: Similar Cases ──────────────────────────────────────────────────
    with tab4:
        st.markdown('<div class="section-header">Similar Cases in Database</div>', unsafe_allow_html=True)
        st.markdown("<small style='color:#555'>Cases in your local database that are structurally similar to this judgment.</small>", unsafe_allow_html=True)
        st.markdown("")

        summary_text = summary.get("plain_summary", text[:500])
        similar = find_similar_cases(summary_text, exclude_doc=doc_name, top_k=3)

        if similar:
            for case in similar:
                similarity_pct = int(case["similarity"] * 100)
                bar_color = "#c9a84c" if similarity_pct > 70 else "#22c55e"
                display_name = case["doc_name"].replace("_", " ").strip()
                excerpt = case["excerpt"][:220]
                if len(case["excerpt"]) > 220:
                    excerpt = excerpt[:excerpt.rfind(" ")] + "..."
                st.markdown(f"""
                <div class="similar-case-card">
                    <div style="display:flex;justify-content:space-between;
                        align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px;">
                        <span style="font-family:'Playfair Display',serif;
                            color:#d4c5a9;font-size:1rem;">
                            📄 {display_name}
                        </span>
                        <span style="background:{bar_color}22;color:{bar_color};
                            font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                            padding:3px 10px;border-radius:20px;border:1px solid {bar_color};
                            white-space:nowrap;">
                            {similarity_pct}% match
                        </span>
                    </div>
                    <div style="background:#0a1020;border-radius:3px;height:3px;margin-bottom:12px;">
                        <div style="background:{bar_color};width:{similarity_pct}%;
                            height:100%;border-radius:3px;"></div>
                    </div>
                    <div style="font-size:12px;color:#7a8fa6;line-height:1.7;
                        font-style:italic;word-break:break-word;">
                        "{excerpt}"
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:40px;color:#555;">
                <div style="font-size:40px;margin-bottom:12px;">🗃️</div>
                <div>No similar cases in database yet.</div>
                <div style="font-size:12px;margin-top:8px;">
                    Upload more judgment PDFs to build your case library.
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB 5: Q&A ────────────────────────────────────────────────────────────
    with tab5:
        st.markdown('<div class="section-header">Ask About This Judgment</div>', unsafe_allow_html=True)
        st.markdown("<small style='color:#555'>Questions are answered using only content from the uploaded document — no hallucination</small>", unsafe_allow_html=True)
        st.markdown("")

        question = st.text_input(
            "Your question",
            placeholder="e.g. What was the main argument of the appellant? What sections were violated?",
        )

        if st.button("🔍 Get Answer") and question:
            with st.spinner("Retrieving relevant sections and generating answer..."):
                q_chunks = retrieve_similar(question, top_k=4, doc_name=doc_name)
                answer = answer_question(question, q_chunks, language)

            st.markdown(f"""
            <div class="summary-card" style="margin-top:16px;">
                <div style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;
                    color:#c9a84c;letter-spacing:2px;margin-bottom:10px;">ANSWER</div>
                <div style="font-size:1rem;line-height:1.8;color:#d4c5a9;">{answer}</div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("📖 Source sections used"):
                for chunk in q_chunks:
                    st.markdown(f"""
                    <div style="background:#0a1020;border-left:2px solid #2a4a6a;
                        padding:10px 14px;margin:6px 0;font-size:12px;color:#7a8fa6;">
                        <b style='color:#4a9eff'>{chunk.get('section','')}</b><br>
                        {chunk['content'][:400]}...
                    </div>
                    """, unsafe_allow_html=True)

    # Cleanup
    os.unlink(tmp_path)

elif not uploaded_file:
    # Landing state
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;">
        <div style="font-size:72px;margin-bottom:20px;">⚖️</div>
        <div style="font-family:'Playfair Display',serif;font-size:2rem;color:#c9a84c;margin-bottom:12px;">
            Justice, Explained Simply
        </div>
        <div style="color:#7a8fa6;font-size:1rem;max-width:600px;margin:0 auto;line-height:1.8;">
            Upload any Supreme Court or High Court judgment PDF.<br>
            CourtMitra will explain it in plain language, show the judge's reasoning visually,
            and help you understand what to do next.
        </div>
        <div style="margin-top:40px;display:flex;justify-content:center;gap:40px;flex-wrap:wrap;">
            <div style="text-align:center;">
                <div style="font-size:32px;">🔍</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                    color:#555;letter-spacing:2px;margin-top:6px;">EXTRACT</div>
                <div style="font-size:12px;color:#7a8fa6;margin-top:4px;">Legal entities & facts</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:32px;">📋</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                    color:#555;letter-spacing:2px;margin-top:6px;">SUMMARIZE</div>
                <div style="font-size:12px;color:#7a8fa6;margin-top:4px;">In plain language</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:32px;">🔗</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                    color:#555;letter-spacing:2px;margin-top:6px;">VISUALIZE</div>
                <div style="font-size:12px;color:#7a8fa6;margin-top:4px;">Reasoning flowchart</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:32px;">💬</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                    color:#555;letter-spacing:2px;margin-top:6px;">ASK</div>
                <div style="font-size:12px;color:#7a8fa6;margin-top:4px;">Any question about the case</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)