import io
import requests
import streamlit as st


# --------- CONFIG ---------
DEFAULT_API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="NUST Bank Assistant",
    page_icon="💳",
    layout="wide",
)

# --------- ENHANCED MODERN THEME / CSS ---------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide top header bar */
    header[data-testid="stHeader"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-bottom: none;
    }
    
    /* Hide toolbar/menu */
    .stToolbar, [data-testid="stToolbar"] {
        display: none;
    }
    
    /* Page background - Elegant gradient */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Header card */
    .header-card {
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 28px 36px;
        margin-bottom: 28px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    .header-card h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 38px;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .header-card p {
        color: #64748b;
        font-size: 15px;
        margin: 10px 0 0 0;
        font-weight: 400;
        line-height: 1.5;
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 18px;
        border-radius: 100px;
        font-size: 13px;
        font-weight: 600;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4);
    }
    
    .status-badge::before {
        content: "●";
        font-size: 10px;
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: rgba(255, 255, 255, 0.12);
        padding: 8px;
        border-radius: 14px;
        backdrop-filter: blur(10px);
        margin-bottom: 0;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 10px;
        color: rgba(255, 255, 255, 0.75);
        font-weight: 600;
        padding: 10px 24px;
        transition: all 0.3s ease;
        font-size: 15px;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.98);
        color: #667eea;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    }
    
    /* Better spacing for tab content */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 24px;
    }

    /* Chat message styling */
    .stChatMessage {
        border-radius: 18px !important;
        padding: 18px 22px !important;
        margin-bottom: 14px !important;
        border: none !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08) !important;
    }

    .stChatMessage[data-testid="stChatMessage"]:has(div[role="img"][aria-label="user"]) {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }
    
    .stChatMessage[data-testid="stChatMessage"]:has(div[role="img"][aria-label="user"]) p {
        color: white !important;
    }

    .stChatMessage[data-testid="stChatMessage"]:has(div[role="img"][aria-label="assistant"]) {
        background: rgba(255, 255, 255, 0.98) !important;
        color: #1e293b !important;
    }

    /* Card containers */
    .custom-card {
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(10px);
        border-radius: 18px;
        padding: 26px;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.4);
        margin-bottom: 18px;
    }
    
    .custom-card h4 {
        color: #1e293b;
        font-size: 19px;
        font-weight: 700;
        margin: 0 0 18px 0;
        letter-spacing: -0.3px;
    }
    
    .custom-card h3 {
        color: #1e293b;
        font-size: 21px;
        font-weight: 700;
        margin: 0 0 10px 0;
        letter-spacing: -0.3px;
    }
    
    .card-subtitle {
        color: #64748b;
        font-size: 14px;
        margin-bottom: 22px;
        line-height: 1.6;
    }
    
    /* Section headers */
    .section-header {
        color: white;
        font-size: 20px;
        font-weight: 700;
        margin: 0 0 16px 0;
        letter-spacing: -0.3px;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    /* Buttons */
    .stButton button {
        border-radius: 12px !important;
        padding: 12px 26px !important;
        border: none !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.35) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.45) !important;
    }
    
    /* Example buttons */
    .stButton button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.95) !important;
        color: #667eea !important;
        border: 2px solid rgba(102, 126, 234, 0.25) !important;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.06) !important;
        font-weight: 500 !important;
    }
    
    .stButton button[kind="secondary"]:hover {
        background: white !important;
        border-color: #667eea !important;
        box-shadow: 0 5px 18px rgba(102, 126, 234, 0.25) !important;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > textarea {
        border-radius: 12px !important;
        border: 2px solid #e2e8f0 !important;
        background: white !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.12) !important;
    }
    
    /* Slider */
    .stSlider {
        padding: 12px 0;
    }
    
    .stSlider > div > div > div > div {
        background: #667eea !important;
    }
    
    /* File uploader */
    .stFileUploader {
        background: rgba(255, 255, 255, 0.6);
        border-radius: 14px;
        padding: 22px;
        border: 2px dashed #cbd5e1;
        transition: all 0.3s ease;
    }
    
    .stFileUploader:hover {
        border-color: #667eea;
        background: rgba(255, 255, 255, 0.75);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        padding-top: 3rem;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: rgba(255, 255, 255, 0.95);
    }
    
    section[data-testid="stSidebar"] h1 {
        color: white;
        font-size: 22px;
        font-weight: 700;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.18);
        border: 1.5px solid rgba(255, 255, 255, 0.35);
        color: white;
    }
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input::placeholder {
        color: rgba(255, 255, 255, 0.65);
    }
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input:focus {
        background: rgba(255, 255, 255, 0.25);
        border-color: rgba(255, 255, 255, 0.6);
    }
    
    /* Chat input - Match card style */
    .stChatInputContainer {
        border-top: none !important;
        background: transparent !important;
        padding: 16px 0 !important;
    }
    
    .stChatInputContainer > div {
        background: rgba(255, 255, 255, 0.98) !important;
        border-radius: 16px !important;
        border: 2px solid rgba(255, 255, 255, 0.4) !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12) !important;
        padding: 4px !important;
    }
    
    .stChatInputContainer textarea {
        border: none !important;
        background: transparent !important;
        color: #1e293b !important;
        font-size: 15px !important;
    }
    
    .stChatInputContainer textarea::placeholder {
        color: #94a3b8 !important;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
    }
    
    .stError {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 4px 16px rgba(239, 68, 68, 0.3);
    }
    
    /* Sources section */
    .sources-section {
        margin-top: 18px;
        padding: 18px;
        background: rgba(102, 126, 234, 0.06);
        border-radius: 14px;
        border-left: 4px solid #667eea;
    }
    
    .sources-section h6 {
        color: #667eea;
        font-weight: 700;
        font-size: 13px;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }
    
    /* Caption text */
    .stCaption {
        color: rgba(255, 255, 255, 0.8) !important;
        font-size: 13px !important;
    }
    
    /* Hide empty columns and containers */
    .stColumn > div:empty,
    .element-container:empty {
        display: none !important;
    }
    
    /* Column spacing improvements */
    .stColumn {
        padding: 0 10px;
    }
    
    /* Better markdown spacing */
    .stMarkdown p {
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------- SIDEBAR ---------
st.sidebar.title("⚙️ Settings")

api_url = st.sidebar.text_input("FastAPI backend URL", DEFAULT_API_URL)
API_URL = api_url.rstrip("/") or DEFAULT_API_URL

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Model:** Llama-3.2-3B-Instruct\n"
    "**Pipeline:** RAG + FAISS (main index)\n\n"
    "Use the *Admin* tab to update FAQs or upload a new Excel policy sheet."
)

# --------- HEADER ---------
st.markdown(
    """
    <div class="header-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>💳 NUST Bank Assistant</h1>
                <p>Ask about accounts, profit rates, eligibility, documents, and other product details.</p>
            </div>
            <div class="status-badge">
                Live
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------- TABS ---------
tab_chat, tab_admin = st.tabs(["💬 Chat", "🛠 Admin"])

# ======================================
#                  CHAT TAB
# ======================================
with tab_chat:
    left, right = st.columns([0.68, 0.32], gap="medium")

    with right:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("#### 💡 Quick examples")
        st.caption("Click any example to try it out")
        
        examples = [
            "What is the opening and minimum balance requirement in NAA?",
            "What is the profit rate for NUST Sahar Savings Account?",
            "What are the documents required for LCA?",
        ]
        
        for ex in examples:
            if st.button(ex, key=f"ex_{ex}", use_container_width=True, type="secondary"):
                st.session_state["prefill_query"] = ex
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown('<div class="custom-card" style="margin-top: 18px;">', unsafe_allow_html=True)
        st.markdown("#### ⚙️ Retrieval settings")
        top_k = st.slider(
            "Number of documents (Top K)",
            min_value=1,
            max_value=5,
            value=3,
            help="Higher values retrieve more context but may include less relevant information",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with left:
        st.markdown('<h4 class="section-header">💬 Conversation</h4>', unsafe_allow_html=True)

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "text": (
                        " Welcome to NUST Bank Assistant! I'm here to help you with information about "
                        "account types, opening balances, profit rates, eligibility requirements, and more. "
                        "Feel free to ask me anything!"
                    ),
                }
            ]

        # Render history
        for msg in st.session_state.chat_history:
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                st.write(msg["text"])
                if msg["role"] == "assistant" and "sources" in msg and msg["sources"]:
                    st.markdown('<div class="sources-section">', unsafe_allow_html=True)
                    st.markdown("###### 📚 Sources")
                    for s in msg["sources"]:
                        sheet = s.get("sheet", "Unknown")
                        q = s.get("question", "")
                        score = s.get("score", None)
                        if score is not None:
                            st.markdown(f"• **{sheet}** · {q}  _(relevance: {score:.2f})_")
                        else:
                            st.markdown(f"• **{sheet}** · {q}")
                    st.markdown("</div>", unsafe_allow_html=True)

        # Chat input (with optional prefill from example)
        default_prompt = st.session_state.pop("prefill_query", "")
        user_query = st.chat_input("Ask a question about NUST Bank…", key="chat_input")

        if default_prompt and not user_query:
            user_query = default_prompt

        if user_query:
            # Show user message
            st.session_state.chat_history.append({"role": "user", "text": user_query})
            with st.chat_message("user"):
                st.write(user_query)

            # Call backend with short-term history
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        MAX_TURNS = 6  # last few messages for light memory
                        history = st.session_state.chat_history[-MAX_TURNS:]

                        history_text = ""
                        for m in history:
                            prefix = "User:" if m["role"] == "user" else "Assistant:"
                            history_text += f"{prefix} {m['text']}\n"

                        # IMPORTANT: query is ONLY current question; history goes in separate field
                        payload = {
                            "query": user_query,
                            "top_k": top_k,
                            "history": history_text,
                        }

                        resp = requests.post(
                            f"{API_URL}/chat",
                            json=payload,
                            timeout=60,
                        )

                        if resp.status_code != 200:
                            answer = f"⚠️ Error from backend: {resp.status_code} {resp.text}"
                            sources = []
                        else:
                            data = resp.json()
                            answer = data.get("answer", "No answer returned by backend.")
                            sources = data.get("sources", [])
                    except Exception:
                        answer = "⚠️ Network error: Unable to connect to backend"
                        sources = []

                    st.write(answer)
                    if sources:
                        st.markdown('<div class="sources-section">', unsafe_allow_html=True)
                        st.markdown("###### 📚 Sources")
                        for s in sources:
                            sheet = s.get("sheet", "Unknown")
                            q = s.get("question", "")
                            score = s.get("score", None)
                            if score is not None:
                                st.markdown(f"• **{sheet}** · {q}  _(relevance: {score:.2f})_")
                            else:
                                st.markdown(f"• **{sheet}** · {q}")
                        st.markdown("</div>", unsafe_allow_html=True)

            st.session_state.chat_history.append(
                {"role": "assistant", "text": answer, "sources": sources}
            )
            st.rerun()

# ======================================
#                  ADMIN TAB
# ======================================
with tab_admin:
    col_faq, col_excel = st.columns([0.5, 0.5], gap="medium")

    with col_faq:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("###  Add / update FAQ entry")
        st.markdown(
            '<div class="card-subtitle">'
            "Use this to add or update a single policy entry. "
            "If a question already exists for a sheet, it will be replaced."
            "</div>",
            unsafe_allow_html=True,
        )

        sheet = st.text_input(
            "Sheet / Product code",
            placeholder="e.g., NAA, LCA, VPCA",
            key="a_sheet",
        )
        question = st.text_input(
            "Question",
            placeholder="Enter the question",
            key="a_question",
        )
        answer = st.text_area(
            "Answer / content",
            height=160,
            placeholder="Enter the detailed answer",
            key="a_answer",
        )

        if st.button(" Save / update FAQ", key="btn_save_faq", use_container_width=True):
            if not sheet or not question or not answer:
                st.error("⚠️ Please fill all fields: sheet, question, and answer.")
            else:
                try:
                    resp = requests.post(
                        f"{API_URL}/add_document",
                        json={
                            "sheet": sheet,
                            "question": question,
                            "answer": answer,
                        },
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        st.success("✅ FAQ entry saved successfully!")
                    else:
                        st.error(f"⚠️ Backend error: {resp.status_code}")
                except Exception:
                    st.error("⚠️ Network error: Unable to connect to backend")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_excel:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("###  Upload Excel policy file")
        st.markdown(
            '<div class="card-subtitle">'
            "Upload the latest product knowledge Excel. "
            "The system will extract QAs, upsert by (sheet, question), "
            "and rebuild the main FAISS index."
            "</div>",
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "Choose Excel file (.xlsx)",
            type=["xlsx"],
            key="excel_upload",
        )

        if st.button(
            " Upload & rebuild index",
            key="btn_upload_excel",
            use_container_width=True,
        ):
            if uploaded_file is None:
                st.error("⚠️ Please choose an Excel file first.")
            else:
                try:
                    file_bytes = uploaded_file.read()
                    files = {
                        "file": (
                            uploaded_file.name,
                            io.BytesIO(file_bytes),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    }
                    with st.spinner("Processing Excel file..."):
                        resp = requests.post(
                            f"{API_URL}/upload_excel", files=files, timeout=300
                        )
                    if resp.status_code == 200:
                        data = resp.json()
                        count = data.get("count", 0)
                        st.success(
                            f"✅ Success! Excel uploaded and processed. "
                            f"{count} documents were added to the main index."
                        )
                    else:
                        st.error(f"⚠️ Backend error: {resp.status_code}")
                except Exception:
                    st.error("⚠️ Network error: Unable to connect to backend")

        st.markdown("</div>", unsafe_allow_html=True)