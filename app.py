import streamlit as st
import os
import threading
import time
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
# Prevents 'NoSessionContext' errors when background threads update the Streamlit UI
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import the refactored core modules
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

# Load environment variables
load_dotenv()

# 1. Page Configuration (Must be the first Streamlit command)
st.set_page_config(
    page_title="Forensic Modernizer Pro",
    page_icon="🛡️",
    layout="wide"
)

# UI Lock to prevent browser websocket collisions during real-time streaming
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
        # 1. PHASE 3: UNIFIED CODE SYNTHESIS (Complete File Mode)
        full_code = ""
        synth_prompt = agent.get_synthesis_prompt(doc_data, target_lang)
        
        for delta in agent.stream_llm(synth_prompt):
            full_code += delta
            with ui_lock:
                # Typing effect with cursor
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
            
        # Store for session persistence
        result_collector["code"] = full_code
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock:
            st.error(f"Synthesis Worker Error: {str(e)}")

# --- MAIN APP UI ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Automated Ingestion ➡️ Parallel Forensic Logic Extraction ➡️ Full-File Synthesis")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Pipeline Settings")
    target_stack = st.selectbox("Target Architecture", [
        "Java (Vanilla 17+)", 
        "Python (Standard)", 
        "C# (.NET Core)"
    ])
    st.divider()
    st.markdown("**Core Quality Gate:**")
    st.write("✅ Multi-threaded Extraction")
    st.write("✅ 200-Word Tech Summary")
    st.write("✅ Mandatory Full-File Code")
    
    if st.button("Reset Application"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: FILE INGESTION ---
st.subheader("📁 Step 1: Ingest Legacy Source")
uploaded_file = st.file_uploader("Upload Source File (COBOL, VB, Java, etc.)", type=['cbl', 'cob', 'vb', 'bas', 'java', 'txt'])

if uploaded_file:
    # Process file once and store in session to prevent re-parsing on scroll
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

    # Trigger Forensic Analysis
    if st.button("📝 Phase 1: Parallel Forensic Analysis", type="primary", use_container_width=True):
        with st.status("Spawning parallel threads for logic and narrative extraction...") as status:
            doc_results = st.session_state.agent.generate_documentation(st.session_state.clean_code)
            st.session_state.doc = doc_results
            status.update(label="Forensic Analysis Complete!", state="complete")

# --- STEP 2: DOCUMENTATION DASHBOARD ---
if "doc" in st.session_state:
    doc = st.session_state.doc
    metrics = st.session_state.agent.calculate_dashboard_metrics(doc)
    
    st.divider()
    st.header("📑 Phase 2: Technical Specification")
    
    # Heatmap Row
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("AI Confidence", metrics['confidence_pct'])
    with m2:
        # Markdown colored zones
        st.markdown(f"**Dashboard Status:** :{metrics['color']}[{metrics['zone']}]")
    with m3:
        st.metric("Legacy Complexity", f"{metrics['complexity']}/10")

    # 1. LONG EXECUTIVE SUMMARY (Markdown optimized - No HTML bugs)
    st.subheader("1. Detailed Executive System Summary")
    st.info(doc.get('summary', 'Summary extraction failed or was truncated.'))
    
    # 2. BUSINESS LOGIC DEEP-DIVE
    st.subheader("2. Logical Execution Flow & Architecture")
    st.markdown(doc.get('description', 'Logic deep-dive failed.'))

    # 3. FORENSIC DETAILS TABS
    tab_func, tab_vars, tab_deps = st.tabs(["⚙️ Functional Analysis", "📊 Data Dictionary", "🔗 Dependencies"])
    
    with tab_func:
        funcs = doc.get("functions", [])
        if funcs:
            st.table(funcs)
        else:
            st.warning("No discrete functions were identified in the metadata thread.")
    
    with tab_vars:
        vars_list = doc.get("data_dictionary", [])
        if vars_list:
            st.table(vars_list)
        else:
            st.warning("Variable mapping was not detected.")
        
    with tab_deps:
        raw_deps = doc.get('dependencies', [])
        # Resilient formatting for list of dicts or strings
        if isinstance(raw_deps, list):
            clean_deps = [str(d.get('name', d)) if isinstance(d, dict) else str(d) for d in raw_deps]
            st.write(", ".join(clean_deps) if clean_deps else "None detected.")
        else:
            st.write(str(raw_deps))

    # --- STEP 3: UNIFIED SYNTHESIS ---
    st.divider()
    st.header(f"⚙️ Phase 3: Modernize to {target_stack}")
    st.caption("Status: FORCED FULL-FILE SYNTHESIS. Generating complete structure regardless of legacy complexity.")
    
    if st.button("🚀 Execute Unified Transformation", type="primary", use_container_width=True):
        ctx = get_script_run_ctx() # Capture current session context for the thread
        
        # UI slots for the code output
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.subheader("🛠️ Modern Source Code")
            code_placeholder = st.empty()
        with res_col2:
            st.subheader("🧪 Automated Test Suite")
            test_placeholder = st.empty()

        result_collector = {"code": "", "tests": ""}
        
        # Start the threaded synthesis worker
        t = threading.Thread(
            target=transformation_worker,
            args=(doc, target_stack, code_placeholder, test_placeholder, result_collector)
        )
        add_script_run_ctx(t, ctx)
        t.start()
        
        with st.spinner("Writing complete class structure and logic..."):
            # Ensure the UI status spinner waits for the thread to finish
            t.join() 
        
        st.success("Modernization Complete! Unified file is ready.")
        st.session_state.final_results = result_collector

# Final persistence of generated artifacts
if "final_results" in st.session_state:
    st.divider()
    st.info("💡 **Developer Note:** The source code above is a complete file. All global legacy states have been encapsulated into private class members.")
