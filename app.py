import streamlit as st
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Import our refactored core modules
from core.ingestion import LegacyIngestor
from core.analyzer import StaticSemanticAnalyzer
from core.knowledge_base import RAGContextEngine
from core.agents import ValidationRefactoringAgent

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Ultra-Fast Legacy Modernizer",
    page_icon="⚡",
    layout="wide"
)

# Custom CSS for the Dashboard Heatmap and Metrics
st.markdown("""
    <style>
    .status-green { color: #28a745; font-weight: bold; font-size: 20px; }
    .status-amber { color: #ffc107; font-weight: bold; font-size: 20px; }
    .status-red { color: #dc3545; font-weight: bold; font-size: 20px; }
    .metric-box { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; }
    </style>
    """, unsafe_allow_value=True)

# --- App Header ---
st.title("⚡ Ultra-Fast Parallel Modernization")
st.markdown("Automated Legacy-to-Modern Pipeline with **Parallel Streaming** & **Real-Time Analysis**.")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Migration Settings")
    source_lang = st.selectbox("Source Language", ["COBOL", "VB6", "Java (Old)"])
    target_tech = st.selectbox("Target Stack", ["Python (FastAPI)", "Java (Spring Boot)"])
    
    st.divider()
    st.info("Performance Mode: **Parallel Streaming** 🚀")
    if st.button("Reset Pipeline"):
        st.session_state.clear()
        st.rerun()

# --- Core Logic for Parallel Streaming ---
def stream_process_chunk(idx, chunk, target_tech, rag_engine, agent, container):
    """
    Function to be executed in a separate thread for each semantic chunk.
    Streams code and tests directly to specific UI containers.
    """
    # 1. Retrieve Context (Step 6)
    context = rag_engine.get_related_context(chunk)
    
    # 2. Modern Code Synthesis (Step 7 - Streaming)
    container.markdown(f"### 📦 Unit {idx+1}: {chunk.logic_type}")
    code_slot = container.empty()
    full_code = ""
    
    synthesis_prompt = agent.get_synthesis_prompt(context, chunk.description, target_tech)
    for delta in agent.stream_llm(synthesis_prompt):
        full_code += delta
        code_slot.code(full_code + " ▌", language="python" if "Python" in target_tech else "java")
    
    code_slot.code(full_code, language="python" if "Python" in target_tech else "java")
    
    # 3. Generate Unit Tests (Step 7 - Streaming)
    test_slot = container.empty()
    full_tests = ""
    test_prompt = agent.get_test_prompt(full_code, target_tech)
    
    for delta in agent.stream_llm(test_prompt):
        full_tests += delta
        test_slot.markdown(f"*Generating Tests...*\n```python\n{full_tests} ▌\n```")
    
    test_slot.markdown(f"**Unit Tests**\n```python\n{full_tests}\n```")
    
    return {"id": chunk.chunk_id, "code": full_code, "tests": full_tests}

# --- Main UI Logic ---
code_input = st.text_area("Paste Legacy Source Code:", height=250, placeholder="IDENTIFICATION DIVISION...")

if st.button("🚀 Execute Fast-Track Pipeline", type="primary", use_container_width=True):
    if not code_input:
        st.error("Input code is empty.")
    else:
        # Initialize Engines
        ingestor = LegacyIngestor()
        analyzer = StaticSemanticAnalyzer()
        rag_engine = RAGContextEngine()
        agent = ValidationRefactoringAgent()
        
        start_time = time.time()

        with st.status("Running Automated Pipeline...", expanded=True) as status:
            # Phase 1: Normalization (Fast)
            st.write("Phase 1: Normalizing code...")
            clean_code = ingestor.normalize(code_input)
            
            # Phase 2: Consolidated Analysis (One call instead of three)
            st.write("Phase 2: Consolidated Structural Analysis (AST/CFG/DFG)...")
            graphs = analyzer.generate_graphs(clean_code, source_lang)
            confidence = analyzer.calculate_confidence_score(graphs)
            
            # Phase 3: Semantic Chunking
            st.write("Phase 3: Logic Chunking...")
            chunks = rag_engine.create_semantic_chunks(graphs, clean_code)
            
            # Phase 4: Parallel Synthesis & Streaming (The Speed Booster)
            st.write(f"Phase 4: Parallel synthesis of {len(chunks)} logic units...")
            
            # Create placeholders for each chunk to stream into
            ui_placeholders = [st.container() for _ in range(len(chunks))]
            
            # Use ThreadPoolExecutor for concurrent LLM streaming
            with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
                futures = [
                    executor.submit(stream_process_chunk, i, chunks[i], target_tech, rag_engine, agent, ui_placeholders[i])
                    for i in range(len(chunks))
                ]
                final_results = [f.result() for f in futures]
            
            duration = time.time() - start_time
            status.update(label=f"Modernization Complete in {duration:.1f}s!", state="complete")

        # Save to session state for dashboard rendering
        st.session_state.processed = {
            "results": final_results,
            "graphs": graphs,
            "confidence": confidence,
            "duration": duration
        }

# --- Final Evaluation Dashboard ---
if "processed" in st.session_state:
    data = st.session_state.processed
    
    st.divider()
    st.subheader("📊 Evaluation Dashboard & Heatmap")
    
    # 1. Heatmap / Quality Gate
    col1, col2, col3, col4 = st.columns(4)
    conf = data['confidence']
    
    if conf >= 0.85:
        zone_cls, zone_txt = "status-green", "🟢 GREEN (Auto-Approve)"
    elif conf >= 0.60:
        zone_cls, zone_txt = "status-amber", "🟡 AMBER (Manual Review)"
    else:
        zone_cls, zone_txt = "status-red", "🔴 RED (Manual Cross-Check)"

    with col1:
        st.markdown(f"**Confidence Score**\n<div class='{zone_cls}'>{conf*100:.0f}%</div>", unsafe_allow_value=True)
    with col2:
        st.markdown(f"**Risk Zone**\n<div class='{zone_cls}'>{zone_txt}</div>", unsafe_allow_value=True)
    with col3:
        comp = data['graphs'].get('complexity_metrics', {}).get('cyclomatic_complexity', 'N/A')
        st.metric("Cyclomatic Complexity", comp)
    with col4:
        st.metric("Processing Time", f"{data['duration']:.1f}s")

    # 2. Structural Insights
    with st.expander("🔍 View Structural Dependency Graphs (AST/CFG/DFG)"):
        st.json(data['graphs'])
        st.caption("This analysis indicates the branches and data dependencies extracted from the legacy source.")

    # 3. Validation & Refinement Section
    if conf < 0.85:
        st.warning("⚠️ **Low Confidence Detected:** The legacy code contains high cyclomatic complexity. Manual verification of the control flow branches in the Structural Insights tab is recommended.")
    else:
        st.success("✅ **High Confidence:** All business rules were mapped successfully to the target architecture.")
