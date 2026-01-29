import streamlit as st
import os
import time
import threading
import json
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import our refactored core modules
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent
from core.knowledge_base import RAGContextEngine
from core.agents import ValidationRefactoringAgent

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Forensic Legacy Modernizer (Azure)",
    page_icon="🛡️",
    layout="wide"
)

# UI Lock for thread-safe streaming
ui_lock = threading.Lock()

# --- PROFESSIONAL UI STYLING (Forced High-Contrast for Readability) ---
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
    .status-green { color: #27ae60; font-weight: bold; font-size: 22px; border: 2px solid #27ae60; padding: 5px 15px; border-radius: 5px; }
    .status-amber { color: #f39c12; font-weight: bold; font-size: 22px; border: 2px solid #f39c12; padding: 5px 15px; border-radius: 5px; }
    .status-red { color: #e74c3c; font-weight: bold; font-size: 22px; border: 2px solid #e74c3c; padding: 5px 15px; border-radius: 5px; }
    
    /* Code block styling */
    .stCodeBlock { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_value=True)

# --- Initialize Engines in Session State ---
if "engines_initialized" not in st.session_state:
    st.session_state.ingestor = FileIngestor()
    st.session_state.analyzer = UnifiedOpenAIAgent()
    st.session_state.rag_engine = RAGContextEngine()
    st.session_state.agent = ValidationRefactoringAgent()
    st.session_state.engines_initialized = True

# --- Unified Worker (Thread-Safe Streaming for Azure) ---
def unified_transformation_worker(clean_code, doc_data, target_lang, code_slot, test_slot, result_collector):
    agent = st.session_state.agent
    lang_key = target_lang.lower().split()[0]
    
    try:
        # 1. Synthesize Modern Code (Vanilla Java / Python)
        full_code = ""
        synth_prompt = agent.get_unified_synthesis_prompt(doc_data, target_lang)
        for delta in agent.stream_llm(synth_prompt):
            full_code += delta
            with ui_lock:
                code_slot.code(full_code + " ▌", language=lang_key)
        
        with ui_lock:
            code_slot.code(full_code, language=lang_key)
        
        # 2. Generate Unit Tests (JUnit 5 / Pytest)
        full_tests = ""
        test_prompt = agent.get_unified_test_prompt(full_code, target_lang)
        for delta in agent.stream_llm(test_prompt):
            full_tests += delta
            with ui_lock:
                test_slot.code(full_tests + " ▌", language=lang_key)
        
        with ui_lock:
            test_slot.code(full_tests, language=lang_key)
            
        result_collector["code"] = full_code
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock: st.error(f"Synthesis Worker Error: {str(e)}")

# --- Main App Logic ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Automated Ingestion ➡️ Forensic Knowledge Extraction ➡️ Unified Modern Synthesis")

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
    st.markdown("**Core Standards:**")
    st.write("✅ File-based Ingestion")
    st.write("✅ Forensic Logic Extraction")
    st.write("✅ Framework-free (Vanilla)")
    
    if st.button("Reset Pipeline"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: FILE INGESTION ---
st.subheader("📁 Step 1: Ingest Legacy Source")
uploaded_file = st.file_uploader("Upload Legacy Source File (Voluminous code supported)", type=['cbl', 'cob', 'vb', 'bas', 'java', 'txt'])

if uploaded_file:
    # Read file using Ingestor logic (Handling Encoding)
    raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
    # Step 1: Normalization
    clean_code = st.session_state.ingestor.normalize(raw_content)
    # Extract Metadata
    meta = st.session_state.ingestor.extract_metadata(uploaded_file, clean_code)
    
    c1, c2, c3 = st.columns(3)
    c1.info(f"**File:** {meta['file_name']}")
    c2.info(f"**Role:** {meta['role']}")
    c3.info(f"**Size:** {meta['size_kb']} KB")

    # --- STEP 2: FORENSIC DOCUMENTATION ---
    if st.button("📝 Phase 1: Generate Forensic Documentation", type="primary", use_container_width=True):
        with st.status("Performing deep-dive forensic logic extraction...", expanded=True) as status:
            doc_results = st.session_state.analyzer.generate_documentation(clean_code)
            st.session_state.doc = doc_results
            st.session_state.clean_code = clean_code
            status.update(label="Forensic Analysis Complete!", state="complete")

# --- STEP 3: READABLE FORENSIC DASHBOARD ---
if "doc" in st.session_state:
    doc = st.session_state.doc
    metrics = st.session_state.analyzer.calculate_dashboard_metrics(doc)
    
    st.divider()
    st.header("📑 Phase 2: Technical & Functional Specification")
    
    # Dashboard Metrics / Heatmap
    d_col1, d_col2, d_col3 = st.columns(3)
    with d_col1:
        st.metric("AI Confidence", metrics['confidence_pct'])
    with d_col2:
        st.markdown(f"**Dashboard Status:** <span class='{metrics['color']}'>{metrics['zone']}</span>", unsafe_allow_value=True)
    with d_col3:
        st.metric("Legacy Complexity", f"{metrics['complexity']}/10")

    # READABLE KNOWLEDGE AREA (High Contrast Report Card)
    st.markdown(f"""
    <div class="report-card">
        <h3>1. Executive System Summary</h3>
        <p>{doc.get('summary', 'No summary available.')}</p>
        
        <h3>2. Comprehensive Business Logic Deep-Dive</h3>
        <p>{doc.get('description', 'No deep-dive documentation generated.')}</p>
        
        <h3>3. External Dependencies & Dependencies</h3>
        <p>{", ".join(doc.get('dependencies', ['No external dependencies detected.']))}</p>
    </div>
    """, unsafe_allow_value=True)

    # Detailed Forensic Tabs
    tab_logic, tab_data = st.tabs(["⚙️ Functional Unit Analysis", "📊 Data Dictionary"])
    
    with tab_logic:
        st.subheader("Granular Logic Breakdown per Procedure")
        st.table(doc.get("functions", []))
    
    with tab_data:
        st.subheader("Legacy Variable Mapping (Data Dictionary)")
        st.write("Mapping of cryptic legacy names to business roles:")
        st.table(doc.get("data_dictionary", []))

    # --- STEP 4: UNIFIED SYNTHESIS ---
    st.divider()
    st.header(f"⚙️ Phase 3: Unified Synthesis ({target_lang})")
    
    if st.button(f"🚀 Execute Unified Transformation", type="primary", use_container_width=True):
        ctx = get_script_run_ctx()
        
        # Setup slots for streaming
        col_code, col_test = st.columns(2)
        with col_code:
            st.subheader(f"Modern {target_lang} Code")
            code_placeholder = st.empty()
        with col_test:
            st.subheader("JUnit / Unit Test Suite")
            test_placeholder = st.empty()

        result_collector = {"code": "", "tests": ""}
        
        # Launch Thread for Azure Streaming
        t = threading.Thread(
            target=unified_transformation_worker,
            args=(st.session_state.clean_code, doc, target_lang, code_placeholder, test_placeholder, result_collector)
        )
        add_script_run_ctx(t, ctx)
        t.start()
        
        with st.spinner("Synthesizing modern architecture and validating logic..."):
            t.join() # Wait for completion
        
        st.success("Modernization successful! Review the transformed code and tests below.")
        st.session_state.final_results = result_collector

# --- FOOTER ---
if "final_results" in st.session_state:
    st.info("💡 **Developer Note:** The generated code follows 'Vanilla' standards. External dependencies have been mocked in the Test Suite for immediate runnability.")
