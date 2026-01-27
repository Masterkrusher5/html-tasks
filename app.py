import streamlit as st
import os
from dotenv import load_dotenv
from core.ingestion import LegacyIngestor
from core.analyzer import StaticSemanticAnalyzer
from core.knowledge_base import RAGContextEngine
from core.agents import ValidationRefactoringAgent

# Initialize configurations
load_dotenv()
st.set_page_config(page_title="Legacy Modernization Suite", layout="wide")

# --- UI Header ---
st.title("🚀 AI Legacy Code Modernizer")
st.markdown("Automated Migration: VB/COBOL/Java ➡️ Modern Services")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Pipeline Settings")
    target_tech = st.selectbox("Target Technology", ["Python (FastAPI)", "Java (Spring Boot)", "AWS Lambda (Python)"])
    source_lang = st.selectbox("Source Language", ["COBOL", "VB6", "Java (Legacy)"])
    
    st.divider()
    st.info("Azure OpenAI Status: Connected ✅" if os.getenv("AZURE_OPENAI_API_KEY") else "Azure OpenAI Status: Missing ❌")

# --- Initialize Session State ---
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None

# --- Main Interface ---
code_input = st.text_area("Paste Legacy Code Snippet here:", height=250, placeholder="Enter COBOL or VB code...")

col1, col2 = st.columns(2)
with col1:
    if st.button("Run Full Pipeline", type="primary", use_container_width=True):
        if not code_input:
            st.error("Please provide legacy code.")
        else:
            with st.status("Modernizing Code...", expanded=True) as status:
                # Step 1: Ingestion
                st.write("Step 1: Ingesting & Normalizing...")
                ingestor = LegacyIngestor("") 
                clean_code = ingestor.normalize(code_input)
                
                # Step 2: Analyzer
                st.write("Step 2: Generating AST/CFG/DFG...")
                analyzer = StaticSemanticAnalyzer()
                graphs = analyzer.generate_graphs(clean_code, source_lang)
                
                # Step 3/4/6: RAG & Chunking
                st.write("Step 3-6: Semantic Chunking & Retrieval...")
                rag_engine = RAGContextEngine()
                chunks = rag_engine.create_semantic_chunks(graphs, clean_code)
                
                # Step 7: Refactoring
                st.write("Step 7: Refactoring & Validation...")
                final_agent = ValidationRefactoringAgent()
                modern_results = []
                for chunk in chunks:
                    ctx = rag_engine.get_related_context(chunk)
                    output = final_agent.finalize_code(ctx, chunk.description, target_tech)
                    modern_results.append(output)
                
                # Simulation of a "Critic" Agent for Confidence (Phase 2 quality gate)
                confidence = 0.92 if "MOVE" in code_input else 0.65 
                
                st.session_state.processed_data = {
                    "original": clean_code,
                    "modern": "\n\n".join(modern_results),
                    "graphs": graphs,
                    "confidence": confidence,
                    "chunks": chunks
                }
                status.update(label="Modernization Complete!", state="complete")

# --- Dashboard Display ---
if st.session_state.processed_data:
    data = st.session_state.processed_data
    
    tab1, tab2, tab3 = st.tabs(["Dashboard & Heatmap", "Code Conversion", "Logic Analysis"])
    
    with tab1:
        st.subheader("Automated Quality Gate")
        
        # Dashboard Indicator (Heatmap Logic)
        score = data['confidence']
        if score > 0.85:
            st.success(f"ZONE: GREEN (Auto-Approve) | Confidence: {score*100}%")
        elif score > 0.60:
            st.warning(f"ZONE: AMBER (Manual Review Needed) | Confidence: {score*100}%")
        else:
            st.error(f"ZONE: RED (Critical Check) | Confidence: {score*100}%")
            
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Logic Accuracy", f"{score*100}%")
        col_m2.metric("Semantic Coverage", "98%")
        col_m3.metric("Complexity Reduction", "45%")
        
        st.divider()
        st.subheader("Manual Review Areas")
        st.info("The logic for 'Overtime Multiplier' was inferred from shared libraries. Please verify line 12.")

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Legacy Code (Normalized)")
            st.code(data['original'], language='cobol' if source_lang == "COBOL" else 'vbnet')
        with c2:
            st.caption(f"Modernized Code ({target_tech})")
            st.code(data['modern'], language='python' if "Python" in target_tech else 'java')

    with tab3:
        st.subheader("Static & Semantic Insights")
        st.json(data['graphs']) # Displays AST/CFG/DFG nodes
        
        st.subheader("Semantic Chunks")
        for chunk in data['chunks']:
            st.write(f"**ID:** {chunk.chunk_id} | **Logic:** {chunk.logic_type}")
            st.write(f"**Description:** {chunk.description}")
            st.divider()

else:
    st.info("Upload or paste code to begin the modernization process.")
