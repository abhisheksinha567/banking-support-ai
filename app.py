"""
app.py — Gradio UI for BankAssist AI (Hugging Face Spaces compatible)
"""

import os
import gradio as gr
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from database import get_all_tickets, get_stats, get_ticket_logs, init_db
from agents import process_customer_message, fetch_ticket_status, resolve_ticket

init_db()

# ── CSS ────────────────────────────────────────────────────────────────────────
custom_css = """
body { background: #0f1117 !important; }

.gradio-container {
    background: #0f1117 !important;
    color: #c9d1d9 !important;
    font-family: 'Inter', sans-serif !important;
    max-width: 1100px !important;
    margin: 0 auto !important;
}

.gr-button-primary {
    background: #1f6feb !important;
    border: none !important;
    color: white !important;
    border-radius: 8px !important;
}

.gr-button {
    border-radius: 8px !important;
}

.gr-input, .gr-textarea, .gr-dropdown {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #c9d1d9 !important;
    border-radius: 8px !important;
}

.gr-panel, .gr-box {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 12px !important;
}

.gr-tab-nav button {
    background: #161b22 !important;
    color: #8b949e !important;
    border: 1px solid #21262d !important;
}

.gr-tab-nav button.selected {
    background: #1f6feb !important;
    color: white !important;
}

h1, h2, h3 { color: #58a6ff !important; }
label { color: #8b949e !important; }

.ticket-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    color: #c9d1d9;
}
"""


# ── Helper: format ticket as HTML card ────────────────────────────────────────
def ticket_to_html(t: dict) -> str:
    status_colors = {
        "open":        ("#58a6ff", "#1f6feb22"),
        "in_progress": ("#e3b341", "#d2992222"),
        "resolved":    ("#3fb950", "#2ea04322"),
    }
    cat_colors = {
        "feedback_positive": "#3fb950",
        "feedback_negative": "#f85149",
        "query":             "#79c0ff",
    }
    sc, sbg = status_colors.get(t["status"], ("#8b949e", "#21262d"))
    cc       = cat_colors.get(t["category"], "#8b949e")
    created  = t["created_at"][:16].replace("T", " ")
    cat_label = t["category"].replace("_", " ").title()

    return f"""
    <div class='ticket-card'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;'>
            <span style='font-family:monospace;color:#8b949e;font-size:0.85rem'>{t['ticket_id']}</span>
            <span style='background:{sbg};color:{sc};border-radius:20px;padding:2px 12px;font-size:0.78rem'>
                {t['status'].replace('_',' ').title()}
            </span>
        </div>
        <div style='font-weight:600;color:#c9d1d9;margin-bottom:4px;'>{t['user_name']}</div>
        <div style='color:#8b949e;font-size:0.8rem;margin-bottom:8px;'>{created}</div>
        <div style='margin-bottom:6px;'>
            <span style='color:{cc};font-weight:600;font-size:0.85rem'>{cat_label}</span>
            <span style='color:#8b949e;font-size:0.85rem;margin-left:8px'>· {t['sentiment'].title()}</span>
        </div>
        <div style='background:#0f1117;border-radius:8px;padding:10px;font-size:0.88rem;color:#8b949e;margin-bottom:8px;'>
            💬 {t['message']}
        </div>
        <div style='background:#1f6feb11;border:1px solid #1f6feb33;border-radius:8px;padding:10px;font-size:0.88rem;color:#c9d1d9;'>
            🏦 {t['response']}
        </div>
    </div>
    """


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Customer Chat
# ══════════════════════════════════════════════════════════════════════════════
def handle_message(user_name, message):
    if not user_name.strip():
        return "<p style='color:#f85149'>⚠️ Please enter your name.</p>"
    if not message.strip():
        return "<p style='color:#f85149'>⚠️ Please enter a message.</p>"

    try:
        result = process_customer_message(user_name.strip(), message.strip())
        cat_colors = {
            "feedback_positive": "#3fb950",
            "feedback_negative": "#f85149",
            "query":             "#79c0ff",
        }
        cc        = cat_colors.get(result["category"], "#8b949e")
        cat_label = result["category"].replace("_", " ").title()

        return f"""
        <div style='margin-bottom:12px;'>
            <div style='background:#1f6feb;color:white;border-radius:18px 18px 4px 18px;
                        padding:12px 16px;max-width:75%;margin-left:auto;margin-bottom:8px;'>
                <b>{user_name}</b><br>{message}
            </div>

            <div style='display:flex;gap:8px;margin:8px 0;flex-wrap:wrap;align-items:center;'>
                <span style='color:{cc};font-weight:600'>◉ {cat_label}</span>
                <span style='color:#8b949e'>·</span>
                <span style='color:#8b949e;font-size:0.85rem'>Sentiment: {result['sentiment'].title()}</span>
                <span style='color:#8b949e'>·</span>
                <span style='font-family:monospace;font-size:0.8rem;color:#8b949e'>{result['ticket_id']}</span>
            </div>

            <div style='background:#161b22;border:1px solid #30363d;color:#c9d1d9;
                        border-radius:18px 18px 18px 4px;padding:12px 16px;max-width:75%;'>
                🏦 <b>BankAssist AI</b><br><br>{result['response']}
            </div>

            <div style='margin-top:10px;background:#2ea04322;border:1px solid #2ea04355;
                        border-radius:8px;padding:10px;color:#3fb950;font-size:0.88rem;'>
                ✅ Ticket <b>{result['ticket_id']}</b> created successfully!
            </div>
        </div>
        """
    except EnvironmentError as e:
        return f"<p style='color:#f85149'>⚠️ {e}</p>"
    except Exception as e:
        return f"<p style='color:#f85149'>❌ Pipeline error: {e}</p>"


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Ticket Tracker
# ══════════════════════════════════════════════════════════════════════════════
def load_tickets(status_filter, search):
    tickets = get_all_tickets()
    if not tickets:
        return "<p style='color:#8b949e;text-align:center;padding:40px'>No tickets yet. Go to Customer Chat to create one!</p>"

    filtered = [
        t for t in tickets
        if (status_filter == "All" or t["status"] == status_filter)
        and (not search or search.lower() in t["user_name"].lower()
                        or search.lower() in t["ticket_id"].lower())
    ]

    if not filtered:
        return "<p style='color:#8b949e;text-align:center;padding:40px'>No tickets match your filter.</p>"

    html = f"<p style='color:#8b949e;font-size:0.85rem;margin-bottom:12px'>{len(filtered)} ticket(s) found</p>"
    for t in filtered:
        html += ticket_to_html(t)
    return html


def lookup_ticket(ticket_id):
    if not ticket_id.strip():
        return "<p style='color:#f85149'>Please enter a ticket ID.</p>"
    t = fetch_ticket_status(ticket_id.strip())
    if not t:
        return "<p style='color:#f85149'>❌ Ticket not found.</p>"

    logs = get_ticket_logs(ticket_id.strip())
    log_html = ""
    if logs:
        log_html = "<div style='margin-top:10px;'><b style='color:#8b949e;font-size:0.8rem'>AUDIT LOG</b>"
        for l in logs:
            log_html += f"""
            <div style='background:#0f1117;border-radius:6px;padding:8px;margin-top:6px;font-size:0.82rem;color:#8b949e;'>
                <span style='color:#58a6ff'>{l['timestamp'][:16].replace('T',' ')}</span>
                · {l['action']} · {l['details']}
            </div>"""
        log_html += "</div>"

    return ticket_to_html(t) + log_html


def update_status(ticket_id, new_status):
    if not ticket_id.strip():
        return "<p style='color:#f85149'>Please enter a ticket ID.</p>"
    ok = resolve_ticket(ticket_id.strip(), new_status)
    if ok:
        return f"<p style='color:#3fb950'>✅ Ticket <b>{ticket_id}</b> updated to <b>{new_status}</b></p>"
    return "<p style='color:#f85149'>❌ Ticket not found.</p>"


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════
def load_dashboard():
    stats = get_stats()

    kpi_html = f"""
    <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;'>
        <div style='background:#161b22;border:1px solid #21262d;border-radius:12px;padding:16px;text-align:center;'>
            <div style='font-size:2rem;color:#58a6ff;font-weight:700'>{stats['total']}</div>
            <div style='color:#8b949e;font-size:0.8rem'>Total Tickets</div>
        </div>
        <div style='background:#161b22;border:1px solid #21262d;border-radius:12px;padding:16px;text-align:center;'>
            <div style='font-size:2rem;color:#58a6ff;font-weight:700'>{stats['open']}</div>
            <div style='color:#8b949e;font-size:0.8rem'>Open</div>
        </div>
        <div style='background:#161b22;border:1px solid #21262d;border-radius:12px;padding:16px;text-align:center;'>
            <div style='font-size:2rem;color:#e3b341;font-weight:700'>{stats['in_progress']}</div>
            <div style='color:#8b949e;font-size:0.8rem'>In Progress</div>
        </div>
        <div style='background:#161b22;border:1px solid #21262d;border-radius:12px;padding:16px;text-align:center;'>
            <div style='font-size:2rem;color:#3fb950;font-weight:700'>{stats['resolved']}</div>
            <div style='color:#8b949e;font-size:0.8rem'>Resolved</div>
        </div>
    </div>
    """

    all_tickets = get_all_tickets()
    if all_tickets:
        df = pd.DataFrame(all_tickets)[["ticket_id","user_name","category","sentiment","status","created_at"]]
        df["created_at"] = df["created_at"].str[:16].str.replace("T"," ")
        df.columns = ["Ticket ID","Customer","Category","Sentiment","Status","Created At"]
        table_html = df.to_html(index=False, border=0,
                                classes="",
                                justify="left").replace(
            "<table",
            "<table style='width:100%;border-collapse:collapse;color:#c9d1d9;font-size:0.85rem'"
        ).replace("<th>", "<th style='color:#8b949e;padding:8px;border-bottom:1px solid #21262d;text-align:left'>") \
         .replace("<td>", "<td style='padding:8px;border-bottom:1px solid #21262d'>")
    else:
        table_html = "<p style='color:#8b949e'>No tickets yet.</p>"

    return kpi_html + "<h3 style='color:#58a6ff'>Recent Tickets</h3>" + table_html


# ══════════════════════════════════════════════════════════════════════════════
# BUILD GRADIO APP
# ══════════════════════════════════════════════════════════════════════════════
with gr.Blocks(css=custom_css, title="BankAssist AI") as demo:

    gr.HTML("""
    <div style='text-align:center;padding:24px 0 8px;'>
        <h1 style='font-size:2rem;margin-bottom:4px'>🏦 BankAssist AI</h1>
        <p style='color:#8b949e;font-size:0.95rem'>
            Multi-Agent Banking Customer Support · AutoGen · Groq LLaMA 3.3 70B
        </p>
        <div style='display:flex;justify-content:center;gap:12px;margin-top:10px;flex-wrap:wrap;'>
            <span style='background:#1f6feb22;color:#58a6ff;border:1px solid #1f6feb55;
                         border-radius:20px;padding:3px 12px;font-size:0.78rem'>🔵 ClassifierAgent</span>
            <span style='color:#484f58'>→</span>
            <span style='background:#d2992222;color:#e3b341;border:1px solid #d2992255;
                         border-radius:20px;padding:3px 12px;font-size:0.78rem'>🟡 ResponderAgent</span>
            <span style='color:#484f58'>→</span>
            <span style='background:#2ea04322;color:#3fb950;border:1px solid #2ea04355;
                         border-radius:20px;padding:3px 12px;font-size:0.78rem'>🟢 TicketAgent</span>
        </div>
    </div>
    """)

    with gr.Tabs():

        # ── Tab 1: Chat ────────────────────────────────────────────────────
        with gr.Tab("💬 Customer Chat"):
            gr.HTML("<p style='color:#8b949e;margin-bottom:16px'>Submit a message — agents will classify, respond, and raise a ticket automatically.</p>")
            with gr.Row():
                with gr.Column(scale=1):
                    name_input = gr.Textbox(label="Your Name", placeholder="e.g. Priya Sharma")
                    sample_dd  = gr.Dropdown(
                        label="Load a sample message",
                        choices=[
                            "Select a sample…",
                            "😊 Positive feedback",
                            "😤 Negative feedback",
                            "❓ Account query",
                            "🔒 Security concern",
                        ],
                        value="Select a sample…",
                    )
                    msg_input = gr.Textbox(label="Your Message", lines=5,
                                           placeholder="Type your message here…")
                    send_btn  = gr.Button("🚀 Send to Agents", variant="primary")

                with gr.Column(scale=2):
                    chat_output = gr.HTML(
                        value="<div style='text-align:center;padding:60px;color:#484f58;'>"
                              "<div style='font-size:3rem'>🤖</div>"
                              "<div style='margin-top:12px'>Submit a message to see the agents in action</div>"
                              "</div>"
                    )

            samples_map = {
                "Select a sample…":  "",
                "😊 Positive feedback": "The new mobile banking app is absolutely fantastic! So much easier to manage my accounts.",
                "😤 Negative feedback": "My transaction has been stuck for 3 days. Nobody is helping me — this is unacceptable!",
                "❓ Account query":     "What is the current interest rate on your 1-year fixed deposit?",
                "🔒 Security concern":  "I noticed an unrecognised login attempt on my account. What should I do?",
            }

            def fill_sample(choice):
                return samples_map.get(choice, "")

            sample_dd.change(fill_sample, inputs=sample_dd, outputs=msg_input)
            send_btn.click(handle_message, inputs=[name_input, msg_input], outputs=chat_output)

        # ── Tab 2: Ticket Tracker ──────────────────────────────────────────
        with gr.Tab("🎫 Ticket Tracker"):
            with gr.Row():
                status_dd = gr.Dropdown(
                    label="Filter by Status",
                    choices=["All", "open", "in_progress", "resolved"],
                    value="All",
                )
                search_box = gr.Textbox(label="Search by name or ticket ID",
                                        placeholder="e.g. Priya or TKT-…")
                refresh_btn = gr.Button("🔄 Refresh", variant="secondary")

            tickets_html = gr.HTML()
            refresh_btn.click(load_tickets, inputs=[status_dd, search_box], outputs=tickets_html)
            status_dd.change(load_tickets,  inputs=[status_dd, search_box], outputs=tickets_html)

            gr.HTML("<hr style='border-color:#21262d;margin:20px 0'>")
            gr.HTML("<h3 style='color:#58a6ff'>🔍 Lookup & Update Ticket</h3>")

            with gr.Row():
                lookup_input = gr.Textbox(label="Ticket ID", placeholder="TKT-XXXXXXXX")
                lookup_btn   = gr.Button("🔍 Fetch Ticket", variant="secondary")

            lookup_output = gr.HTML()
            lookup_btn.click(lookup_ticket, inputs=lookup_input, outputs=lookup_output)

            gr.HTML("<hr style='border-color:#21262d;margin:16px 0'>")
            with gr.Row():
                update_id     = gr.Textbox(label="Ticket ID to Update", placeholder="TKT-XXXXXXXX")
                update_status_dd = gr.Dropdown(label="New Status",
                                               choices=["open","in_progress","resolved"],
                                               value="in_progress")
                update_btn    = gr.Button("✅ Update Status", variant="primary")

            update_output = gr.HTML()
            update_btn.click(update_status, inputs=[update_id, update_status_dd], outputs=update_output)

        # ── Tab 3: Dashboard ───────────────────────────────────────────────
        with gr.Tab("📊 Dashboard"):
            dash_btn  = gr.Button("🔄 Load Dashboard", variant="primary")
            dash_html = gr.HTML()
            dash_btn.click(load_dashboard, outputs=dash_html)


if __name__ == "__main__":
    demo.launch()