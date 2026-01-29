import streamlit as st
import os
import threading
import time
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import specialized core modules
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

# Load environment variables
load_dotenv()

# 1. Page Configuration
st.set_page_config(
    page_title="Ultra-Parallel Modernizer",
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
st.markdown("Parallel Logic Extraction ➡️ Segmented Synthesis ➡️ Complete File Assembly")

# Sidebar
with st.sidebar:
    st.header("Pipeline Settings")
    target_stack = st.selectbox("Target Architecture", [
        "Java (Vanilla 17+)", 
        "Python (Standard)", 
        "C# (.NET Core)"
    ])
    st.divider()
    if st.button("Reset Application"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: INGESTION ---
st.subheader("📁 Step 1: Ingest Legacy Source")
uploaded_file = st.file_uploader("Upload Source File", type=['cbl', 'cob', 'vb', 'java', 'txt'])

if uploaded_file:
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

    if st.button("📝 Phase 1: Parallel Forensic Analysis", type="primary", use_container_width=True):
        with st.status("Analyzing voluminous code using parallel extraction...") as status:
            doc_results = st.session_state.agent.generate_documentation(st.session_state.clean_code)
            st.session_state.doc = doc_results
            status.update(label="Forensic Analysis Complete!", state="complete")

# --- STEP 2: DOCUMENTATION DASHBOARD ---
if "doc" in st.session_state:
    doc = st.session_state.doc
    metrics = st.session_state.agent.calculate_dashboard_metrics(doc)
    
    st.divider()
    st.header("📑 Phase 2: Technical Specification")
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("AI Confidence", metrics['confidence_pct'])
    with m2:
        st.markdown(f"**Dashboard Status:** :{metrics['color']}[{metrics['zone']}]")
    with m3:
        st.metric("Legacy Complexity", f"{metrics['complexity']}/10")

    # Display 300-400 Word Technical Summary
    st.subheader("1. Detailed Executive System Summary")
    st.info(doc.get('summary', 'Summary extraction failed.'))
    
    st.subheader("2. Logical Execution Flow")
    st.markdown(doc.get('description', 'Deep-dive failed.'))

    tab_func, tab_vars = st.tabs(["⚙️ Functional Analysis", "📊 Data Dictionary"])
    with tab_func: st.table(doc.get("functions", []))
    with tab_vars: st.table(doc.get("data_dictionary", []))

    # --- STEP 3: SEGMENTED PARALLEL SYNTHESIS ---
    st.divider()
    st.header(f"🚀 Phase 3: Segmented Modernization ({target_stack})")
    st.caption("Status: Multi-stream assembly enabled to prevent token truncation.")
    
    if st.button("Execute Parallel Transformation", type="primary", use_container_width=True):
        ctx = get_script_run_ctx()
        
        # UI Slots for the dynamic dual-stream assembly
        col_code, col_test = st.columns(2)
        with col_code:
            st.subheader("🛠️ Unified Source Code")
            skel_slot = st.empty()
            logic_slot = st.empty()
            footer_slot = st.empty()
        with col_test:
            st.subheader("🧪 Automated Test Suite")
            test_slot = st.empty()

        # Shared containers for final assembly and download
        synthesis_results = {"skeleton": "", "logic": "", "tests": ""}

        def skeleton_worker():
            agent = st.session_state.agent
            prompt = agent.get_skeleton_prompt(doc, target_stack)
            for delta in agent.stream_llm(prompt):
                synthesis_results["skeleton"] += delta
                with ui_lock:
                    skel_slot.code(synthesis_results["skeleton"] + " ▌", language="java")
            with ui_lock: skel_slot.code(synthesis_results["skeleton"])

        def logic_worker():
            agent = st.session_state.agent
            prompt = agent.get_methods_prompt(doc, target_stack)
            for delta in agent.stream_llm(prompt):
                synthesis_results["logic"] += delta
                with ui_lock:
                    logic_slot.code(synthesis_results["logic"] + " ▌", language="java")
            with ui_lock: 
                logic_slot.code(synthesis_results["logic"])
                # Add closing brace for Java/C#
                if "Java" in target_stack or "C#" in target_stack:
                    footer_slot.code("}")

        # Start Parallel Synthesis Threads
        t1 = threading.Thread(target=skeleton_worker)
        t2 = threading.Thread(target=logic_worker)
        add_script_run_ctx(t1, ctx); add_script_run_ctx(t2, ctx)
        
        t1.start(); t2.start()
        
        with st.spinner("Assembling file architecture in parallel..."):
            t1.join(); t2.join()

        # Assemble Final Code for testing and download
        closing = "}" if ("Java" in target_stack or "C#" in target_stack) else ""
        final_code = f"{synthesis_results['skeleton']}\n{synthesis_results['logic']}\n{closing}"
        st.session_state.assembled_code = final_code

        # Start Testing Phase
        def test_worker():
            agent = st.session_state.agent
            prompt = agent.get_test_prompt(final_code, target_stack)
            for delta in agent.stream_llm(prompt):
                synthesis_results["tests"] += delta
                with ui_lock:
                    test_slot.code(synthesis_results["tests"] + " ▌", language="java")
            with ui_lock: test_slot.code(synthesis_results["tests"])
            st.session_state.final_tests = synthesis_results["tests"]

        t3 = threading.Thread(target=test_worker)
        add_script_run_ctx(t3, ctx)
        t3.start(); t3.join()
        
        st.success("Modernization Complete! File is unified and assembled.")

# --- STEP 4: DOWNLOAD PROVISION ---
if "assembled_code" in st.session_state:
    st.divider()
    st.subheader("📥 Step 4: Download Results")
    
    ext = get_extension(target_stack)
    
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            label=f"💾 Download Modernized {ext.upper()} File",
            data=st.session_state.assembled_code,
            file_name=f"modernized_component.{ext}",
            mime="text/plain",
            use_container_width=True
        )
    with dl_col2:
        st.download_button(
            label="🧪 Download Unit Test Suite",
            data=st.session_state.get("final_tests", ""),
            file_name=f"test_suite.{ext}",
            mime="text/plain",
            use_container_width=True
        )
