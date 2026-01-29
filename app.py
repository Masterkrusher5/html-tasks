import streamlit as st
import os
import threading
import time
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import core modules
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

# UI Lock for thread-safe streaming
ui_lock = threading.Lock()

# 2. Initialize Engines
if "agent" not in st.session_state:
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.ingestor = FileIngestor()

# --- WORKER: CODE SYNTHESIS & TESTING ---
def synthesis_worker(clean_code, target_lang, code_slot, test_slot, result_collector):
    """
    Background worker that streams the Full Code and then the Test Suite.
    """
    agent = st.session_state.agent
    lang_key = "java" if "Java" in target_lang else "python" if "Python" in target_lang else "csharp"
    
    try:
        # 1. STREAM CODE (Using the Direct Source-to-Target Prompt)
        full_code = ""
        # Note: We pass clean_code directly, bypassing the Doc JSON to avoid truncation
        synth_prompt = agent.get_synthesis_prompt(clean_code, target_lang)
        
        for delta in agent.stream_llm(synth_prompt, max_tokens=4000):
            full_code += delta
            with ui_lock:
                code_slot.code(full_code + " ▌", language=lang_key)
        
        with ui_lock:
            code_slot.code(full_code, language=lang_key)
        
        # 2. STREAM TESTS
        full_tests = ""
        test_prompt = agent.get_test_prompt(full_code, target_lang)
        
        for delta in agent.stream_llm(test_prompt, max_tokens=2000):
            full_tests += delta
            with ui_lock:
                test_slot.code(full_tests + " ▌", language=lang_key)
        
        with ui_lock:
            test_slot.code(full_tests, language=lang_key)
            
        # Save results
        result_collector["code"] = full_code
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock:
            st.error(f"Synthesis Error: {str(e)}")

# --- MAIN UI ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Automated Ingestion ➡️ Forensic Analysis ➡️ Full-File Synthesis")

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
uploaded_file = st.file_uploader("Upload Legacy File", type=['cbl', 'cob', 'vb', 'java', 'txt'])

if uploaded_file:
    # Process file once
    if "clean_code" not in st.session_state or st.session_state.get("current_file") != uploaded_file.name:
        raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
        st.session_state.clean_code = st.session_state.ingestor.normalize(raw_content)
        st.session_state.meta = st.session_state.ingestor.extract_metadata(uploaded_file, st.session_state.clean_code)
        st.session_state.current_file = uploaded_file.name
        # Clear previous results on new file load
        if "doc_text" in st.session_state: del st.session_state.doc_text
        if "final_results" in st.session_state: del st.session_state.final_results

    meta = st.session_state.meta
    c1, c2, c3 = st.columns(3)
    c1.metric("File Name", meta['file_name'])
    c2.metric("Detected Role", meta['role'])
    c3.metric("Payload Size", f"{meta['size_kb']} KB")

    # --- STEP 2: FORENSIC DOCUMENTATION (Streaming Markdown) ---
    st.divider()
    st.subheader("📝 Phase 1: Forensic Documentation")
    
    if st.button("Start Analysis", type="primary"):
        doc_placeholder = st.empty()
        full_doc = ""
        
        # Stream the documentation (Narrative Mode)
        prompt = st.session_state.agent.get_documentation_prompt(st.session_state.clean_code)
        
        for delta in st.session_state.agent.stream_llm(prompt, max_tokens=2000):
            full_doc += delta
            doc_placeholder.markdown(full_doc + " ▌")
        
        doc_placeholder.markdown(full_doc)
        st.session_state.doc_text = full_doc

    # Display persisted documentation and metrics
    if "doc_text" in st.session_state:
        if not st.button("Regenerate Analysis", key="regen_btn"): # Simple trick to keep doc visible
             st.markdown(st.session_state.doc_text)
        
        # Calculate Heuristic Metrics based on text length/content
        metrics = st.session_state.agent.calculate_dashboard_metrics(st.session_state.doc_text)
        
        st.info(f"**Analysis Confidence:** {metrics['confidence_pct']} | **Risk Zone:** {metrics['zone']}")

        # --- STEP 3: UNIFIED SYNTHESIS ---
        st.divider()
        st.subheader(f"🚀 Phase 2: Modernization ({target_stack})")
        
        if st.button("Execute Full-File Synthesis", type="primary"):
            ctx = get_script_run_ctx()
            
            col_code, col_test = st.columns(2)
            with col_code:
                st.subheader("Modern Source Code")
                code_placeholder = st.empty()
            with col_test:
                st.subheader("Unit Test Suite")
                test_placeholder = st.empty()

            result_collector = {"code": "", "tests": ""}
            
            # Start Background Thread
            t = threading.Thread(
                target=synthesis_worker,
                args=(st.session_state.clean_code, target_stack, code_placeholder, test_placeholder, result_collector)
            )
            add_script_run_ctx(t, ctx)
            t.start()
            
            with st.spinner("Synthesizing complete file structure..."):
                t.join()
            
            st.success("Modernization Complete.")
            st.session_state.final_results = result_collector

# --- DOWNLOAD SECTION ---
if "final_results" in st.session_state:
    st.divider()
    st.subheader("📥 Downloads")
    
    ext = "java" if "Java" in target_stack else "py" if "Python" in target_stack else "cs"
    
    d1, d2 = st.columns(2)
    with d1:
        st.download_button("💾 Download Source Code", st.session_state.final_results["code"], file_name=f"modernized.{ext}")
    with d2:
        st.download_button("🧪 Download Tests", st.session_state.final_results["tests"], file_name=f"tests.{ext}")
