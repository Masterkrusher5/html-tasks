import streamlit as st
import os
import time
import threading
import json
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import core engine modules
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Forensic Legacy Modernizer Pro",
    page_icon="🛡️",
    layout="wide"
)

# UI Lock for thread-safe streaming
ui_lock = threading.Lock()

# --- PROFESSIONAL UI STYLING (High Contrast Fix) ---
st.markdown("""
    <style>
    /* Force high-contrast for the Documentation Report */
    .report-card {
        background-color: #ffffff !important;
        padding: 35px;
        border-radius: 12px;
        border: 2px solid #e0e6ed;
        color: #1e272e !important;  /* Deep Charcoal Text */
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
    
    /* Ensure markdown text in tabs is also readable */
    .stMarkdown p { color: inherit; }
    </style>
    """, unsafe_allow_html=True)

# --- Initialize Engines in Session State ---
if "engines_initialized" not in st.session_state:
    st.session_state.ingestor = FileIngestor()
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.engines_initialized = True

# --- Unified Worker (Thread-Safe Streaming) ---
def unified_transformation_worker(clean_code, doc_data, target_lang, code_slot, test_slot, result_collector):
    agent = st.session_state.agent
    lang_key = target_lang.lower().split()[0]
    
    try:
        # 1. Synthesize Modern Code
        full_code = ""
        synth_prompt = agent.get_synthesis_prompt(doc_data, target_lang)
        for delta in agent.stream_llm(synth_prompt):
            full_code += delta
            with ui_lock:
                code_slot.code(full_code + " ▌", language=lang_key)
        
        with ui_lock:
            code_slot.code(full_code, language=lang_key)
        
        # 2. Generate Unit Tests
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
        with ui_lock: st.error(f"Transformation Worker Error: {str(e)}")

# --- Main App Logic ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Automated Ingestion ➡️ Detailed Forensic Spec ➡️ Modern Unified Synthesis")

with st.sidebar:
    st.header("1. Pipeline Configuration")
    target_lang = st.selectbox("Target Architecture", [
        "Java (Vanilla)", 
        "Python (Clean)", 
        "C# (.NET Core)", 
        "TypeScript (Node.js)"
    ])
    source_lang = st.selectbox("Source Technology", ["COBOL", "VB6", "Java (Legacy)"])
    
    st.divider()
    if st.button("Reset Application Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- STEP 1: FILE INGESTION ---
st.subheader("📁 Step 1: Ingest Legacy Source")
uploaded_file = st.file_uploader("Upload Legacy Source File", type=['cbl', 'cob', 'vb', 'bas', 'java', 'txt'])

if uploaded_file:
    raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
    clean_code = st.session_state.ingestor.normalize(raw_content)
    meta = st.session_state.ingestor.extract_metadata(uploaded_file, clean_code)
    
    c1, c2, c3 = st.columns(3)
    c1.info(f"**File:** {meta['file_name']}")
    c2.info(f"**Detected Role:** {meta['role']}")
    c3.info(f"**Size:** {meta['size_kb']} KB")

    # --- STEP 2: FORENSIC DOCUMENTATION ---
    if st.button("📝 Phase 1: Generate Forensic Documentation", type="primary", use_container_width=True):
        with st.status("Analyzing voluminous code structure...", expanded=True) as status:
            doc_results = st.session_state.agent.generate_documentation(clean_code)
            # Save to state so it persists across re-runs
            st.session_state.doc = doc_results
            st.session_state.clean_code = clean_code
            status.update(label="Analysis Complete!", state="complete")

# --- STEP 3: READABLE FORENSIC DASHBOARD ---
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
        st.markdown(f"**Dashboard Status:** <span class='{metrics['color']}'>{metrics['zone']}</span>", unsafe_allow_html=True)
    with m3:
        st.metric("Legacy Complexity", f"{metrics.get('complexity', 'N/A')}/10")

    # --- Robust Parsing for Dependencies (Fixes TypeError) ---
    raw_deps = doc.get('dependencies', [])
    if isinstance(raw_deps, list):
        clean_deps = [str(d.get('name', d)) if isinstance(d, dict) else str(d) for d in raw_deps]
        deps_display = ", ".join(clean_deps) if clean_deps else "None Detected"
    else:
        deps_display = str(raw_deps)

    # READABLE KNOWLEDGE AREA (Styled Report Card)
    st.markdown(f"""
    <div class="report-card">
        <h3>1. Executive System Summary</h3>
        <p>{doc.get('summary', 'No summary available.')}</p>
        
        <h3>2. Comprehensive Business Logic Deep-Dive</h3>
        <p>{doc.get('description', 'No deep-dive documentation generated.')}</p>
        
        <h3>3. External Dependencies & IO</h3>
        <p>{deps_display}</p>
    </div>
    """, unsafe_allow_html=True)

    # Detailed Forensic Tabs
    tab_logic, tab_data = st.tabs(["⚙️ Functional Unit Analysis", "📊 Data Dictionary"])
    
    with tab_logic:
        st.subheader("Granular Logic Breakdown")
        funcs = doc.get("functions", [])
        if funcs:
            st.table(funcs)
        else:
            st.info("No explicit procedures identified in logic.")
    
    with tab_data:
        st.subheader("Data Dictionary (Variable Mapping)")
        data_dict = doc.get("data_dictionary", [])
        if data_dict:
            st.table(data_dict)
        else:
            st.info("No specific variable mappings detected.")

    # --- STEP 4: UNIFIED SYNTHESIS ---
    st.divider()
    st.header(f"⚙️ Phase 3: Unified Synthesis ({target_lang})")
    
    if st.button(f"🚀 Start Unified Transformation", type="primary", use_container_width=True):
        ctx = get_script_run_ctx() # Capture current UI session
        
        col_code, col_test = st.columns(2)
        with col_code:
            st.subheader(f"Modern {target_lang}")
            code_placeholder = st.empty()
        with col_test:
            st.subheader("Unit Test Suite")
            test_placeholder = st.empty()

        result_collector = {"code": "", "tests": ""}
        
        # Run worker in background thread
        t = threading.Thread(
            target=unified_transformation_worker,
            args=(st.session_state.clean_code, doc, target_lang, code_placeholder, test_placeholder, result_collector)
        )
        add_script_run_ctx(t, ctx)
        t.start()
        
        with st.spinner("Synthesizing unified architecture..."):
            t.join() # Wait for completion
        
        st.success("Modernization complete!")
        st.session_state.final_results = result_collector

# Retention of generated code after synthesis
if "final_results" in st.session_state:
    st.info("💡 **Pro-Tip:** Review the generated code and unit tests above. Ensure all 'dependencies' from Phase 2 are correctly integrated.")
