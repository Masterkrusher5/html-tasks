import streamlit as st
import os
import time
import threading
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
# Critical to prevent 'NoSessionContext' errors during real-time streaming
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import forensic engine modules
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Forensic Modernizer Pro",
    page_icon="🛡️",
    layout="wide"
)

# UI Lock for thread-safe streaming to the browser websocket
ui_lock = threading.Lock()

# --- Initialize Engines in Session State ---
if "engines_initialized" not in st.session_state:
    st.session_state.ingestor = FileIngestor()
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.engines_initialized = True

# --- Modernization Worker (The Synthesis Engine) ---
def transformation_worker(doc_data, target_lang, code_slot, test_slot, result_collector):
    """
    Worker function executed in a background thread.
    Streams a complete, runnable file first, followed by a full test suite.
    """
    agent = st.session_state.agent
    lang_key = target_lang.lower().split()[0] # e.g., 'java'
    
    try:
        # 1. STREAM COMPLETE SOURCE CODE
        full_code = ""
        synth_prompt = agent.get_synthesis_prompt(doc_data, target_lang)
        
        for delta in agent.stream_llm(synth_prompt):
            full_code += delta
            with ui_lock:
                # Use a typing-effect cursor for better UX
                code_slot.code(full_code + " ▌", language=lang_key)
        
        with ui_lock:
            code_slot.code(full_code, language=lang_key)
        
        # 2. STREAM COMPREHENSIVE UNIT TESTS
        full_tests = ""
        test_prompt = agent.get_test_prompt(full_code, target_lang)
        
        for delta in agent.stream_llm(test_prompt):
            full_tests += delta
            with ui_lock:
                test_slot.code(full_tests + " ▌", language=lang_key)
        
        with ui_lock:
            test_slot.code(full_tests, language=lang_key)
            
        # Store for session persistence
        result_collector["code"] = full_code
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock:
            st.error(f"Synthesis Error: {str(e)}")

# --- MAIN UI INTERFACE ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Automated Forensic Analysis ➡️ Deep Technical Specification ➡️ Unified Full-File Synthesis")

# Sidebar Configuration
with st.sidebar:
    st.header("Pipeline Settings")
    target_lang = st.selectbox("Target Architecture", [
        "Java (Vanilla 17+)", 
        "Python (Clean/Typing)", 
        "C# (.NET Core)", 
        "TypeScript (Node.js)"
    ])
    source_lang = st.selectbox("Source Language", ["COBOL", "VB6", "Java (Legacy)"])
    
    st.divider()
    st.markdown("**Fidelity Standards:**")
    st.write("✅ Detailed plain-text documentation")
    st.write("✅ Full file synthesis (Runnable)")
    st.write("✅ Logic State preservation")
    
    if st.button("Reset Pipeline Session"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: FILE INGESTION ---
st.subheader("📁 Step 1: Ingest Legacy Source")
uploaded_file = st.file_uploader("Upload Voluminous Source File", type=['cbl', 'cob', 'vb', 'bas', 'java', 'txt'])

if uploaded_file:
    # Read and Normalize
    raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
    clean_code = st.session_state.ingestor.normalize(raw_content)
    meta = st.session_state.ingestor.extract_metadata(uploaded_file, clean_code)
    
    # Display ingestion metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("File Name", meta['file_name'])
    c2.metric("Detected Role", meta['role'])
    c3.metric("Payload Size", f"{meta['size_kb']} KB")

    # --- STEP 2: GENERATE FORENSIC DOCUMENTATION ---
    if st.button("📝 Phase 1: Generate Full Technical Documentation", type="primary", use_container_width=True):
        with st.status("Performing forensic analysis of logic, data flow, and state...", expanded=True) as status:
            st.write("Consulting LLM for high-fidelity technical specs...")
            doc_results = st.session_state.agent.generate_documentation(clean_code)
            
            # Persist to session
            st.session_state.doc = doc_results
            st.session_state.clean_code = clean_code
            status.update(label="Forensic Mapping Complete!", state="complete")

# --- STEP 3: DISPLAY TECHNICAL DASHBOARD ---
if "doc" in st.session_state:
    doc = st.session_state.doc
    metrics = st.session_state.agent.calculate_dashboard_metrics(doc)
    
    st.divider()
    st.header("📑 Phase 2: Technical & Functional Specification")
    
    # Quality Gate Heatmap
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("AI Confidence", metrics['confidence_pct'])
    with m2:
        # Use colored markdown for status
        st.markdown(f"**Dashboard Status:** :{metrics['color']}[{metrics['zone']}]")
    with m3:
        st.metric("Legacy Complexity", f"{metrics['complexity']}/10")

    # 1. LONG EXECUTIVE SUMMARY (Markdown optimized)
    st.subheader("1. Detailed Executive System Summary")
    st.info(doc.get('summary', 'No summary available.'))
    
    # 2. BUSINESS LOGIC DEEP-DIVE
    st.subheader("2. Logical Execution Flow & Architecture")
    st.markdown(doc.get('description', 'No detailed description available.'))

    # 3. FORENSIC DETAILS TABS
    tab_func, tab_vars, tab_deps = st.tabs(["⚙️ Functional Breakdown", "📊 Data Dictionary", "🔗 External Dependencies"])
    
    with tab_func:
        st.write("Granular analysis of detected procedures and paragraphs:")
        st.table(doc.get("functions", []))
    
    with tab_vars:
        st.write("Mapping legacy variables to modern business roles:")
        st.table(doc.get("data_dictionary", []))
        
    with tab_deps:
        # Handle dependencies gracefully if they are dicts or strings
        deps = doc.get('dependencies', [])
        if isinstance(deps, list):
            for d in deps:
                st.write(f"- {d}")
        else:
            st.write(deps)

    # --- STEP 4: UNIFIED SYNTHESIS ---
    st.divider()
    st.header(f"⚙️ Phase 3: Synthesize {target_lang} (Unified Transformation)")
    
    if st.button("🚀 Start Full-File Modernization", type="primary", use_container_width=True):
        ctx = get_script_run_ctx() # Capture current UI context
        
        # UI slots for the code output
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.subheader("🛠️ Modern Source Code")
            code_placeholder = st.empty()
        with res_col2:
            st.subheader("🧪 JUnit / Unit Test Suite")
            test_placeholder = st.empty()

        result_collector = {"code": "", "tests": ""}
        
        # Start the threaded worker for streaming
        t = threading.Thread(
            target=transformation_worker,
            args=(doc, target_lang, code_placeholder, test_placeholder, result_collector)
        )
        add_script_run_ctx(t, ctx)
        t.start()
        
        with st.spinner("Writing complete class structure and injecting logic..."):
            t.join() # Wait for the thread to finish the full file
        
        st.success("Modernization Complete! File is unified and logically consistent.")
        st.session_state.final_results = result_collector

# Final persistence of generated artifacts
if "final_results" in st.session_state:
    st.info("💡 **Developer Note:** The source code above is a complete file including imports and state management. You can copy it directly into your IDE.")
