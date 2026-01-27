import streamlit as st
import os
import time
import threading
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import our refactored core modules
from core.ingestion import LegacyIngestor
from core.analyzer import StaticSemanticAnalyzer
from core.knowledge_base import RAGContextEngine
from core.agents import ValidationRefactoringAgent

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Legacy to Vanilla Java Modernizer",
    page_icon="☕",
    layout="wide"
)

# UI Lock to prevent browser websocket collisions during streaming
ui_lock = threading.Lock()

# Custom CSS for the Dashboard
st.markdown("""
    <style>
    .status-green { color: #28a745; font-weight: bold; font-size: 22px; }
    .status-amber { color: #ffc107; font-weight: bold; font-size: 22px; }
    .status-red { color: #dc3545; font-weight: bold; font-size: 22px; }
    .metric-card { background-color: #f9f9f9; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    </style>
    """, unsafe_allow_value=True)

# --- Initialize Engines in Session State ---
if "engines_initialized" not in st.session_state:
    st.session_state.ingestor = LegacyIngestor()
    st.session_state.analyzer = StaticSemanticAnalyzer()
    st.session_state.rag_engine = RAGContextEngine()
    st.session_state.agent = ValidationRefactoringAgent()
    st.session_state.engines_initialized = True

# --- Unified Processing Worker (Thread Safe) ---
def unified_transformation_worker(clean_code, context, code_slot, test_slot, result_collector):
    """
    Worker function executed in a dedicated thread.
    Streams the full Java code, then streams the full test class.
    """
    agent = st.session_state.agent
    
    try:
        # 1. STREAM VANILLA JAVA CODE
        full_java = ""
        synthesis_prompt = agent.get_unified_synthesis_prompt(context, clean_code)
        
        for delta in agent.stream_llm(synthesis_prompt):
            full_java += delta
            with ui_lock:
                code_slot.code(full_java + " ▌", language="java")
        
        with ui_lock:
            code_slot.code(full_java, language="java")
        
        # 2. STREAM JUNIT 5 TESTS (Using the generated Java code as context)
        full_tests = ""
        test_prompt = agent.get_unified_test_prompt(full_java)
        
        for delta in agent.stream_llm(test_prompt):
            full_tests += delta
            with ui_lock:
                test_slot.code(full_tests + " ▌", language="java")
        
        with ui_lock:
            test_slot.code(full_tests, language="java")
        
        # Save final results for the persistence/dashboard
        result_collector["java"] = full_java
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock:
            st.error(f"Transformation Error: {str(e)}")

# --- Main Interface ---
st.title("☕ Unified Legacy Transformation")
st.markdown("Modernizing code to **Vanilla Java 17+** and **JUnit 5** (Framework-free).")

col_inp, col_set = st.columns([3, 1])
with col_inp:
    code_input = st.text_area("Paste Legacy Source Code (VB, COBOL, Old Java):", height=250)
with col_set:
    source_lang = st.selectbox("Source Language", ["COBOL", "VB6", "Java (Legacy)"])
    st.info("Target Stack: **Vanilla Java (Standard Library)**")

if st.button("🚀 Start Unified Transformation", type="primary", use_container_width=True):
    if not code_input:
        st.error("Please provide legacy source code.")
    else:
        start_time = time.time()
        # Capture Streamlit Session Context
        ctx = get_script_run_ctx()

        with st.status("Phase 1 & 2: Analyzing Legacy Structure...", expanded=True) as status:
            # Step 1: Normalization
            clean_code = st.session_state.ingestor.normalize(code_input)
            
            # Step 2: Structural Graph Extraction
            graphs = st.session_state.analyzer.generate_graphs(clean_code, source_lang)
            
            # Step 3: Unified Knowledge Extraction
            st.write("Phase 3: Extracting unified business context...")
            context = st.session_state.rag_engine.get_unified_context(graphs, clean_code)
            
            st.write("Phase 4: Synthesizing Modern Java & JUnit Tests...")
            
            # Setup UI layout for code blocks
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.subheader("🛠️ Modern Vanilla Java")
                code_placeholder = st.empty()
            with res_col2:
                st.subheader("🧪 JUnit 5 Test Suite")
                test_placeholder = st.empty()

            # Result collector for storage
            result_collector = {"java": "", "tests": ""}

            # --- LAUNCH UNIFIED WORKER THREAD ---
            t = threading.Thread(
                target=unified_transformation_worker,
                args=(clean_code, context, code_placeholder, test_placeholder, result_collector)
            )
            add_script_run_ctx(t, ctx)
            t.start()
            
            # Wait for the transformation to complete
            t.join()

            duration = time.time() - start_time
            status.update(label=f"Transformation Complete in {duration:.1f}s", state="complete")
            
            # Save results to session state for Dashboard
            st.session_state.final_java = result_collector["java"]
            st.session_state.final_tests = result_collector["tests"]
            st.session_state.final_graphs = graphs
            st.session_state.final_conf = st.session_state.analyzer.calculate_confidence_score(graphs)
            st.session_state.final_duration = duration

# --- Evaluation Dashboard ---
if "final_java" in st.session_state:
    st.divider()
    st.subheader("📊 Final Evaluation Report")
    
    conf = st.session_state.final_conf
    
    # Heatmap Logic
    if conf >= 0.85:
        zone_cls, zone_txt = "status-green", "🟢 GREEN (Auto-Approve)"
    elif conf >= 0.60:
        zone_cls, zone_txt = "status-amber", "🟡 AMBER (Manual Review)"
    else:
        zone_cls, zone_txt = "status-red", "🔴 RED (High Risk)"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Confidence Score**\n<div class='{zone_cls}'>{conf*100:.0f}%</div>", unsafe_allow_value=True)
    with c2:
        st.markdown(f"**Dashboard Status**\n<div class='{zone_cls}'>{zone_txt}</div>", unsafe_allow_value=True)
    with c3:
        st.metric("Total Execution Time", f"{st.session_state.final_duration:.1f}s")

    with st.expander("🔍 View Extracted Structural Insights (AST/CFG/DFG)"):
        st.json(st.session_state.final_graphs)
        st.info("The structural graphs were used to ensure variable and control flow consistency in the modern Java output.")

    if conf < 0.85:
        st.warning("⚠️ **Manual Verification Required:** High complexity detected in legacy branches. Cross-check the transformed Java logic against the CFG paths in the Structural Insights tab.")
