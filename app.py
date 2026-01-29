import streamlit as st
import os
import threading
import time
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
# Necessary to prevent 'NoSessionContext' errors when background threads update the UI
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import specialized core modules
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

# Load environment variables
load_dotenv()

# 1. Page Configuration
st.set_page_config(
    page_title="Forensic Modernizer Pro",
    page_icon="🛡️",
    layout="wide"
)

# UI Lock for thread-safe websocket communication
ui_lock = threading.Lock()

# 2. Initialize Engines
if "agent" not in st.session_state:
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.ingestor = FileIngestor()

# --- HELPER: GET FILE EXTENSION ---
def get_extension(stack):
    if "Java" in stack: return "java"
    if "Python" in stack: return "py"
    if "C#" in stack: return "cs"
    return "txt"

# --- MAIN UI INTERFACE ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Dual-Pipeline Parallel Engine: **Documentation** and **Synthesis** streams independently.")

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("Pipeline Settings")
    target_stack = st.selectbox("Target Architecture", [
        "Java (Vanilla 17+)", 
        "Python (Standard)", 
        "C# (.NET Core)"
    ])
    st.divider()
    st.markdown("**Performance Mode:**")
    st.write("🚀 Parallel Threading: Enabled")
    st.write("🚀 Truncation Protection: Active")
    
    if st.button("Reset Application"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: FILE INGESTION ---
st.subheader("📁 Step 1: Ingest Legacy Source")
uploaded_file = st.file_uploader("Upload Legacy File", type=['cbl', 'cob', 'vb', 'java', 'txt'])

if uploaded_file:
    # Handle file processing and persistence
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

    # --- STEP 2: START PARALLEL MODERNIZATION ---
    if st.button("🚀 Start Dual-Pipeline Modernization", type="primary", use_container_width=True):
        ctx = get_script_run_ctx()
        
        # --- UI LAYOUT (VERTICAL STACK) ---
        
        # TOP SECTION: DOCUMENTATION
        st.divider()
        st.subheader("📑 Phase 1: Technical Documentation (300-400 words)")
        doc_slot = st.empty()
        metrics_slot = st.empty()
        
        # BOTTOM SECTION: CODE SYNTHESIS
        st.divider()
        st.subheader(f"🛠️ Phase 2: Unified Code Synthesis ({target_stack})")
        code_slot = st.empty()
        
        st.subheader("🧪 Phase 3: Automated Test Suite")
        test_slot = st.empty()

        # Shared containers for results and downloads
        results = {"doc": "", "code": "", "tests": ""}

        # --- WORKER 1: THE ANALYST (Documentation) ---
        def analyst_worker():
            agent = st.session_state.agent
            prompt = agent.get_documentation_prompt(st.session_state.clean_code)
            for delta in agent.stream_llm(prompt, max_tokens=2000):
                results["doc"] += delta
                with ui_lock:
                    doc_slot.markdown(results["doc"] + " ▌")
            
            with ui_lock:
                doc_slot.markdown(results["doc"])
                # Generate heuristic metrics once documentation is finished
                metrics = agent.calculate_dashboard_metrics(results["doc"])
                metrics_slot.success(f"**Confidence:** {metrics['confidence_pct']} | **Zone:** {metrics['zone']}")
                st.session_state.final_doc = results["doc"]

        # --- WORKER 2: THE CODER (Source-to-Target) ---
        def coder_worker():
            agent = st.session_state.agent
            prompt = agent.get_synthesis_prompt(st.session_state.clean_code, target_stack)
            lang_key = get_extension(target_stack)
            
            for delta in agent.stream_llm(prompt, max_tokens=4000):
                results["code"] += delta
                with ui_lock:
                    code_slot.code(results["code"] + " ▌", language=lang_key)
            
            with ui_lock:
                code_slot.code(results["code"], language=lang_key)
                st.session_state.final_code = results["code"]

        # --- LAUNCH PARALLEL THREADS ---
        t1 = threading.Thread(target=analyst_worker)
        t2 = threading.Thread(target=coder_worker)
        
        add_script_run_ctx(t1, ctx)
        add_script_run_ctx(t2, ctx)
        
        t1.start()
        t2.start()
        
        # Wait for the Coder to finish so we can generate tests based on the code
        t2.join() 
        
        # --- WORKER 3: THE QA (Triggered after Code is ready) ---
        def test_worker():
            agent = st.session_state.agent
            lang_key = get_extension(target_stack)
            prompt = agent.get_test_prompt(results["code"], target_stack)
            
            for delta in agent.stream_llm(prompt, max_tokens=2000):
                results["tests"] += delta
                with ui_lock:
                    test_slot.code(results["tests"] + " ▌", language=lang_key)
            
            with ui_lock:
                test_slot.code(results["tests"], language=lang_key)
                st.session_state.final_tests = results["tests"]

        t3 = threading.Thread(target=test_worker)
        add_script_run_ctx(t3, ctx)
        t3.start()
        t3.join()
        
        st.success("🏁 All modernization pipelines completed successfully.")

# --- STEP 3: DOWNLOAD & PERSISTENCE ---
if "final_code" in st.session_state:
    st.divider()
    st.subheader("📥 Step 3: Download Modernized Artifacts")
    
    ext = get_extension(target_stack)
    
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            label=f"💾 Download {ext.upper()} Source",
            data=st.session_state.final_code,
            file_name=f"modernized_component.{ext}",
            mime="text/plain",
            use_container_width=True
        )
    with dl_col2:
        if "final_tests" in st.session_state:
            st.download_button(
                label="🧪 Download Unit Tests",
                data=st.session_state.final_tests,
                file_name=f"test_suite.{ext}",
                mime="text/plain",
                use_container_width=True
            )

# Show logic recap if doc exists in state
if "final_doc" in st.session_state:
    with st.expander("🔍 View Technical Documentation Archive"):
        st.markdown(st.session_state.final_doc)
