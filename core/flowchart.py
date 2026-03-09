from typing import List, Dict

# Color mapping for node types
TYPE_COLORS = {
    "fact":     ("📋", "#1e3a5f", "#4a9eff"),
    "issue":    ("⚖️",  "#3d1f5f", "#a855f7"),
    "argument": ("💬", "#1f3d2f", "#22c55e"),
    "law":      ("📜", "#3d2f1f", "#f59e0b"),
    "decision": ("🏛️", "#3d1f1f", "#ef4444"),
}


def build_mermaid_flowchart(reasoning_steps: List[Dict]) -> str:
    """
    Generate a Mermaid flowchart string from reasoning steps.
    """
    lines = ["flowchart TD"]
    lines.append("    classDef fact fill:#1e3a5f,stroke:#4a9eff,color:#e0f0ff,stroke-width:2px")
    lines.append("    classDef issue fill:#3d1f5f,stroke:#a855f7,color:#f0e0ff,stroke-width:2px")
    lines.append("    classDef argument fill:#1f3d2f,stroke:#22c55e,color:#e0ffe8,stroke-width:2px")
    lines.append("    classDef law fill:#3d2f1f,stroke:#f59e0b,color:#fff8e0,stroke-width:2px")
    lines.append("    classDef decision fill:#5f1f1f,stroke:#ef4444,color:#ffe0e0,stroke-width:3px")
    lines.append("")

    for i, step in enumerate(reasoning_steps):
        node_id = f"S{i}"
        step_type = step.get("type", "fact")
        emoji, _, _ = TYPE_COLORS.get(step_type, ("📌", "#333", "#fff"))
        label = step.get("label", f"Step {i+1}")
        detail = step.get("detail", "")

        # Escape quotes in label
        label_clean = label.replace('"', "'")
        detail_clean = detail.replace('"', "'")[:80]

        lines.append(f'    {node_id}["{emoji} {label_clean}<br/><small>{detail_clean}</small>"]')
        lines.append(f'    class {node_id} {step_type}')

        if i > 0:
            lines.append(f"    S{i-1} --> {node_id}")

    return "\n".join(lines)


def build_html_flowchart(reasoning_steps: List[Dict]) -> str:
    """
    Build an HTML+CSS flowchart for Streamlit rendering.
    More visually controlled than Mermaid.
    """
    cards = []
    for i, step in enumerate(reasoning_steps):
        step_type = step.get("type", "fact")
        emoji, bg_color, border_color = TYPE_COLORS.get(step_type, ("📌", "#1a1a2e", "#888"))
        label = step.get("label", f"Step {i+1}")
        detail = step.get("detail", "")
        type_label = step_type.upper()

        arrow = "" if i == len(reasoning_steps) - 1 else f"""
        <div style="text-align:center;color:#555;font-size:24px;margin:4px 0;">▼</div>
        """

        card = f"""
        <div style="
            background:{bg_color};
            border:2px solid {border_color};
            border-radius:12px;
            padding:16px 20px;
            margin:4px 0;
            position:relative;
        ">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                <span style="font-size:20px;">{emoji}</span>
                <span style="
                    background:{border_color};
                    color:#000;
                    font-size:10px;
                    font-weight:700;
                    padding:2px 8px;
                    border-radius:20px;
                    letter-spacing:1px;
                ">{type_label}</span>
                <span style="font-size:15px;font-weight:700;color:#fff;">{label}</span>
            </div>
            <div style="color:#ccc;font-size:13px;line-height:1.5;padding-left:30px;">{detail}</div>
        </div>
        {arrow}
        """
        cards.append(card)

    legend_items = "".join([
        f'<span style="background:{c[1]};border:1px solid {c[2]};color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;margin:2px;">{c[0]} {k.capitalize()}</span>'
        for k, c in TYPE_COLORS.items()
    ])

    html = f"""
    <div style="font-family:'Courier New',monospace;">
        <div style="margin-bottom:12px;display:flex;flex-wrap:wrap;gap:6px;">
            {legend_items}
        </div>
        {"".join(cards)}
    </div>
    """
    return html
