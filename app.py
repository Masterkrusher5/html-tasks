import streamlit as st
import threading
import time
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

load_dotenv()
st.set_page_config(page_title="Chained Modernizer", layout="wide")

if "agent" not in st.session_state:
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.ingestor = FileIngestor()

ui_lock = threading.Lock()
st.title("🛡️ Chain-of-Thought Legacy Modernizer")

with st.sidebar:
    target_stack = st.selectbox("Target Stack", ["Java (Vanilla)", "Python", "C#"])

uploaded_file = st.file_uploader("Upload Large Legacy File", type=['cbl', 'vb', 'java', 'txt'])

if uploaded_file:
    raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
    norm_code = st.session_state.ingestor.normalize(raw_content)
    
    if "chunks" not in st.session_state:
        with st.spinner("Parsing Logic Tree & Dependency Graph..."):
            parsed_data = st.session_state.ingestor.chunk_code(norm_code, uploaded_file.name)
            st.session_state.parsed_data = parsed_data
            st.session_state.chunks = parsed_data['chunks']
            st.session_state.global_context = parsed_data['global_context']
            
            doc = st.session_state.agent.generate_summary(st.session_state.global_context)
            st.session_state.summary = doc['summary']

    st.success(f"Successfully parsed **{len(st.session_state.chunks)} functional chunks**.")
    
    with st.expander("View Global Context (Data Structures)"):
        st.code(st.session_state.global_context, language='yaml')
    
    st.subheader("System Summary")
    st.info(st.session_state.summary)

    if st.button("🚀 Start Chained Transformation"):
        ctx = get_script_run_ctx()
        
        st.divider()
        st.subheader("Live Synthesis Stream")
        
        status_slot = st.empty()
        prog_bar = st.progress(0)
        code_slot = st.empty()
        
        full_code_buffer = ""

        def chain_worker():
            agent = st.session_state.agent
            global_ctx = st.session_state.global_context
            chunks = st.session_state.chunks
            
            nonlocal full_code_buffer
            
            with ui_lock: status_slot.text("Generating Class Structure & State...")
            skeleton = agent.generate_global_structure(global_ctx, target_stack)
            full_code_buffer += skeleton + "\n\n"
            with ui_lock: code_slot.code(full_code_buffer, language='java')

            total = len(chunks)
            for i, chunk in enumerate(chunks):
                with ui_lock: 
                    status_slot.text(f"Processing Chunk {i+1}/{total}: {chunk['name']}...")
                    prog_bar.progress((i + 1) / total)
                
                chunk_code = f"\n    // --- Converted {chunk['name']} ---\n"
                for delta in agent.process_chunk_stream(chunk, global_ctx, target_stack):
                    chunk_code += delta
                
                full_code_buffer += chunk_code + "\n"
                with ui_lock: code_slot.code(full_code_buffer + " ▌", language='java')

            full_code_buffer += "\n}"
            with ui_lock: 
                code_slot.code(full_code_buffer, language='java')
                status_slot.success("Transformation Complete!")
                st.session_state.final_code = full_code_buffer

        t = threading.Thread(target=chain_worker)
        add_script_run_ctx(t, ctx)
        t.start()

if "final_code" in st.session_state:
    st.download_button("Download Complete File", st.session_state.final_code, "modernized.java")
