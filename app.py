import streamlit as st
import os
import threading
import time
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
# Necessary to prevent 'NoSessionContext' errors when background threads update the UI
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import our specialized core modules
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

# Load environment variables from .env
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Forensic Modernizer Pro",
    page_icon="🛡️",
    layout="wide"
)

# UI Lock to prevent browser websocket collisions during streaming
ui_lock = threading.Lock()

# --- Initialize Engines in Session State ---
if "engines_initialized" not in st.session_state:
    st.session_state.ingestor = FileIngestor()
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.engines_initialized = True

# --- Unified Worker (Thread-Safe Streaming) ---
def transformation_worker(doc_data, target_lang, code_slot, test_slot, result_collector):
    """
    Worker function executed in a dedicated thread.
    1. Streams the full modern code file (Complete with imports/class).
    2. Streams the full unit test file once code is available.
    """
    agent = st.session_state.agent
    # Detect language for syntax highlighting
    lang_key = "java" if "Java" in target_lang else "python" if "Python" in target_lang else "csharp"
    
    try:
        # 1. PHASE 3: UNIFIED CODE SYNTHESIS (Unstoppable Mode)
        full_code = ""
        synth_prompt = agent.get_synthesis_prompt(doc_data, target_lang)
        
        for delta in agent.stream_llm(synth_prompt):
            full_code += delta
            with ui_lock:
                # Live typing effect
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
            
        # Store results for persistence if user navigates away
        result_collector["code"] = full_code
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock:
            st.error(f"Synthesis Error: {str(e)}")

# --- MAIN UI INTERFACE ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Automated Ingestion ➡️ 300+ Word Technical Spec ➡️ Unstoppable Full-File Synthesis")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Pipeline Settings")
    target_lang = st.selectbox("Target Architecture", [
        "Java (Vanilla 17+)", 
        "Python (Clean/Typing)", 
        "C# (.NET Core)"
    ])
    st.divider()
    st.markdown("**Standards Enforced:**")
    st.write("✅ Multi-paragraph Summary")
    st.write("✅ Private Member State")
    st.write("✅ No Framework Magic")
    
    if st.button("Reset Everything"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: FILE INGESTION ---
st.subheader("📁 Step 1: Ingest Legacy Source")
uploaded_file = st.file_uploader("Upload Source File", type=['cbl', 'cob', 'vb', 'java', 'txt'])

if uploaded_file:
    # Handle voluminous code ingestion
    raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
    clean_code = st.session_state.ingestor.normalize(raw_content)
    meta = st.session_state.ingestor.extract_metadata(uploaded_file, clean_code)
    
    # Metadata Dashboard
    c1, c2, c3 = st.columns(3)
    c1.metric("File Name", meta['file_name'])
    c2.metric("Detected Role", meta['role'])
    c3.metric("Payload Size", f"{meta['size_kb']} KB")

    # --- STEP 2: FORENSIC DOCUMENTATION ---
    if st.button("📝 Phase 1: Generate Deep-Dive Documentation", type="primary", use_container_width=True):
        with st.status("Analyzing system architecture and logic flow...", expanded=True) as status:
            doc_results = st.session_state.agent.generate_documentation(clean_code)
            st.session_state.doc = doc_results
            st.session_state.clean_code = clean_code
            status.update(label="Forensic Specification Complete!", state="complete")

# --- STEP 3: DISPLAY FORENSIC DASHBOARD ---
if "doc" in st.session_state:
    doc = st.session_state.doc
    metrics = st.session_state.agent.calculate_dashboard_metrics(doc)
    
    st.divider()
    st.header("📑 Phase 2: Technical Specification")
    
    # Risk Heatmap Row
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("AI Confidence", metrics['confidence_pct'])
    with m2:
        st.markdown(f"**Dashboard Status:** :{metrics['color']}[{metrics['zone']}]")
    with m3:
        st.metric("Legacy Complexity", f"{metrics['complexity']}/10")

    # 1. LONG EXECUTIVE SUMMARY (Readability focus - No HTML)
    st.subheader("1. Detailed Executive System Summary")
    st.info(doc.get('summary', 'Summary generation failed.'))
    
    # 2. BUSINESS LOGIC DEEP-DIVE
    st.subheader("2. Logical Execution Flow & Architecture")
    st.markdown(doc.get('description', 'Logic deep-dive failed.'))

    # 3. FORENSIC DETAILS TABS
    tab_func, tab_vars, tab_deps = st.tabs(["⚙️ Functional Analysis", "📊 Data Dictionary", "🔗 Dependencies"])
    
    with tab_func:
        st.write("Granular breakdown of procedures and business rules:")
        st.table(doc.get("functions", []))
    
    with tab_vars:
        st.write("Variable mapping from legacy fields to business roles:")
        st.table(doc.get("data_dictionary", []))
        
    with tab_deps:
        deps = doc.get('dependencies', [])
        st.write(deps if deps else "No external dependencies detected.")

    # --- STEP 4: UNIFIED SYNTHESIS (Unstoppable) ---
    st.divider()
    st.header(f"⚙️ Phase 3: Full-File Modernization ({target_lang})")
    st.caption("Status: FORCED SYNTHESIS ENABLED. Generating complete file structure regardless of risk zone.")
    
    if st.button("🚀 Execute Unified Transformation", type="primary", use_container_width=True):
        ctx = get_script_run_ctx() # Bind the UI context to the thread
        
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
            args=(doc, target_lang, code_placeholder, test_placeholder, result_collector)
        )
        add_script_run_ctx(t, ctx)
        t.start()
        
        with st.spinner("Synthesizing class structure and logic... failure is not an option."):
            t.join() # Wait for the background thread to finish completely
        
        st.success("Modernization Complete! Logic and state preserved in unified file.")
        st.session_state.final_results = result_collector

# Retention of results
if "final_results" in st.session_state:
    st.divider()
    st.info("💡 **Architect's Note:** The code above is a complete file. Global legacy state has been encapsulated into class members.")
