import streamlit as st
import os
import time
import threading
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import core modules
from core.ingestion import LegacyIngestor
from core.analyzer import StaticSemanticAnalyzer
from core.knowledge_base import RAGContextEngine
from core.agents import ValidationRefactoringAgent

load_dotenv()

# --- Page Config ---
st.set_page_config(page_title="Ultra-Fast Modernizer", page_icon="⚡", layout="wide")

# UI Lock to prevent threads from colliding when writing to the browser
ui_lock = threading.Lock()

# --- Initialize Engines in Session State ---
if "engines_initialized" not in st.session_state:
    st.session_state.ingestor = LegacyIngestor()
    st.session_state.analyzer = StaticSemanticAnalyzer()
    st.session_state.rag_engine = RAGContextEngine()
    st.session_state.agent = ValidationRefactoringAgent()
    st.session_state.engines_initialized = True

# --- Parallel Worker Function (Thread Safe) ---
def stream_process_chunk(idx, chunk, target_tech, container, shared_results):
    """
    Worker function with UI Locking to prevent blank units.
    """
    rag = st.session_state.rag_engine
    agent = st.session_state.agent
    
    try:
        # 1. Retrieve Context
        context = rag.get_related_context(chunk)
        
        # Initialize UI slots inside the container
        with ui_lock:
            container.markdown(f"### 📦 Unit {idx+1}: {chunk.logic_type}")
            code_slot = container.empty()
            test_slot = container.empty()

        # 2. Modern Code Synthesis (Streaming)
        full_code = ""
        prompt = agent.get_synthesis_prompt(context, chunk.description, target_tech)
        
        for delta in agent.stream_llm(prompt):
            full_code += delta
            # Use Lock to safely update UI
            with ui_lock:
                code_slot.code(full_code + " ▌", language="python" if "Python" in target_tech else "java")
        
        with ui_lock:
            code_slot.code(full_code, language="python" if "Python" in target_tech else "java")
        
        # 3. Unit Tests (Streaming)
        full_tests = ""
        test_prompt = agent.get_test_prompt(full_code, target_tech)
        
        for delta in agent.stream_llm(test_prompt):
            full_tests += delta
            with ui_lock:
                test_slot.markdown(f"*Generating Tests...*\n```python\n{full_tests} ▌\n```")
        
        with ui_lock:
            test_slot.markdown(f"**Unit Tests**\n```python\n{full_tests}\n```")
        
        # Save results to shared dictionary for the final dashboard
        shared_results[idx] = {"code": full_code, "tests": full_tests, "type": chunk.logic_type}

    except Exception as e:
        with ui_lock:
            container.error(f"Error in Unit {idx+1}: {str(e)}")

# --- Main Interface ---
st.title("⚡ Parallel Modernization Engine")
code_input = st.text_area("Paste Legacy Source Code:", height=250)

with st.sidebar:
    st.header("Settings")
    target_tech = st.selectbox("Target Stack", ["Python (FastAPI)", "Java (Spring Boot)"])
    source_lang = st.selectbox("Source Lang", ["COBOL", "VB6", "Java"])

if st.button("🚀 Start Fast-Track Pipeline", type="primary"):
    if not code_input:
        st.error("Input code is empty.")
    else:
        start_time = time.time()
        ctx = get_script_run_ctx()

        with st.status("Analyzing & Processing...", expanded=True) as status:
            # Step 1 & 2: Structural Analysis
            clean_code = st.session_state.ingestor.normalize(code_input)
            graphs = st.session_state.analyzer.generate_graphs(clean_code, source_lang)
            chunks = st.session_state.rag_engine.create_semantic_chunks(graphs, clean_code)
            
            st.write(f"Processing {len(chunks)} units in parallel threads...")
            
            threads = []
            shared_results = {} # Thread-safe collection of final results
            
            for i, chunk in enumerate(chunks):
                placeholder = st.container() # Create a dedicated container
                
                t = threading.Thread(
                    target=stream_process_chunk, 
                    args=(i, chunk, target_tech, placeholder, shared_results)
                )
                
                add_script_run_ctx(t, ctx) 
                threads.append(t)
                t.start()

            # Wait for all threads to finish COMPLETELY
            for t in threads:
                t.join()
            
            duration = time.time() - start_time
            status.update(label=f"Completed in {duration:.1f}s!", state="complete")
            
            # Persist data to session state AFTER threads are done to ensure UI stability
            st.session_state.final_results = shared_results
            st.session_state.final_conf = st.session_state.analyzer.calculate_confidence_score(graphs)
            st.session_state.final_graphs = graphs
            st.session_state.final_duration = duration

# --- Dashboard Display (Renders from persisted State) ---
if "final_results" in st.session_state:
    st.divider()
    st.subheader("📊 Evaluation Dashboard")
    
    # Render final Confidence Metric
    conf = st.session_state.final_conf
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Confidence Score", f"{conf*100:.0f}%")
    with c2:
        st.metric("Total Time", f"{st.session_state.final_duration:.1f}s")
    with c3:
        st.metric("Status", "SUCCESS")

    with st.expander("🔍 View Final Structural Insights"):
        st.json(st.session_state.final_graphs)
