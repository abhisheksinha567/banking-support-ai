"""
app.py — Gradio UI for BankAssist AI
"""

import os
import gradio as gr
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from database import get_all_tickets, get_stats, get_ticket_logs, init_db
from agents import process_customer_message, fetch_ticket_status, resolve_ticket

init_db()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Customer Chat
# ══════════════════════════════════════════════════════════════════════════════
def handle_message(user_name, message):
    if not user_name.strip():
        return "⚠️ Please enter your name."
    if not message.strip():
        return "⚠️ Please enter a message."
    try:
        result = process_customer_message(user_name.strip(), message.strip())
        cat_label = result["category"].replace("_", " ").title()
        return f"""
🎫 Ticket ID   : {result['ticket_id']}
📂 Category    : {cat_label}
💭 Sentiment   : {result['sentiment'].title()}
📌 Status      : {result['status'].title()}

🏦 BankAssist AI Response:
{result['response']}
        """.strip()
    except EnvironmentError as e:
        return f"⚠️ Configuration error: {e}"
    except Exception as e:
        return f"❌ Pipeline error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Ticket Tracker
# ══════════════════════════════════════════════════════════════════════════════
def load_tickets(status_filter, search):
    tickets = get_all_tickets()
    if not tickets:
        return "No tickets yet. Go to Customer Chat to create one!"

    filtered = [
        t for t in tickets
        if (status_filter == "All" or t["status"] == status_filter)
        and (not search or search.lower() in t["user_name"].lower()
                        or search.lower() in t["ticket_id"].lower())
    ]

    if not filtered:
        return "No tickets match your filter."

    lines = [f"{len(filtered)} ticket(s) found\n{'─'*60}"]
    for t in filtered:
        created = t["created_at"][:16].replace("T", " ")
        lines.append(f"""
🎫 {t['ticket_id']} | {t['user_name']} | {created}
   Category : {t['category'].replace('_',' ').title()}
   Sentiment: {t['sentiment'].title()}
   Status   : {t['status'].replace('_',' ').title()}
   Message  : {t['message'][:80]}...
   Response : {t['response'][:100]}...
{'─'*60}""")
    return "\n".join(lines)


def lookup_ticket(ticket_id):
    if not ticket_id.strip():
        return "Please enter a ticket ID."
    t = fetch_ticket_status(ticket_id.strip())
    if not t:
        return "❌ Ticket not found."

    logs = get_ticket_logs(ticket_id.strip())
    log_lines = "\n".join(
        f"  [{l['timestamp'][:16].replace('T',' ')}] {l['action']} — {l['details']}"
        for l in logs
    )

    return f"""
🎫 Ticket    : {t['ticket_id']}
👤 Customer  : {t['user_name']}
📂 Category  : {t['category'].replace('_',' ').title()}
💭 Sentiment : {t['sentiment'].title()}
📌 Status    : {t['status'].replace('_',' ').title()}
🕐 Created   : {t['created_at'][:16].replace('T',' ')}

💬 Message:
{t['message']}

🏦 AI Response:
{t['response']}

📋 Audit Log:
{log_lines if log_lines else '  No logs yet.'}
    """.strip()


def update_status(ticket_id, new_status):
    if not ticket_id.strip():
        return "Please enter a ticket ID."
    ok = resolve_ticket(ticket_id.strip(), new_status)
    if ok:
        return f"✅ Ticket {ticket_id} updated to '{new_status}' successfully!"
    return "❌ Ticket not found. Please check the ticket ID."


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════
def load_dashboard():
    stats = get_stats()
    all_tickets = get_all_tickets()

    summary = f"""
📊 DASHBOARD SUMMARY
{'═'*40}
📋 Total Tickets  : {stats['total']}
🔵 Open           : {stats['open']}
🟡 In Progress    : {stats['in_progress']}
🟢 Resolved       : {stats['resolved']}

📂 BY CATEGORY
{'─'*40}
""".strip()

    for cat, cnt in stats.get("by_category", {}).items():
        summary += f"\n  {cat.replace('_',' ').title():30} {cnt}"

    summary += f"\n\n💭 BY SENTIMENT\n{'─'*40}"
    for sent, cnt in stats.get("by_sentiment", {}).items():
        summary += f"\n  {sent.title():30} {cnt}"

    return summary


def load_ticket_table():
    all_tickets = get_all_tickets()
    if not all_tickets:
        return pd.DataFrame(columns=["Ticket ID","Customer","Category","Sentiment","Status","Created At"])
    df = pd.DataFrame(all_tickets)[["ticket_id","user_name","category","sentiment","status","created_at"]]
    df["created_at"] = df["created_at"].str[:16].str.replace("T"," ")
    df.columns = ["Ticket ID","Customer","Category","Sentiment","Status","Created At"]
    return df


# ══════════════════════════════════════════════════════════════════════════════
# BUILD GRADIO APP
# ══════════════════════════════════════════════════════════════════════════════
with gr.Blocks(title="BankAssist AI") as demo:

    gr.Markdown("""
    # 🏦 BankAssist AI
    ### Multi-Agent Banking Customer Support
    **Pipeline:** 🔵 ClassifierAgent → 🟡 ResponderAgent → 🟢 TicketAgent | Powered by AutoGen + Groq LLaMA 3.3 70B
    """)

    with gr.Tabs():

        # ── Tab 1: Chat ────────────────────────────────────────────────────
        with gr.Tab("💬 Customer Chat"):
            gr.Markdown("Submit a message — agents will classify, respond, and raise a ticket automatically.")
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
                    chat_output = gr.Textbox(
                        label="Agent Response",
                        lines=12,
                        interactive=False,
                        placeholder="Agent response will appear here…"
                    )

            samples_map = {
                "Select a sample…":     "",
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
            gr.Markdown("### Browse Tickets")
            with gr.Row():
                status_dd  = gr.Dropdown(label="Filter by Status",
                                         choices=["All","open","in_progress","resolved"],
                                         value="All")
                search_box = gr.Textbox(label="Search by name or ticket ID",
                                        placeholder="e.g. Priya or TKT-…")
                refresh_btn = gr.Button("🔄 Refresh", variant="secondary")

            tickets_out = gr.Textbox(label="Tickets", lines=20, interactive=False)
            refresh_btn.click(load_tickets, inputs=[status_dd, search_box], outputs=tickets_out)
            status_dd.change(load_tickets,  inputs=[status_dd, search_box], outputs=tickets_out)

            gr.Markdown("### 🔍 Lookup Ticket")
            with gr.Row():
                lookup_input = gr.Textbox(label="Ticket ID", placeholder="TKT-XXXXXXXX")
                lookup_btn   = gr.Button("🔍 Fetch", variant="secondary")
            lookup_out = gr.Textbox(label="Ticket Details", lines=15, interactive=False)
            lookup_btn.click(lookup_ticket, inputs=lookup_input, outputs=lookup_out)

            gr.Markdown("### ✏️ Update Ticket Status")
            with gr.Row():
                update_id        = gr.Textbox(label="Ticket ID", placeholder="TKT-XXXXXXXX")
                update_status_dd = gr.Dropdown(label="New Status",
                                               choices=["open","in_progress","resolved"],
                                               value="in_progress")
                update_btn       = gr.Button("✅ Update", variant="primary")
            update_out = gr.Textbox(label="Result", lines=2, interactive=False)
            update_btn.click(update_status, inputs=[update_id, update_status_dd], outputs=update_out)

        # ── Tab 3: Dashboard ───────────────────────────────────────────────
        with gr.Tab("📊 Dashboard"):
            dash_btn   = gr.Button("🔄 Load Dashboard", variant="primary")
            dash_out   = gr.Textbox(label="Summary", lines=20, interactive=False)
            table_out  = gr.Dataframe(label="All Tickets")
            
            def load_all():
                return load_dashboard(), load_ticket_table()
            
            dash_btn.click(load_all, outputs=[dash_out, table_out])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)