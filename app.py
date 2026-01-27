import streamlit as st
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# --- CRITICAL IMPORTS FOR THREADING ---
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import our refactored core modules
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

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    source_lang = st.selectbox("Source", ["COBOL", "VB6", "Java (Old)"])
    target_tech = st.selectbox("Target", ["Python (FastAPI)", "Java (Spring Boot)"])
    if st.button("Reset"):
        st.session_state.clear()
        st.rerun()

# --- Parallel Worker Function ---
def stream_process_chunk(idx, chunk, target_tech, rag_engine, agent, container):
    """
    Background worker that handles LLM streaming.
    The 'container' is a Streamlit placeholder (st.empty).
    """
    try:
        # 1. Context Retrieval
        context = rag_engine.get_related_context(chunk)
        
        container.markdown(f"### 📦 Unit {idx+1}: {chunk.logic_type}")
        code_slot = container.empty()
        
        # 2. Modern Code Synthesis (Streaming)
        full_code = ""
        synthesis_prompt = agent.get_synthesis_prompt(context, chunk.description, target_tech)
        
        for delta in agent.stream_llm(synthesis_prompt):
            full_code += delta
            # This line works now because we added the ScriptRunCtx
            code_slot.code(full_code + " ▌", language="python" if "Python" in target_tech else "java")
        
        code_slot.code(full_code, language="python" if "Python" in target_tech else "java")
        
        # 3. Unit Tests (Streaming)
        test_slot = container.empty()
        full_tests = ""
        test_prompt = agent.get_test_prompt(full_code, target_tech)
        
        for delta in agent.stream_llm(test_prompt):
            full_tests += delta
            test_slot.markdown(f"*Generating Tests...*\n```python\n{full_tests} ▌\n```")
        
        test_slot.markdown(f"**Unit Tests**\n```python\n{full_tests}\n```")
        
        return {"id": chunk.chunk_id, "code": full_code, "tests": full_tests}
    except Exception as e:
        container.error(f"Error in Unit {idx+1}: {str(e)}")
        return None

# --- Main Logic ---
code_input = st.text_area("Paste Legacy Source Code:", height=250)

if st.button("🚀 Start Fast-Track Pipeline", type="primary"):
    if not code_input:
        st.error("Please provide input code.")
    else:
        # Initialize Engines
        ingestor = LegacyIngestor()
        analyzer = StaticSemanticAnalyzer()
        rag_engine = RAGContextEngine()
        agent = ValidationRefactoringAgent()
        
        start_time = time.time()

        with st.status("Analyzing & Chunking...", expanded=True) as status:
            clean_code = ingestor.normalize(code_input)
            graphs = analyzer.generate_graphs(clean_code, source_lang)
            chunks = rag_engine.create_semantic_chunks(graphs, clean_code)
            
            st.write(f"Executing {len(chunks)} threads in parallel...")
            
            # --- THE FIX: GET THE CURRENT SESSION CONTEXT ---
            ctx = get_script_run_ctx()
            
            ui_placeholders = [st.container() for _ in range(len(chunks))]
            final_results = []
            
            with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
                futures = []
                for i in range(len(chunks)):
                    # Submit the task
                    f = executor.submit(
                        stream_process_chunk, 
                        i, chunks[i], target_tech, rag_engine, agent, ui_placeholders[i]
                    )
                    # --- THE FIX: ATTACH CONTEXT TO THE THREAD ---
                    add_script_run_ctx(f, ctx)
                    futures.append(f)
                
                final_results = [f.result() for f in futures]
            
            duration = time.time() - start_time
            status.update(label=f"Done in {duration:.1f}s!", state="complete")

        st.session_state.processed = {
            "results": final_results,
            "graphs": graphs,
            "confidence": analyzer.calculate_confidence_score(graphs),
            "duration": duration
        }

# --- Dashboard Display ---
if "processed" in st.session_state:
    data = st.session_state.processed
    st.divider()
    st.subheader("📊 Evaluation Dashboard")
    
    col1, col2, col3 = st.columns(3)
    conf = data['confidence']
    
    with col1:
        color = "status-green" if conf > 0.8 else "status-red"
        st.markdown(f"**Confidence**\n<div class='{color}'>{conf*100:.0f}%</div>", unsafe_allow_value=True)
    with col2:
        st.metric("Units Processed", len(data['results']))
    with col3:
        st.metric("Execution Time", f"{data['duration']:.1f}s")
    
    with st.expander("🔍 View Structural Analysis (JSON)"):
        st.json(data['graphs'])
