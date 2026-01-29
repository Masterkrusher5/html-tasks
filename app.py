import streamlit as st
import os
import threading
import re
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from core.ingestion import FileIngestor
from core.analyzer import UnifiedOpenAIAgent

load_dotenv()

# 1. Page Configuration
st.set_page_config(
    page_title="Forensic Modernizer Pro",
    page_icon="🛡️",
    layout="wide"
)

ui_lock = threading.Lock()

# 2. Engines Initialization
if "agent" not in st.session_state:
    st.session_state.agent = UnifiedOpenAIAgent()
    st.session_state.ingestor = FileIngestor()

# --- CUSTOM CSS FOR PROFESSIONAL UI ---
st.markdown("""
    <style>
    /* Main Report Container */
    .report-container {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* Header Styling */
    .report-header {
        color: #1565C0; /* Professional Blue */
        font-family: 'Segoe UI', sans-serif;
        font-weight: 600;
        font-size: 1.4rem;
        margin-bottom: 15px;
        border-bottom: 2px solid #f0f2f6;
        padding-bottom: 8px;
    }

    /* Summary Box Highlight */
    .summary-box {
        background-color: #f8f9fa;
        border-left: 5px solid #2ecc71;
        padding: 15px;
        border-radius: 5px;
        font-size: 16px;
        line-height: 1.6;
        color: #2c3e50;
    }

    /* Logic Flow Styling */
    .logic-box {
        font-family: 'Courier New', monospace;
        background-color: #fafafa;
        padding: 15px;
        border: 1px solid #eee;
        border-radius: 5px;
        font-size: 14px;
        color: #333;
    }
    
    /* Metrics Tags */
    .metric-tag {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.9rem;
        margin-right: 10px;
    }
    .tag-green { background-color: #d4edda; color: #155724; }
    .tag-red { background-color: #f8d7da; color: #721c24; }
    </style>
""", unsafe_allow_html=True)

# --- HELPER: PARSE MARKDOWN SECTIONS ---
def parse_markdown_report(text):
    """
    Splits the LLM's markdown output into structured sections for UI display.
    """
    sections = {
        "summary": "Processing...",
        "flow": "Processing...",
        "data": "Processing..."
    }
    
    try:
        # Split by Level 3 Headers (### Number.)
        parts = re.split(r'### \d+\.', text)
        
        if len(parts) > 1: sections["summary"] = parts[1].strip()
        if len(parts) > 2: sections["flow"] = parts[2].strip()
        if len(parts) > 3: sections["data"] = parts[3].strip()
        
        # Fallback if headers are missing
        if len(parts) < 2: sections["summary"] = text
            
    except Exception:
        sections["summary"] = text
        
    return sections

# --- WORKER ---
def synthesis_worker(clean_code, target_lang, code_slot, test_slot, result_collector):
    agent = st.session_state.agent
    lang_key = "java" if "Java" in target_lang else "python"
    
    try:
        # CODE STREAM
        full_code = ""
        synth_prompt = agent.get_synthesis_prompt(clean_code, target_lang)
        for delta in agent.stream_llm(synth_prompt, max_tokens=4000):
            full_code += delta
            with ui_lock:
                code_slot.code(full_code + " ▌", language=lang_key)
        with ui_lock:
            code_slot.code(full_code, language=lang_key)
        
        # TEST STREAM
        full_tests = ""
        test_prompt = agent.get_test_prompt(full_code, target_lang)
        for delta in agent.stream_llm(test_prompt, max_tokens=2000):
            full_tests += delta
            with ui_lock:
                test_slot.code(full_tests + " ▌", language=lang_key)
        with ui_lock:
            test_slot.code(full_tests, language=lang_key)
            
        result_collector["code"] = full_code
        result_collector["tests"] = full_tests

    except Exception as e:
        with ui_lock: st.error(f"Error: {str(e)}")

# --- UI HEADER ---
st.title("🛡️ Forensic Legacy Modernizer Pro")
st.caption("Enterprise-Grade Logic Extraction & Unified Synthesis Engine")

with st.sidebar:
    st.header("⚙️ Configuration")
    target_stack = st.selectbox("Target Architecture", ["Java (Vanilla 17+)", "Python (Standard)", "C# (.NET Core)"])
    st.divider()
    if st.button("🔄 Reset Pipeline"):
        st.session_state.clear()
        st.rerun()

# --- STEP 1: INGESTION ---
uploaded_file = st.file_uploader("Upload Source File", type=['cbl', 'cob', 'vb', 'java', 'txt'])

if uploaded_file:
    # Logic to prevent re-reading file on every interaction
    if "clean_code" not in st.session_state or st.session_state.get("current_file") != uploaded_file.name:
        raw_content = st.session_state.ingestor.read_uploaded_file(uploaded_file)
        st.session_state.clean_code = st.session_state.ingestor.normalize(raw_content)
        st.session_state.meta = st.session_state.ingestor.extract_metadata(uploaded_file, st.session_state.clean_code)
        st.session_state.current_file = uploaded_file.name
        if "doc_text" in st.session_state: del st.session_state.doc_text
        if "final_results" in st.session_state: del st.session_state.final_results

    meta = st.session_state.meta
    
    # File Metadata Card
    with st.container():
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**📄 File:** `{meta['file_name']}`")
        c2.markdown(f"**🏷️ Role:** `{meta['role']}`")
        c3.markdown(f"**📦 Size:** `{meta['size_kb']} KB`")

    st.divider()

    # --- PHASE 1: DOCUMENTATION ---
    col_btn, col_status = st.columns([1, 4])
    with col_btn:
        start_analysis = st.button("📝 Start Forensic Analysis", type="primary")
    
    if start_analysis:
        doc_placeholder = st.empty()
        full_doc = ""
        prompt = st.session_state.agent.get_documentation_prompt(st.session_state.clean_code)
        
        # Stream raw markdown first
        with st.spinner("Forensic Analysis in progress..."):
            for delta in st.session_state.agent.stream_llm(prompt, max_tokens=1500):
                full_doc += delta
                doc_placeholder.markdown(full_doc + " ▌")
        
        # Save to state
        st.session_state.doc_text = full_doc
        st.rerun() # Rerun to render the "Fancy" view

    # --- PHASE 2: FANCY DOCUMENTATION DISPLAY ---
    if "doc_text" in st.session_state:
        # Parse the raw markdown into sections
        sections = parse_markdown_report(st.session_state.doc_text)
        metrics = st.session_state.agent.calculate_dashboard_metrics(st.session_state.doc_text)
        
        # 1. Metrics Header
        st.subheader("📊 Phase 1: Technical Specification")
        m1, m2 = st.columns([1, 3])
        with m1:
            st.metric("AI Confidence", metrics['confidence_pct'])
        with m2:
            st.markdown("##### Risk Assessment")
            # Custom HTML Badge for Zone
            badge_class = "tag-green" if "GREEN" in metrics['zone'] else "tag-red"
            st.markdown(f"""
            <span class="metric-tag {badge_class}">{metrics['zone']}</span>
            <span class="metric-tag">Complexity: {metrics['complexity']}/10</span>
            """, unsafe_allow_html=True)

        # 2. Structured Report Container
        st.markdown('<div class="report-container">', unsafe_allow_html=True)
        
        st.markdown('<div class="report-header">1. Executive Technical Summary</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-box">{sections["summary"]}</div>', unsafe_allow_html=True)
        
        st.write("") # Spacer
        
        # Tabs for details
        tab_flow, tab_data, tab_raw = st.tabs(["⚡ Execution Flow", "🗃️ Data Dictionary", "📝 Raw View"])
        
        with tab_flow:
            st.markdown('<div class="report-header">2. Logical Execution Path</div>', unsafe_allow_html=True)
            st.markdown(sections["flow"])
            
        with tab_data:
            st.markdown('<div class="report-header">3. Variable & State Mapping</div>', unsafe_allow_html=True)
            st.markdown(sections["data"])
            
        with tab_raw:
            st.text_area("Raw Analysis Output", st.session_state.doc_text, height=300)

        st.markdown('</div>', unsafe_allow_html=True) # End report-container

        # --- PHASE 3: SYNTHESIS ---
        st.divider()
        st.subheader(f"🚀 Phase 2: Unified Modernization ({target_stack})")
        
        if st.button("Generate Full-File Code & Tests", type="primary", use_container_width=True):
            ctx = get_script_run_ctx()
            col_code, col_test = st.columns(2)
            with col_code:
                st.markdown("### 🛠️ Modern Source")
                code_placeholder = st.empty()
            with col_test:
                st.markdown("### 🧪 Unit Test Suite")
                test_placeholder = st.empty()

            result_collector = {"code": "", "tests": ""}
            
            t = threading.Thread(
                target=synthesis_worker,
                args=(st.session_state.clean_code, target_stack, code_placeholder, test_placeholder, result_collector)
            )
            add_script_run_ctx(t, ctx)
            t.start()
            
            with st.spinner("Synthesizing High-Density Logic..."):
                t.join()
            
            st.success("Modernization Complete.")
            st.session_state.final_results = result_collector

# --- DOWNLOADS SECTION (Docs + Code + Tests) ---
if "doc_text" in st.session_state or "final_results" in st.session_state:
    st.divider()
    st.subheader("📥 Export Artifacts")
    
    # We use 3 columns to include the Documentation Download
    d1, d2, d3 = st.columns(3)
    
    # 1. Download Documentation (Available immediately after Phase 1)
    if "doc_text" in st.session_state:
        with d1:
            st.download_button(
                label="📄 Download Forensic Spec",
                data=st.session_state.doc_text,
                file_name="forensic_analysis.md",
                mime="text/markdown",
                use_container_width=True
            )

    # 2. Download Code & Tests (Available after Phase 2)
    if "final_results" in st.session_state:
        ext = "java" if "Java" in target_stack else "py"
        with d2:
            st.download_button(
                label=f"💾 Download Source ({ext})",
                data=st.session_state.final_results["code"],
                file_name=f"modernized.{ext}",
                use_container_width=True
            )
        with d3:
            st.download_button(
                label=f"🧪 Download Tests ({ext})",
                data=st.session_state.final_results["tests"],
                file_name=f"tests.{ext}",
                use_container_width=True
            )
