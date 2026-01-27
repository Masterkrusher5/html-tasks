import streamlit as st
import os
import time
import threading
from dotenv import load_dotenv

# --- THE CRITICAL FIX IMPORTS ---
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import our core modules
from core.ingestion import LegacyIngestor
from core.analyzer import StaticSemanticAnalyzer
from core.knowledge_base import RAGContextEngine
from core.agents import ValidationRefactoringAgent

load_dotenv()

# --- Page Configuration ---
st.set_page_config(page_title="Ultra-Fast Modernizer", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .status-green { color: #28a745; font-weight: bold; font-size: 20px; }
    .status-amber { color: #ffc107; font-weight: bold; font-size: 20px; }
    .status-red { color: #dc3545; font-weight: bold; font-size: 20px; }
    </style>
    """, unsafe_allow_value=True)

st.title("⚡ Parallel Modernization Engine")

# --- Initialize Engines ---
if "engines_initialized" not in st.session_state:
    st.session_state.ingestor = LegacyIngestor()
    st.session_state.analyzer = StaticSemanticAnalyzer()
    st.session_state.rag_engine = RAGContextEngine()
    st.session_state.agent = ValidationRefactoringAgent()
    st.session_state.engines_initialized = True

# --- Parallel Worker Function ---
def stream_process_chunk(idx, chunk, target_tech, container):
    """
    Worker function executed in a dedicated thread.
    """
    # Note: We access engines from session_state inside the thread
    rag = st.session_state.rag_engine
    agent = st.session_state.agent
    
    try:
        # Step 6: Context Retrieval
        context = rag.get_related_context(chunk)
        
        container.markdown(f"### 📦 Unit {idx+1}: {chunk.logic_type}")
        code_slot = container.empty()
        
        # Step 7: Modern Code Synthesis (Streaming)
        full_code = ""
        prompt = agent.get_synthesis_prompt(context, chunk.description, target_tech)
        
        for delta in agent.stream_llm(prompt):
            full_code += delta
            # The Context allows this line to update the UI browser session
            code_slot.code(full_code + " ▌", language="python" if "Python" in target_tech else "java")
        
        code_slot.code(full_code, language="python" if "Python" in target_tech else "java")
        
        # Step 7: Unit Tests (Streaming)
        test_slot = container.empty()
        full_tests = ""
        test_prompt = agent.get_test_prompt(full_code, target_tech)
        
        for delta in agent.stream_llm(test_prompt):
            full_tests += delta
            test_slot.markdown(f"*Generating Tests...*\n```python\n{full_tests} ▌\n```")
        
        test_slot.markdown(f"**Unit Tests**\n```python\n{full_tests}\n```")
        
    except Exception as e:
        container.error(f"Error in Unit {idx+1}: {str(e)}")

# --- Main Logic ---
code_input = st.text_area("Paste Legacy Source Code:", height=250)
target_tech = st.sidebar.selectbox("Target Stack", ["Python (FastAPI)", "Java (Spring Boot)"])
source_lang = st.sidebar.selectbox("Source Lang", ["COBOL", "VB6", "Java"])

if st.button("🚀 Start Fast-Track Pipeline", type="primary"):
    if not code_input:
        st.error("Please provide input code.")
    else:
        start_time = time.time()
        
        # Capture the context of the current browser session
        ctx = get_script_run_ctx()

        with st.status("Analyzing & Chunking...", expanded=True) as status:
            # Phase 1 & 2 (Sequential)
            clean_code = st.session_state.ingestor.normalize(code_input)
            graphs = st.session_state.analyzer.generate_graphs(clean_code, source_lang)
            chunks = st.session_state.rag_engine.create_semantic_chunks(graphs, clean_code)
            
            st.write(f"Launching {len(chunks)} parallel threads...")
            
            # --- THE THREADING FIX BLOCK ---
            threads = []
            for i, chunk in enumerate(chunks):
                # Create a specific container for this thread
                placeholder = st.container()
                
                # Define the thread
                t = threading.Thread(
                    target=stream_process_chunk, 
                    args=(i, chunk, target_tech, placeholder)
                )
                
                # IMPORTANT: Attach the session context to the thread
                add_script_run_ctx(t, ctx) 
                
                threads.append(t)
                t.start()

            # Wait for all threads to finish
            for t in threads:
                t.join()
            
            duration = time.time() - start_time
            status.update(label=f"Done in {duration:.1f}s!", state="complete")
            
            # Save metrics to session state
            st.session_state.final_conf = st.session_state.analyzer.calculate_confidence_score(graphs)
            st.session_state.final_graphs = graphs
            st.session_state.final_duration = duration

# --- Dashboard Display ---
if "final_conf" in st.session_state:
    st.divider()
    st.subheader("📊 Evaluation Dashboard")
    c1, c2, c3 = st.columns(3)
    conf = st.session_state.final_conf
    
    with c1:
        color = "status-green" if conf > 0.8 else "status-red"
        st.markdown(f"**Confidence**\n<div class='{color}'>{conf*100:.0f}%</div>", unsafe_allow_value=True)
    with c2:
        st.metric("Processing Time", f"{st.session_state.final_duration:.1f}s")
    with c3:
        st.metric("Risk Zone", "LOW" if conf > 0.8 else "HIGH")
    
    with st.expander("🔍 Structural Analysis"):
        st.json(st.session_state.final_graphs)
