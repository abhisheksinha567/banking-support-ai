"""
app.py — Streamlit UI: Customer Chat | Ticket Tracker | Dashboard
"""

import streamlit as st
import pandas as pd
from database import get_all_tickets, get_stats, get_ticket_logs, init_db
from agents import process_customer_message, fetch_ticket_status, resolve_ticket

st.set_page_config(page_title="BankAssist AI", page_icon="🏦",
                   layout="wide", initial_sidebar_state="expanded")
init_db()

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#0f1117; }
[data-testid="stSidebar"]          { background:#161b22; border-right:1px solid #21262d; }
[data-testid="metric-container"]   { background:#161b22; border:1px solid #21262d;
                                     border-radius:12px; padding:16px 20px; }
[data-testid="stMetricValue"] { color:#58a6ff; font-size:2rem !important; }
[data-testid="stMetricLabel"] { color:#8b949e; font-size:0.8rem; }

.user-bubble  { background:#1f6feb; color:white; border-radius:18px 18px 4px 18px;
                padding:12px 16px; margin:6px 0; max-width:75%; margin-left:auto; }
.agent-bubble { background:#161b22; border:1px solid #30363d; color:#c9d1d9;
                border-radius:18px 18px 18px 4px; padding:12px 16px; margin:6px 0; max-width:75%; }

.badge-open        { background:#1f6feb22; color:#58a6ff; border:1px solid #1f6feb55;
                     border-radius:20px; padding:2px 10px; font-size:0.78rem; }
.badge-in_progress { background:#d2992222; color:#e3b341; border:1px solid #d2992255;
                     border-radius:20px; padding:2px 10px; font-size:0.78rem; }
.badge-resolved    { background:#2ea04322; color:#3fb950; border:1px solid #2ea04355;
                     border-radius:20px; padding:2px 10px; font-size:0.78rem; }

.tag-feedback_positive { color:#3fb950; font-weight:600; }
.tag-feedback_negative { color:#f85149; font-weight:600; }
.tag-query             { color:#79c0ff; font-weight:600; }
.section-header { color:#8b949e; font-size:0.75rem; letter-spacing:0.1em;
                  text-transform:uppercase; margin-bottom:8px; }
#MainMenu, footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏦 BankAssist AI")
    st.markdown("<p style='color:#8b949e;font-size:0.85rem'>Multi-Agent Customer Support</p>",
                unsafe_allow_html=True)
    st.divider()
    page = st.radio("Nav", ["💬 Customer Chat","🎫 Ticket Tracker","📊 Dashboard"],
                    label_visibility="collapsed")
    st.divider()
    st.markdown("<p class='section-header'>Agent Pipeline</p>", unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size:0.82rem;color:#8b949e;line-height:2'>
    🔵 <b style='color:#c9d1d9'>ClassifierAgent</b><br>&nbsp;&nbsp;&nbsp;↓<br>
    🟡 <b style='color:#c9d1d9'>ResponderAgent</b><br>&nbsp;&nbsp;&nbsp;↓<br>
    🟢 <b style='color:#c9d1d9'>TicketAgent</b>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Customer Chat
# ══════════════════════════════════════════════════════════════════════════════
if page == "💬 Customer Chat":
    st.markdown("## 💬 Customer Support Chat")
    st.markdown("<p style='color:#8b949e'>Messages are automatically classified, responded to, and logged as tickets.</p>",
                unsafe_allow_html=True)
    st.divider()

    col1, col2 = st.columns([1.2, 1.8])

    with col1:
        st.markdown("<p class='section-header'>New Message</p>", unsafe_allow_html=True)
        user_name = st.text_input("Your Name", placeholder="e.g. Priya Sharma")
        samples = {
            "Select a sample…": "",
            "😊 Positive feedback":  "The new mobile banking app is absolutely fantastic! So much easier to manage my accounts.",
            "😤 Negative feedback":  "My transaction has been stuck for 3 days. Nobody is helping me — this is unacceptable!",
            "❓ Account query":      "What is the current interest rate on your 1-year fixed deposit?",
            "🔒 Security concern":   "I noticed an unrecognised login attempt on my account. What should I do?",
        }
        sample  = st.selectbox("Load a sample", list(samples.keys()))
        message = st.text_area("Your Message", value=samples.get(sample,""),
                               height=140, placeholder="Type your message here…")
        submitted = st.button("🚀 Send to Agents", use_container_width=True, type="primary")

    with col2:
        st.markdown("<p class='section-header'>Agent Output</p>", unsafe_allow_html=True)
        if submitted:
            if not user_name.strip():
                st.error("Please enter your name.")
            elif not message.strip():
                st.error("Please enter a message.")
            else:
                with st.spinner("🤖 Agents processing…"):
                    try:
                        result = process_customer_message(user_name.strip(), message.strip())

                        st.markdown(f"<div class='user-bubble'><b>{user_name}</b><br>{message}</div>",
                                    unsafe_allow_html=True)

                        cat_label = result["category"].replace("_"," ").title()
                        st.markdown(f"""
                        <div style='display:flex;gap:8px;margin:8px 0;flex-wrap:wrap;align-items:center;'>
                          <span class='tag-{result["category"]}'>◉ {cat_label}</span>
                          <span style='color:#8b949e'>·</span>
                          <span style='color:#8b949e;font-size:0.85rem'>Sentiment: {result["sentiment"].title()}</span>
                          <span style='color:#8b949e'>·</span>
                          <span style='font-family:monospace;font-size:0.8rem;color:#8b949e'>{result["ticket_id"]}</span>
                        </div>""", unsafe_allow_html=True)

                        st.markdown(f"<div class='agent-bubble'>🏦 <b>BankAssist AI</b><br><br>{result['response']}</div>",
                                    unsafe_allow_html=True)
                        st.success(f"✅ Ticket **{result['ticket_id']}** created!")

                    except EnvironmentError as e:
                        st.error(f"⚠️ {e}")
                    except Exception as e:
                        st.error(f"❌ Pipeline error: {e}")
                        st.exception(e)
        else:
            st.markdown("""
            <div style='text-align:center;padding:60px 20px;color:#484f58;'>
              <div style='font-size:3rem'>🤖</div>
              <div style='margin-top:12px'>Submit a message to see the agents in action</div>
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Ticket Tracker
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎫 Ticket Tracker":
    st.markdown("## 🎫 Ticket Tracker")
    st.divider()
    tab1, tab2 = st.tabs(["All Tickets", "Lookup & Update"])

    with tab1:
        tickets = get_all_tickets()
        if not tickets:
            st.info("No tickets yet. Go to Customer Chat to create one!")
        else:
            c1, c2, c3 = st.columns(3)
            status_f = c1.multiselect("Status",   ["open","in_progress","resolved"],
                                      default=["open","in_progress","resolved"])
            cat_f    = c2.multiselect("Category", ["feedback_positive","feedback_negative","query"],
                                      default=["feedback_positive","feedback_negative","query"])
            search   = c3.text_input("Search name / ID", placeholder="Priya or TKT-…")

            filtered = [t for t in tickets
                        if t["status"] in status_f and t["category"] in cat_f
                        and (not search or search.lower() in t["user_name"].lower()
                                        or search.lower() in t["ticket_id"].lower())]

            st.markdown(f"<p style='color:#8b949e;font-size:0.85rem'>{len(filtered)} ticket(s)</p>",
                        unsafe_allow_html=True)

            for t in filtered:
                created = t["created_at"][:16].replace("T"," ")
                with st.expander(f"🎫 {t['ticket_id']} — {t['user_name']} ({created})"):
                    r1, r2, r3 = st.columns(3)
                    r1.markdown(f"<span class='badge-{t['status']}'>{t['status'].replace('_',' ').title()}</span>",
                                unsafe_allow_html=True)
                    r2.markdown(f"<span class='tag-{t['category']}'>{t['category'].replace('_',' ').title()}</span>",
                                unsafe_allow_html=True)
                    r3.markdown(f"<span style='color:#8b949e'>Sentiment: {t['sentiment'].title()}</span>",
                                unsafe_allow_html=True)
                    st.markdown(f"**Message:** {t['message']}")
                    st.info(f"**AI Response:** {t['response']}")

    with tab2:
        st.markdown("<p class='section-header'>Lookup</p>", unsafe_allow_html=True)
        lid = st.text_input("Ticket ID", placeholder="TKT-XXXXXXXX")
        if st.button("🔍 Fetch"):
            t = fetch_ticket_status(lid.strip())
            if t:
                st.markdown(f"**{t['ticket_id']}** — {t['user_name']}")
                st.metric("Status", t["status"].replace("_"," ").title())
                st.markdown(f"**Message:** {t['message']}")
                st.info(t["response"])
                logs = get_ticket_logs(lid.strip())
                if logs:
                    df = pd.DataFrame(logs)[["timestamp","action","details"]]
                    df["timestamp"] = df["timestamp"].str[:16].str.replace("T"," ")
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.error("Ticket not found.")

        st.divider()
        st.markdown("<p class='section-header'>Update Status</p>", unsafe_allow_html=True)
        uid = st.text_input("Ticket ID to Update", placeholder="TKT-XXXXXXXX", key="uid")
        ns  = st.selectbox("New Status", ["open","in_progress","resolved"])
        if st.button("✅ Update"):
            st.success(f"Updated to **{ns}**") if resolve_ticket(uid.strip(), ns) else st.error("Not found.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.markdown("## 📊 Analytics Dashboard")
    st.divider()
    stats = get_stats()

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Total Tickets", stats["total"])
    k2.metric("Open",          stats["open"])
    k3.metric("In Progress",   stats["in_progress"])
    k4.metric("Resolved",      stats["resolved"])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### By Category")
        if stats["by_category"]:
            df = pd.DataFrame({"Category":[k.replace("_"," ").title() for k in stats["by_category"]],
                               "Count": list(stats["by_category"].values())})
            st.bar_chart(df.set_index("Category"), color="#1f6feb")
        else:
            st.info("No data yet.")
    with c2:
        st.markdown("#### By Sentiment")
        if stats["by_sentiment"]:
            df = pd.DataFrame({"Sentiment":[k.title() for k in stats["by_sentiment"]],
                               "Count": list(stats["by_sentiment"].values())})
            st.bar_chart(df.set_index("Sentiment"), color="#3fb950")
        else:
            st.info("No data yet.")

    st.divider()
    st.markdown("#### All Tickets")
    all_t = get_all_tickets()
    if all_t:
        df = pd.DataFrame(all_t)[["ticket_id","user_name","category","sentiment","status","created_at"]]
        df["created_at"] = df["created_at"].str[:16].str.replace("T"," ")
        df.columns = ["Ticket ID","Customer","Category","Sentiment","Status","Created At"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No tickets yet.")