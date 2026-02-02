import streamlit as st
import threading
import os
import time
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
# Critical to prevent 'NoSessionContext' errors during real-time streaming
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

# 2. Initialize Engines in Session State
if "agent" not in st.session_state:
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.ingestor = FileIngestor()

# --- CUSTOM CSS FOR HIGH-CONTRAST READABILITY ---
st.markdown("""
    <style>
    .report-container {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        color: #2c3e50 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .stCodeBlock { border: 1px solid #d1d8e0 !important; }
    </style>
""", unsafe_allow_html=True)

# --- MAIN UI INTERFACE ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.markdown("Chained Logic Extraction ➡️ Multi-Threaded Synthesis ➡️ Unified Assembly")

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("Pipeline Settings")
    target_stack = st.selectbox("Target Architecture", [
        "Java (Vanilla 17+)", 
        "Python (Standard)", 
        "C# (.NET Core)"
    ])
    st.divider()
    st.info("🚀 **High-Resiliency Mode:**\nLogic is converted piece-by-piece. Updates are throttled to ensure UI stability during high-volume streaming.")
    
    if st.button("Reset Application"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: INGESTION & FORENSIC CHUNKING ---
uploaded_file = st.file_uploader("Upload Legacy Source File", type=['cbl', 'cob', 'vb', 'bas', 'frm', 'java', 'txt'])

if uploaded_file:
    # Handle ingestion and persistence
    if "chunks" not in st.session_state or st.session_state.get("current_file") != uploaded_file.name:
        raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
        norm_code = st.session_state.ingestor.normalize(raw_content)
        
        with st.spinner("Analyzing File Structure & Extracting Global Context..."):
            # 1. Chunking
            parsed_data = st.session_state.ingestor.chunk_code(norm_code, uploaded_file.name)
            st.session_state.chunks = parsed_data['chunks']
            st.session_state.global_context = parsed_data['global_context']
            st.session_state.current_file = uploaded_file.name
            
            # 2. Generate Forensic Summary
            summ_data = st.session_state.agent.generate_summary(st.session_state.global_context)
            st.session_state.summary = summ_data.get('summary', 'Analysis failed.')

    # Metadata Dashboard
    st.success(f"Forensic Analysis Complete: Identified **{len(st.session_state.chunks)} functional chunks**.")
    
    # Render Documentation Dashboard
    st.divider()
    col_doc_left, col_doc_right = st.columns([1, 1])
    
    with col_doc_left:
        st.subheader("📑 Technical Executive Summary")
        st.markdown(f'<div class="report-container">{st.session_state.summary}</div>', unsafe_allow_html=True)
    
    with col_doc_right:
        st.subheader("🗃️ Global Context (State Variables)")
        with st.expander("View Data Structures", expanded=True):
            st.code(st.session_state.global_context, language='yaml')

    # --- STEP 2: CHAINED LOGIC SYNTHESIS ---
    st.divider()
    st.subheader(f"🚀 Phase 2: Unified Modernization ({target_stack})")
    
    if st.button("Start Chained Transformation", type="primary", use_container_width=True):
        ctx = get_script_run_ctx()
        
        status_slot = st.empty()
        prog_bar = st.progress(0)
        
        # Synthesis Slots
        col_code, col_test = st.columns(2)
        with col_code:
            st.markdown("### 🛠️ Modern Source Code")
            code_slot = st.empty()
        with col_test:
            st.markdown("### 🧪 Unit Test Suite")
            test_slot = st.empty()

        # Shared containers for results
        code_container = []
        
        def chained_worker():
            agent = st.session_state.agent
            g_ctx = st.session_state.global_context
            chunks = st.session_state.chunks
            lang_key = "java" if "Java" in target_stack else "python"
            
            try:
                # 1. Synthesize Class Skeleton
                with ui_lock: status_slot.info("Step 1/3: Synthesizing Class Structure & Member Variables...")
                skeleton = agent.generate_global_structure(g_ctx, target_stack)
                code_container.append(skeleton + "\n\n")
                with ui_lock: code_slot.code("".join(code_container), language=lang_key)

                # 2. Iterate Logic Chunks
                total = len(chunks)
                for i, chunk in enumerate(chunks):
                    with ui_lock:
                        status_slot.info(f"Step 2/3: Converting Chunk {i+1}/{total}: {chunk['name']}...")
                        prog_bar.progress((i + 1) / total)
                    
                    code_container.append(f"\n    // --- Logic Implementation: {chunk['name']} ---\n")
                    
                    # Stream logic tokens with UI Throttling to prevent freezing
                    token_counter = 0
                    for delta in agent.process_chunk_stream(chunk, g_ctx, target_stack):
                        code_container[-1] += delta
                        token_counter += 1
                        
                        # Only update UI every 15 tokens to keep websocket clear
                        if token_counter % 15 == 0:
                            with ui_lock:
                                code_slot.code("".join(code_container) + " ▌", language=lang_key)
                    
                    # Force a final UI update for the chunk
                    with ui_lock:
                        code_slot.code("".join(code_container), language=lang_key)

                # 3. Finalize Assembly
                if "Java" in target_stack or "C#" in target_stack:
                    code_container.append("\n}")
                
                final_code = "".join(code_container)
                st.session_state.final_code = final_code

                # 4. Generate Tests (Streaming)
                with ui_lock: status_slot.info("Step 3/3: Generating Comprehensive Unit Tests...")
                test_buffer = ""
                # We use the generic stream helper for tests
                for delta in agent.process_chunk_stream({"name": "UnitTests", "code": agent.get_test_prompt(final_code, target_stack)}, g_ctx, target_stack):
                    test_buffer += delta
                    with ui_lock:
                        test_slot.code(test_buffer + " ▌", language=lang_key)
                
                with ui_lock:
                    test_slot.code(test_buffer, language=lang_key)
                    status_slot.success("🎯 Modernization & Testing Complete!")
                
                st.session_state.final_tests = test_buffer

            except Exception as e:
                with ui_lock: st.error(f"Chain Error: {str(e)}")

        # Launch background thread
        t = threading.Thread(target=chained_worker)
        add_script_run_ctx(t, ctx)
        t.start()

# --- STEP 3: PERSISTENT DOWNLOADS ---
if "final_code" in st.session_state:
    st.divider()
    st.subheader("📥 Download Results")
    
    ext = "java" if "Java" in target_stack else "py" if "Python" in target_stack else "cs"
    
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    with dl_col1:
        st.download_button("📄 Download Forensic Spec (.md)", st.session_state.summary, file_name="forensic_spec.md")
    with dl_col2:
        st.download_button(f"💾 Download Source ({ext.upper()})", st.session_state.final_code, file_name=f"modernized.{ext}")
    with dl_col3:
        if "final_tests" in st.session_state:
            st.download_button(f"🧪 Download Tests ({ext.upper()})", st.session_state.final_tests, file_name=f"tests.{ext}")
