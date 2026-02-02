import streamlit as st
import threading
import time
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import core modules
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

# Load environment variables
load_dotenv()

# 1. Configuration
st.set_page_config(
    page_title="Chained Modernizer Pro",
    page_icon="🛡️",
    layout="wide"
)

# UI Lock for thread-safe streaming
ui_lock = threading.Lock()

# 2. Initialize Engines
if "agent" not in st.session_state:
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.ingestor = FileIngestor()

# --- MAIN UI ---
st.title("🛡️ Chain-of-Thought Legacy Modernizer")
st.markdown("Global Context Extraction ➡️ Chunk-Based Synthesis ➡️ Unified Assembly")

# Sidebar
with st.sidebar:
    st.header("Pipeline Settings")
    target_stack = st.selectbox("Target Architecture", ["Java (Vanilla 17+)", "Python (Standard)", "C# (.NET Core)"])
    st.divider()
    st.info("ℹ️ **Chunking Mode:**\nLarge files are split into logical units (Paragraphs/Methods) to bypass token limits while preserving global state.")
    if st.button("Reset Application"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: INGESTION & CHUNKING ---
uploaded_file = st.file_uploader("Upload Large Legacy File", type=['cbl', 'cob', 'vb', 'java', 'txt'])

if uploaded_file:
    # 1. Read & Normalize
    if "chunks" not in st.session_state or st.session_state.get("current_file") != uploaded_file.name:
        raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
        norm_code = st.session_state.ingestor.normalize(raw_content)
        
        with st.spinner("Parsing Logic Tree & Building Dependency Graph..."):
            # Intelligent Chunking
            parsed_data = st.session_state.ingestor.chunk_code(norm_code, uploaded_file.name)
            
            # Save to session
            st.session_state.chunks = parsed_data['chunks']
            st.session_state.global_context = parsed_data['global_context']
            st.session_state.current_file = uploaded_file.name
            
            # Generate Context Summary
            summary_data = st.session_state.agent.generate_summary(st.session_state.global_context)
            st.session_state.summary = summary_data.get('summary', 'Analysis failed')

    # 2. Display Ingestion Dashboard
    st.success(f"Successfully parsed **{len(st.session_state.chunks)} functional chunks** from {uploaded_file.name}.")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Global Context (State)")
        with st.expander("View Data Division / Global Variables", expanded=True):
            st.code(st.session_state.global_context, language='yaml')
    
    with col2:
        st.subheader("System Summary")
        st.info(st.session_state.summary)

    # --- STEP 2: CHAINED SYNTHESIS ---
    st.divider()
    
    if st.button("🚀 Start Chained Transformation", type="primary"):
        ctx = get_script_run_ctx()
        
        st.subheader(f"Live Synthesis Stream ({target_stack})")
        
        # UI Slots
        status_slot = st.empty()
        prog_bar = st.progress(0)
        code_slot = st.empty()
        
        # Mutable container to hold the full code across the thread
        # We use a list because lists are mutable and accessible in nested scopes
        code_container = []

        def chain_worker():
            agent = st.session_state.agent
            global_ctx = st.session_state.global_context
            chunks = st.session_state.chunks
            
            # Detect language for syntax highlighting
            lang_key = "java" if "Java" in target_stack else "python" if "Python" in target_stack else "csharp"
            
            try:
                # A. Generate Class Skeleton (Headers/Variables)
                with ui_lock: status_slot.text("Phase 1: Synthesizing Class Structure & State...")
                skeleton = agent.generate_global_structure(global_ctx, target_stack)
                
                code_container.append(skeleton + "\n\n")
                with ui_lock: code_slot.code("".join(code_container), language=lang_key)

                # B. Iterate Logic Chunks
                total = len(chunks)
                for i, chunk in enumerate(chunks):
                    with ui_lock: 
                        status_slot.text(f"Phase 2: Converting Chunk {i+1}/{total}: {chunk['name']}...")
                        prog_bar.progress((i + 1) / total)
                    
                    chunk_buffer = f"\n    // --- Converted Logic: {chunk['name']} ---\n"
                    
                    # Stream specific chunk logic
                    for delta in agent.process_chunk_stream(chunk, global_ctx, target_stack):
                        chunk_buffer += delta
                    
                    # Append completed chunk to main buffer
                    code_container.append(chunk_buffer + "\n")
                    
                    # Update UI with the growing file
                    with ui_lock: code_slot.code("".join(code_container) + " ▌", language=lang_key)

                # C. Finalize File
                closing_brace = "\n}" if ("Java" in target_stack or "C#" in target_stack) else ""
                code_container.append(closing_brace)
                final_source = "".join(code_container)
                
                with ui_lock: 
                    code_slot.code(final_source, language=lang_key)
                    status_slot.success("Transformation Complete! All chunks assembled.")
                    prog_bar.progress(100)
                    st.session_state.final_code = final_source

            except Exception as e:
                with ui_lock: st.error(f"Chain Error: {str(e)}")

        # Launch Thread
        t = threading.Thread(target=chain_worker)
        add_script_run_ctx(t, ctx)
        t.start()

# --- STEP 3: DOWNLOAD ---
if "final_code" in st.session_state:
    st.divider()
    ext = "java" if "Java" in target_stack else "py" if "Python" in target_stack else "cs"
    st.download_button(
        label="💾 Download Complete File", 
        data=st.session_state.final_code, 
        file_name=f"modernized_full.{ext}",
        mime="text/plain"
    )
