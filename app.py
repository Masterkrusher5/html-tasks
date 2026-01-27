import streamlit as st
import os
import time
import threading
from dotenv import load_dotenv

# --- THREADING CONTEXT IMPORTS ---
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# Import core engine modules
from core.ingestion import LegacyIngestor
from core.analyzer import StaticSemanticAnalyzer
from core.knowledge_base import RAGContextEngine
from core.agents import ValidationRefactoringAgent

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Multi-Lang Legacy Modernizer",
    page_icon="🚀",
    layout="wide"
)

# UI Lock to prevent browser websocket collisions during streaming
ui_lock = threading.Lock()

# Custom CSS for the Evaluation Dashboard
st.markdown("""
    <style>
    .status-green { color: #28a745; font-weight: bold; font-size: 22px; }
    .status-amber { color: #ffc107; font-weight: bold; font-size: 22px; }
    .status-red { color: #dc3545; font-weight: bold; font-size: 22px; }
    .metric-card { background-color: #f9f9f9; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    pre { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_value=True)

# --- Initialize Engines in Session State ---
if "engines_initialized" not in st.session_state:
    st.session_state.ingestor = LegacyIngestor()
    st.session_state.analyzer = StaticSemanticAnalyzer()
    st.session_state.rag_engine = RAGContextEngine()
    st.session_state.agent = ValidationRefactoringAgent()
    st.session_state.engines_initialized = True

# --- Unified Multi-Lang Worker (Thread Safe) ---
def unified_transformation_worker(clean_code, context, target_lang, code_slot, test_slot, result_collector):
    """
    Worker function executed in a dedicated thread.
    1. Streams the full modern code file.
    2. Streams the full unit test file once code is available.
    """
    agent = st.session_state.agent
    lang_key = target_lang.lower().split()[0] # e.g., 'java' or 'python'
    
    try:
        # 1. PHASE 3: UNIFIED CODE SYNTHESIS
        full_code = ""
        synthesis_prompt = agent.get_unified_synthesis_prompt(context, clean_code, target_lang)
        
        for delta in agent.stream_llm(synthesis_prompt, target_lang):
            full_code += delta
            with ui_lock:
                code_slot.code(full_code + " ▌", language=lang_key)
        
        with ui_lock:
            code_slot.code(full_code, language=lang_key)
        
        # 2. PHASE 4: UNIFIED UNIT TEST GENERATION
        full_tests = ""
        test_prompt = agent.get_unified_test_prompt(full_code, target_lang)
        
        for delta in agent.stream_llm(test_prompt, target_lang):
            full_tests += delta
            with ui_lock:
                test_slot.code(full_tests + " ▌", language=lang_key)
        
        with ui_lock:
            test_slot.code(full_tests, language=lang_key)
        
        # Save results for session persistence
        result_collector["code"] = full_code
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock:
            st.error(f"Transformation Error: {str(e)}")

# --- Main Interface ---
st.title("🚀 Unified Multi-Language Modernizer")
st.markdown("Automated transformation of legacy code into cohesive, modern architectures.")

# --- Sidebar: Language Selection ---
with st.sidebar:
    st.header("Transformation Target")
    target_lang = st.selectbox("Select Target Language", [
        "Java (Vanilla)", 
        "Python (Clean)", 
        "Python (FastAPI)", 
        "C# (.NET Core)", 
        "TypeScript (Node.js)"
    ])
    source_lang = st.selectbox("Source Language", ["COBOL", "VB6", "Java (Legacy)"])
    
    st.divider()
    st.markdown("**Architecture Standards:**")
    st.write(f"- Single Unified File")
    st.write(f"- Idiomatic {target_lang}")
    if "Java" in target_lang:
        st.write("- Framework-free (Vanilla)")
    
    if st.button("Reset Application"):
        st.session_state.clear()
        st.rerun()

# --- Input Section ---
code_input = st.text_area("Paste Legacy Source Code:", height=300, placeholder="Input COBOL, VB, or Old Java code here...")

if st.button("🚀 Execute Modernization Pipeline", type="primary", use_container_width=True):
    if not code_input:
        st.error("Please provide source code.")
    else:
        start_time = time.time()
        # Capture Streamlit Session Context for the background thread
        ctx = get_script_run_ctx()

        with st.status("Initializing Pipeline...", expanded=True) as status:
            # Step 1: Normalization (Local)
            st.write("Step 1: Normalizing code & stripping noise...")
            clean_code = st.session_state.ingestor.normalize(code_input)
            
            # Step 2: Structural Analysis (LLM)
            st.write("Step 2: Extracting structural graphs (AST/CFG/DFG)...")
            graphs = st.session_state.analyzer.generate_graphs(clean_code, source_lang)
            
            # Step 3: Unified Context (LLM)
            st.write("Step 3: Generating unified business logic specification...")
            context = st.session_state.rag_engine.get_unified_context(graphs, clean_code)
            
            st.write(f"Step 4: Synthesizing {target_lang} & Tests...")
            
            # Setup UI layout for streaming code blocks
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.subheader(f"🛠️ Modern {target_lang}")
                code_placeholder = st.empty()
            with res_col2:
                st.subheader("🧪 Unit Test Suite")
                test_placeholder = st.empty()

            # Result collector for storage
            result_collector = {"code": "", "tests": ""}

            # --- LAUNCH UNIFIED WORKER THREAD ---
            t = threading.Thread(
                target=unified_transformation_worker,
                args=(clean_code, context, target_lang, code_placeholder, test_placeholder, result_collector)
            )
            add_script_run_ctx(t, ctx)
            t.start()
            
            # Thread Join ensures the status spinner waits for the LLM to finish streaming
            t.join()

            duration = time.time() - start_time
            status.update(label=f"Modernization Complete in {duration:.1f}s", state="complete")
            
            # Persist results to session state for the Dashboard
            st.session_state.final_code = result_collector["code"]
            st.session_state.final_tests = result_collector["tests"]
            st.session_state.final_graphs = graphs
            st.session_state.final_conf = st.session_state.analyzer.calculate_confidence_score(graphs)
            st.session_state.final_duration = duration
            st.session_state.target_used = target_lang

# --- Evaluation Dashboard & Heatmap ---
if "final_code" in st.session_state:
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
        st.caption("These graphs identify variable lifecycles and control flow paths used to validate the transformation.")

    if conf < 0.85:
        st.warning(f"⚠️ **Manual Review Priority:** High complexity detected. Ensure the modern {st.session_state.target_used} code addresses all conditional branches shown in the CFG.")
