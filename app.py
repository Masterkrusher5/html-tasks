import streamlit as st
import os
from dotenv import load_dotenv

# Import our refactored core modules
from core.ingestion import LegacyIngestor
from core.analyzer import StaticSemanticAnalyzer
from core.knowledge_base import RAGContextEngine
from core.agents import ValidationRefactoringAgent

# Initialize configurations
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Legacy Modernization Suite",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS for the Dashboard Heatmap
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #007bff;
    }
    .status-green { color: #28a745; font-weight: bold; }
    .status-amber { color: #ffc107; font-weight: bold; }
    .status-red { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_value=True)

# --- App Header ---
st.title("🛡️ AI Legacy Code Modernizer")
st.markdown("""
    **Phase 1-4 Pipeline:** Knowledge Extraction ➡️ Static/Semantic Analysis ➡️ 
    Context-Aware Synthesis ➡️ Automated Validation & Testing.
""")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Pipeline Settings")
    source_lang = st.selectbox("Source Language", ["COBOL", "VB6", "Java (Legacy)"])
    target_tech = st.selectbox("Target Architecture", ["Python (FastAPI)", "Java (Spring Boot)", "Node.js (TypeScript)"])
    
    st.divider()
    st.info("Direct LLM Connection: ACTIVE ✅" if os.getenv("LLM_KEY") else "Direct LLM Connection: MISSING ❌")
    
    if st.button("Clear Cache"):
        st.session_state.clear()
        st.rerun()

# --- Main Interface ---
code_input = st.text_area("Paste Legacy Source Code:", height=300, placeholder="IDENTIFICATION DIVISION. PROGRAM-ID. PAYROLL...")

if st.button("🚀 Start Modernization Process", type="primary", use_container_width=True):
    if not code_input:
        st.error("Please provide legacy code to proceed.")
    else:
        # Initialize Core Engines
        ingestor = LegacyIngestor()
        analyzer = StaticSemanticAnalyzer()
        rag_engine = RAGContextEngine()
        agent = ValidationRefactoringAgent()

        with st.status("Modernizing Application...", expanded=True) as status:
            # Step 1: Ingestion & Normalization
            st.write("Step 1: Normalizing voluminous code...")
            clean_code = ingestor.normalize(code_input)
            
            # Step 2: Static + Semantic Analysis
            st.write("Step 2: Generating AST/CFG/DFG Graphs...")
            graphs = analyzer.generate_graphs(clean_code, source_lang)
            confidence = analyzer.calculate_confidence_score(graphs)
            
            # Step 3, 4, 6: Semantic Chunking & Retrieval
            st.write("Step 3-6: Indexing Knowledge Base & Context Retrieval...")
            chunks = rag_engine.create_semantic_chunks(graphs, clean_code)
            
            # Step 7: Synthesis & Testing
            st.write("Step 7: Synthesizing Modern Code & Unit Tests...")
            results = []
            for chunk in chunks:
                context = rag_engine.get_related_context(chunk)
                modern_code = agent.finalize_code(context, chunk.description, target_tech)
                unit_tests = agent.generate_tests(modern_code, target_tech)
                results.append({
                    "chunk": chunk,
                    "modern": modern_code,
                    "tests": unit_tests,
                    "context": context
                })

            status.update(label="Modernization Complete!", state="complete")

        # Store in session state for rendering
        st.session_state.modern_results = results
        st.session_state.graphs = graphs
        st.session_state.confidence = confidence
        st.session_state.clean_code = clean_code

# --- Dashboard & Evaluation Report ---
if "modern_results" in st.session_state:
    data = st.session_state.modern_results
    conf = st.session_state.confidence
    graphs = st.session_state.graphs

    # 1. EVALUATION DASHBOARD (The Quality Gate)
    st.divider()
    st.subheader("📊 Final Evaluation & Risk Dashboard")
    
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    # Heatmap Logic
    if conf >= 0.85:
        zone_color = "status-green"
        zone_text = "GREEN (Auto-Approved)"
    elif conf >= 0.60:
        zone_color = "status-amber"
        zone_text = "AMBER (Manual Review Needed)"
    else:
        zone_color = "status-red"
        zone_text = "RED (High Risk - Cross Check)"

    with m_col1:
        st.markdown(f"**Confidence Score**\n<h2 class='{zone_color}'>{conf*100:.0f}%</h2>", unsafe_allow_value=True)
    with m_col2:
        st.markdown(f"**Dashboard Status**\n<h3 class='{zone_color}'>{zone_text}</h3>", unsafe_allow_value=True)
    with m_col3:
        complexity = graphs.get('complexity_metrics', {}).get('cyclomatic_complexity', 'N/A')
        st.metric("Cyclomatic Complexity", complexity)
    with m_col4:
        st.metric("Logic Chunks", len(data))

    # 2. SOURCE VS MODERNIZED CODE
    st.divider()
    tab1, tab2, tab3 = st.tabs(["💻 Modernized Source", "🏗️ Structural Analysis", "🧪 Automated Unit Tests"])

    with tab1:
        for item in data:
            st.info(f"**Logical Unit:** {item['chunk'].logic_type} - {item['chunk'].chunk_id}")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Legacy Logic Intent")
                st.write(item['chunk'].description)
            with c2:
                st.caption(f"Modernized {target_tech} Implementation")
                st.code(item['modern'], language="python" if "Python" in target_tech else "java")

    with tab2:
        st.subheader("Syntactic & Semantic Dependency Mapping")
        st.json(graphs)
        st.caption("The graph above identifies variable lifecycles (DFG) and branch paths (CFG).")

    with tab3:
        for item in data:
            st.subheader(f"Tests for {item['chunk'].chunk_id}")
            st.code(item['tests'], language="python" if "Python" in target_tech else "java")

    # 3. MANUAL CROSS-CHECK HIGHLIGHTS
    if conf < 0.85:
        st.warning("⚠️ **Manual Attention Required:** Logic complexity in this module is high. Review the Control Flow Graph (CFG) in Tab 2 to ensure all legacy branches are mapped to the new architecture.")
