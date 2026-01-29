import streamlit as st
import os
import threading
import time
import json
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
# This is mandatory to prevent 'NoSessionContext' errors during parallel streaming
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import our specialized core modules
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

# Load environment variables
load_dotenv()

# 1. Page Configuration (Must be first)
st.set_page_config(
    page_title="Forensic Modernizer Pro",
    page_icon="🛡️",
    layout="wide"
)

# UI Lock for thread-safe websocket communication
ui_lock = threading.Lock()

# 2. Initialize Engines in Session State
if "agent" not in st.session_state:
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.ingestor = FileIngestor()

# --- SYNTHESIS WORKER (Threaded Logic) ---
def transformation_worker(doc_data, target_lang, code_slot, test_slot, result_collector):
    """
    Worker function executed in a dedicated thread.
    Streams a COMPLETE, runnable file structure followed by unit tests.
    """
    agent = st.session_state.agent
    lang_key = "java" if "Java" in target_lang else "python" if "Python" in target_lang else "csharp"
    
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
            
        # Persist results so they don't disappear on next UI interaction
        result_collector["code"] = full_code
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock:
            st.error(f"Synthesis Worker Error: {str(e)}")

# --- MAIN APP UI ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Automated Forensic Analysis ➡️ Deep Technical Specification ➡️ Unified Transformation")

# Sidebar
with st.sidebar:
    st.header("Pipeline Settings")
    target_stack = st.selectbox("Target Architecture", [
        "Java (Vanilla 17+)", 
        "Python (Clean/Typing)", 
        "C# (.NET Core)"
    ])
    st.divider()
    if st.button("Clear Session & Reset"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: INGESTION ---
st.subheader("📁 Step 1: Ingest Legacy Source")
uploaded_file = st.file_uploader("Upload Source File (Voluminous code support)", type=['cbl', 'cob', 'vb', 'java', 'txt'])

if uploaded_file:
    # Process file once and store in session
    if "clean_code" not in st.session_state or st.session_state.get("current_file") != uploaded_file.name:
        raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
        st.session_state.clean_code = st.session_state.ingestor.normalize(raw_content)
        st.session_state.meta = st.session_state.ingestor.extract_metadata(uploaded_file, st.session_state.clean_code)
        st.session_state.current_file = uploaded_file.name

    meta = st.session_state.meta
    c1, c2, c3 = st.columns(3)
    c1.metric("File Name", meta['file_name'])
    c2.metric("Detected Role", meta['role'])
    c3.metric("Payload Size", f"{meta['size_kb']} KB")

    # Trigger Phase 1
    if st.button("📝 Phase 1: Generate Forensic Documentation", type="primary", use_container_width=True):
        with st.status("Analyzing system architecture and logic flow...") as status:
            doc_results = st.session_state.agent.generate_documentation(st.session_state.clean_code)
            st.session_state.doc = doc_results
            status.update(label="Forensic Analysis Complete!", state="complete")

# --- STEP 2: DOCUMENTATION DASHBOARD ---
if "doc" in st.session_state:
    doc = st.session_state.doc
    metrics = st.session_state.agent.calculate_dashboard_metrics(doc)
    
    st.divider()
    st.header("📑 Phase 2: Technical Specification")
    
    # Heatmap row
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("AI Confidence", metrics['confidence_pct'])
    with m2:
        st.markdown(f"**Dashboard Status:** :{metrics['color']}[{metrics['zone']}]")
    with m3:
        st.metric("Legacy Complexity", f"{metrics['complexity']}/10")

    # 1. LONG EXECUTIVE SUMMARY (Uses st.info for high-contrast scrolling text)
    st.subheader("1. Detailed Executive System Summary")
    st.markdown(doc.get('summary', 'Summary Extraction Failed'))
    
    # 2. BUSINESS LOGIC DEEP-DIVE
    st.subheader("2. Logical Execution Flow & Architecture")
    st.markdown(doc.get('description', 'Logic deep-dive failed.'))

    # 3. FORENSIC DETAILS TABS
    tab_func, tab_vars, tab_deps = st.tabs(["⚙️ Functional Analysis", "📊 Data Dictionary", "🔗 Dependencies"])
    
    with tab_func:
        st.write("Granular breakdown of procedures and business rules:")
        st.table(doc.get("functions", []))
    
    with tab_vars:
        st.write("Mapping legacy variables to modern business roles:")
        st.table(doc.get("data_dictionary", []))
        
    with tab_deps:
        raw_deps = doc.get('dependencies', [])
        # Resilient dependency list formatting
        if isinstance(raw_deps, list):
            clean_deps = [str(d.get('name', d)) if isinstance(d, dict) else str(d) for d in raw_deps]
            st.write(", ".join(clean_deps) if clean_deps else "No external dependencies detected.")
        else:
            st.write(str(raw_deps))

    # --- STEP 3: UNIFIED SYNTHESIS ---
    st.divider()
    st.header(f"⚙️ Phase 3: Unified Synthesis ({target_stack})")
    
    if st.button("🚀 Execute Unstoppable Modernization", type="primary", use_container_width=True):
        ctx = get_script_run_ctx() # Bind the UI context to the thread
        
        # Create UI slots for the code output
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.subheader("🛠️ Modern Source Code")
            code_placeholder = st.empty()
        with res_col2:
            st.subheader("🧪 Automated Test Suite")
            test_placeholder = st.empty()

        # Temporary result holder
        res_collector = {"code": "", "tests": ""}
        
        # Start background thread
        t = threading.Thread(
            target=transformation_worker,
            args=(doc, target_stack, code_placeholder, test_placeholder, res_collector)
        )
        add_script_run_ctx(t, ctx)
        t.start()
        
        with st.spinner("Synthesizing class structure... Failure is not an option."):
            # We join to ensure the status bar waits for the thread to finish
            t.join() 
        
        st.success("Modernization Successful! Unified file generated.")
        st.session_state.final_results = res_collector

# Retention Display (Shows results if they were previously generated)
if "final_results" in st.session_state:
    st.divider()
    st.info("💡 **Architect Note:** This code is a single cohesive file with imports, class members, and logically mapped business rules.")
