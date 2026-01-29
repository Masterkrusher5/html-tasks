import streamlit as st
import os
import time
import threading
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
# Prevents 'NoSessionContext' errors when background threads update the UI
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import core engine modules (Ensure __init__.py exists in these folders)
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

# Load environment variables from .env
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Forensic Legacy Modernizer",
    page_icon="🛡️",
    layout="wide"
)

# UI Lock to prevent browser websocket collisions during parallel streaming
ui_lock = threading.Lock()

# --- PROFESSIONAL UI STYLING (High-Contrast for Readability) ---
st.markdown("""
    <style>
    /* Force high-contrast for the Documentation Report */
    .report-card {
        background-color: #ffffff !important;
        padding: 35px;
        border-radius: 12px;
        border: 2px solid #e0e6ed;
        color: #1e272e !important;  /* Deep Charcoal Text for readability */
        line-height: 1.8;
        margin-bottom: 30px;
        box-shadow: 0px 10px 25px rgba(0,0,0,0.1);
    }
    .report-card h3, .report-card h4 {
        color: #0984e3 !important; /* Professional Blue Headers */
        margin-top: 20px;
        border-bottom: 2px solid #f1f2f6;
        padding-bottom: 8px;
        font-weight: bold;
    }
    .report-card p, .report-card li, .report-card span {
        color: #2d3436 !important;
        font-size: 17px;
    }
    .status-green { color: #27ae60; font-weight: bold; font-size: 20px; }
    .status-amber { color: #f39c12; font-weight: bold; font-size: 20px; }
    .status-red { color: #e74c3c; font-weight: bold; font-size: 20px; }
    
    /* Code block styling */
    .stCodeBlock { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Initialize Engines in Session State ---
if "engines_initialized" not in st.session_state:
    if not os.getenv("LLM_ENDPOINT") or not os.getenv("LLM_KEY"):
        st.warning("⚠️ LLM_ENDPOINT or LLM_KEY is missing in your .env file.")
    st.session_state.ingestor = FileIngestor()
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.engines_initialized = True

# --- Unified Worker (Thread-Safe Streaming) ---
def unified_transformation_worker(clean_code, doc_data, target_lang, code_slot, test_slot, result_collector):
    """
    Worker function executed in a dedicated thread.
    1. Streams the full modern code file.
    2. Streams the full unit test file once code is available.
    """
    agent = st.session_state.agent
    lang_key = target_lang.lower().split()[0]
    
    try:
        # 1. PHASE 3: UNIFIED CODE SYNTHESIS
        full_code = ""
        synth_prompt = agent.get_synthesis_prompt(doc_data, target_lang)
        
        for delta in agent.stream_llm(synth_prompt):
            full_code += delta
            with ui_lock:
                code_slot.code(full_code + " ▌", language=lang_key)
        
        with ui_lock:
            code_slot.code(full_code, language=lang_key)
        
        # 2. PHASE 4: UNIFIED UNIT TEST GENERATION
        full_tests = ""
        test_prompt = agent.get_test_prompt(full_code, target_lang)
        
        for delta in agent.stream_llm(test_prompt):
            full_tests += delta
            with ui_lock:
                test_slot.code(full_tests + " ▌", language=lang_key)
        
        with ui_lock:
            test_slot.code(full_tests, language=lang_key)
            
        result_collector["code"] = full_code
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock: 
            st.error(f"Synthesis Worker Error: {str(e)}")

# --- Main Interface ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Automated Ingestion ➡️ Detailed Forensic Spec ➡️ Unified Modern Synthesis")

with st.sidebar:
    st.header("1. Pipeline Configuration")
    target_lang = st.selectbox("Target Language", [
        "Java (Vanilla)", 
        "Python (Clean)", 
        "C# (.NET Core)", 
        "TypeScript (Node.js)"
    ])
    source_lang = st.selectbox("Source Language", ["COBOL", "VB6", "Java (Legacy)"])
    
    st.divider()
    st.markdown("**Core Standards:**")
    st.write("✅ File-based Ingestion")
    st.write("✅ Forensic Logic Extraction")
    st.write("✅ Framework-free (Vanilla)")
    
    if st.button("Reset Session"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: FILE INGESTION ---
st.subheader("📁 Step 1: Ingest Legacy Source")
uploaded_file = st.file_uploader("Upload Legacy Source File (COBOL, VB, Java, etc.)", type=['cbl', 'cob', 'vb', 'bas', 'java', 'txt'])

if uploaded_file:
    # Read file using Ingestor (Handling character encoding)
    raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
    # Phase 1: Normalization (Collapsing whitespace and stripping noise)
    clean_code = st.session_state.ingestor.normalize(raw_content)
    # Extract file metadata for the dashboard
    meta = st.session_state.ingestor.extract_metadata(uploaded_file, clean_code)
    
    c1, c2, c3 = st.columns(3)
    c1.info(f"**File:** {meta['file_name']}")
    c2.info(f"**Detected Role:** {meta['role']}")
    c3.info(f"**Size:** {meta['size_kb']} KB")

    # --- STEP 2: FORENSIC DOCUMENTATION ---
    if st.button("📝 Phase 1: Generate Forensic Documentation", type="primary", use_container_width=True):
        with st.spinner("Performing deep-dive forensic logic extraction..."):
            doc_results = st.session_state.agent.generate_documentation(clean_code)
            st.session_state.doc = doc_results
            st.session_state.clean_code = clean_code

# --- STEP 3: READABLE FORENSIC REPORT ---
if "doc" in st.session_state:
    doc = st.session_state.doc
    metrics = st.session_state.agent.calculate_dashboard_metrics(doc)
    
    st.divider()
    st.header("📑 Phase 2: Technical & Functional Specification")
    
    # Dashboard Metrics Row
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("AI Confidence", metrics['confidence_pct'])
    with m2:
        st.markdown(f"**Status:** <span class='{metrics['color']}'>{metrics['zone']}</span>", unsafe_allow_html=True)
    with m3:
        st.metric("Legacy Complexity", f"{metrics.get('complexity', 'N/A')}/10")

    # READABLE KNOWLEDGE AREA (Styled for high readability)
    st.markdown(f"""
    <div class="report-card">
        <h3>1. Executive System Summary</h3>
        <p>{doc.get('summary', 'No summary available.')}</p>
        
        <h3>2. Comprehensive Business Logic Deep-Dive</h3>
        <p>{doc.get('description', 'No documentation generated.')}</p>
        
        <h3>3. External Dependencies & IO</h3>
        <p>{", ".join(doc.get('dependencies', ['None Detected']))}</p>
    </div>
    """, unsafe_allow_html=True)

    # Detailed Analysis Tabs
    tab_func, tab_data = st.tabs(["⚙️ Functional Unit Analysis", "📊 Data Dictionary"])
    
    with tab_func:
        st.subheader("Granular Procedure Breakdown")
        st.table(doc.get("functions", []))
    
    with tab_data:
        st.subheader("Legacy Variable Mapping")
        st.write("Mapping of cryptic legacy names to business roles:")
        st.table(doc.get("data_dictionary", []))

    # --- STEP 4: UNIFIED SYNTHESIS ---
    st.divider()
    st.header(f"⚙️ Phase 3: Modernize to {target_lang}")
    
    if st.button(f"🚀 Start Unified Transformation", type="primary", use_container_width=True):
        ctx = get_script_run_ctx() # Capture UI session context for the thread
        
        col_code, col_test = st.columns(2)
        with col_code:
            st.subheader(f"Modern {target_lang}")
            code_placeholder = st.empty()
        with col_test:
            st.subheader("JUnit / Unit Test Suite")
            test_placeholder = st.empty()

        result_collector = {"code": "", "tests": ""}
        
        # Launch background thread to stream results without hanging the UI
        t = threading.Thread(
            target=unified_transformation_worker,
            args=(st.session_state.clean_code, doc, target_lang, code_placeholder, test_placeholder, result_collector)
        )
        add_script_run_ctx(t, ctx)
        t.start()
        
        with st.spinner("Synthesizing unified architecture and validating logic..."):
            t.join() # Wait for thread to finish streaming
        
        st.success("Modernization successful!")
        st.session_state.final_results = result_collector

# Footer Info
if "final_results" in st.session_state:
    st.info("💡 **Developer Note:** The generated code follows 'Vanilla' standards. External dependencies have been mocked in the Test Suite.")
