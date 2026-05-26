"""
DENV Drug Combination Analysis GUI Application

A Streamlit-based GUI for anti-DENV drug combination efficacy and safety evaluation.
Full pipeline: Raw Data -> % Inhibition -> SynergyFinder Format -> Synergy Analysis -> Heatmap
"""

import streamlit as st
import pandas as pd
import os
import tempfile
from pathlib import Path

from calculate_inhibition import calculate_percent_inhibition
from synergyfinder_input import generate_synergyfinder_input
from synergy_analysis import calculate_synergy, process_single_block, create_response_matrix
from heatmap_generator import load_files, build_matrix, plot_and_save
from drug_combination_template import generate_from_excel

DATA_DIR = Path("/app/data")
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"

st.set_page_config(
    page_title="DENV Drug Combination Analysis",
    page_icon="🧬",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1f77b4; text-align: center;}
    .sub-header {font-size: 1.5rem; color: #2ca02c;}
    .step-box {background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0;}
</style>
""", unsafe_allow_html=True)

if "step" not in st.session_state:
    st.session_state.step = 0
if "files_created" not in st.session_state:
    st.session_state.files_created = {}


def save_uploaded_file(uploaded_file, dest_path):
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest_path


def main():
    st.markdown("<h1 class='main-header'>DENV Drug Combination Analysis</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Anti-DENV drug combination efficacy and safety evaluation</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.sidebar.markdown("## Pipeline Steps")
    steps = [
        "1️⃣ Generate Template",
        "2️⃣ Calculate % Inhibition",
        "3️⃣ Convert to SynergyFinder",
        "4️⃣ Calculate Synergy",
        "5️⃣ Generate Heatmap"
    ]
    for i, step in enumerate(steps):
        if i <= st.session_state.step:
            st.sidebar.success(step)
        else:
            st.sidebar.info(step)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Output Files")
    if st.session_state.files_created:
        for name, path in st.session_state.files_created.items():
            st.sidebar.markdown(f"✅ {name}")
    
    tab1, tab2 = st.tabs(["🚀 Run Pipeline", "📁 Upload Existing Data"])
    
    with tab1:
        run_pipeline_tab()
    
    with tab2:
        upload_data_tab()


def run_pipeline_tab():
    st.markdown("<h2 class='sub-header'>Run Full Analysis Pipeline</h2>", unsafe_allow_html=True)
    
    st.markdown("### Step 1: Generate Experiment Template (Optional)")
    with st.expander("📋 Template Generation", expanded=False):
        st.markdown("Upload a configuration Excel file to generate the experiment template.")
        
        template_config = st.file_uploader("Upload GenExcel.xlsx", type=["xlsx"], key="template_config")
        
        if template_config:
            col1, col2 = st.columns(2)
            drug_pairs_input = col1.text_input("Drug Pairs (optional)", placeholder="DrugA:DrugB DrugA:DrugC")
            template_output = col2.text_input("Output Filename", value="drug_combination_results.xlsx")
            
            if st.button("Generate Template", key="gen_template"):
                try:
                    temp_path = INPUT_DIR / "GenExcel_temp.xlsx"
                    save_uploaded_file(template_config, temp_path)
                    
                    output_path = OUTPUT_DIR / template_output
                    generate_from_excel(str(temp_path), str(output_path))
                    
                    st.session_state.files_created["Template"] = str(output_path)
                    st.success(f"✅ Template saved to: {output_path}")
                    
                    with open(output_path, "rb") as f:
                        st.download_button("Download Template", f, file_name=template_output)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.markdown("### Step 2: Calculate Percent Inhibition")
    with st.expander("📊 % Inhibition Calculation", expanded=True):
        st.markdown("Upload your raw experimental data (RawInput.xlsx) to calculate percent inhibition.")
        
        raw_input_file = st.file_uploader("Upload RawInput.xlsx", type=["xlsx"], key="raw_input")
        
        if raw_input_file:
            perc_output = st.text_input("Output Filename", value="PercInhibition.xlsx", key="perc_output")
            
            if st.button("Calculate % Inhibition", key="calc_perc"):
                try:
                    input_path = INPUT_DIR / "RawInput.xlsx"
                    save_uploaded_file(raw_input_file, input_path)
                    
                    output_path = OUTPUT_DIR / perc_output
                    calculate_percent_inhibition(str(input_path), str(output_path))
                    
                    st.session_state.files_created["% Inhibition"] = str(output_path)
                    st.session_state.step = max(st.session_state.step, 1)
                    st.success(f"✅ Percent inhibition saved to: {output_path}")
                    
                    with open(output_path, "rb") as f:
                        st.download_button("Download % Inhibition", f, file_name=perc_output)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.markdown("### Step 3: Convert to SynergyFinder Format")
    with st.expander("🔄 Format Conversion", expanded=False):
        st.markdown("Convert percent inhibition data to SynergyFinder Plus input format.")
        
        perc_file = st.file_uploader("Upload PercInhibition.xlsx", type=["xlsx"], key="perc_file")
        
        if perc_file:
            col1, col2 = st.columns(2)
            synergy_input_output = col1.text_input("Output CSV", value="SynergyFinder_input.csv")
            drug_pairs_synergy = col2.text_input("Drug Pairs (optional)", placeholder="DrugA:DrugB")
            
            if st.button("Convert to SynergyFinder", key="convert_synergy"):
                try:
                    input_path = INPUT_DIR / "PercInhibition_upload.xlsx"
                    save_uploaded_file(perc_file, input_path)
                    
                    output_path = OUTPUT_DIR / synergy_input_output
                    drug_pairs = None
                    if drug_pairs_synergy:
                        drug_pairs = [tuple(p.split(":")) for p in drug_pairs_synergy.split()]
                    
                    generate_synergyfinder_input(str(input_path), str(output_path), drug_pairs)
                    
                    st.session_state.files_created["SynergyFinder Input"] = str(output_path)
                    st.session_state.step = max(st.session_state.step, 2)
                    st.success(f"✅ SynergyFinder input saved to: {output_path}")
                    
                    with open(output_path, "rb") as f:
                        st.download_button("Download SynergyFinder Input", f, file_name=synergy_input_output)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.markdown("### Step 4: Calculate Synergy Scores")
    with st.expander("📈 Synergy Analysis", expanded=False):
        st.markdown("Calculate synergy scores using ZIP, Bliss, Loewe, and HSA models.")
        
        synergy_input = st.file_uploader("Upload SynergyFinder_input.csv", type=["csv"], key="synergy_input")
        
        if synergy_input:
            synergy_output = st.text_input("Output Filename", value="synergy_score_table.csv")
            
            if st.button("Calculate Synergy", key="calc_synergy"):
                try:
                    input_path = INPUT_DIR / "SynergyFinder_input.csv"
                    save_uploaded_file(synergy_input, input_path)
                    
                    output_path = OUTPUT_DIR / synergy_output
                    calculate_synergy(str(input_path), str(output_path))
                    
                    st.session_state.files_created["Synergy Scores"] = str(output_path)
                    st.session_state.step = max(st.session_state.step, 3)
                    st.success(f"✅ Synergy scores saved to: {output_path}")
                    
                    with open(output_path, "rb") as f:
                        st.download_button("Download Synergy Scores", f, file_name=synergy_output)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.markdown("### Step 5: Generate Heatmap")
    with st.expander("🗺️ Heatmap Generation", expanded=False):
        st.markdown("Generate publication-quality synergy heatmap.")
        
        col1, col2 = st.columns(2)
        summary_file = col1.file_uploader("Upload synergy_summary.csv", type=["csv"], key="summary_file")
        block_file = col2.file_uploader("Upload SynergyFinder_BlockID.csv", type=["csv"], key="block_file")
        
        if summary_file and block_file:
            heatmap_output = st.text_input("Output Image", value="heatmap.jpeg")
            dpi = st.slider("DPI", min_value=100, max_value=600, value=300)
            
            if st.button("Generate Heatmap", key="gen_heatmap"):
                try:
                    summary_path = INPUT_DIR / "synergy_summary.csv"
                    block_path = INPUT_DIR / "SynergyFinder_BlockID.csv"
                    save_uploaded_file(summary_file, summary_path)
                    save_uploaded_file(block_file, block_path)
                    
                    output_path = OUTPUT_DIR / heatmap_output
                    df_sum, df_block = load_files(str(summary_path), str(block_path))
                    matrix = build_matrix(df_sum, df_block)
                    plot_and_save(matrix, str(output_path), dpi=dpi)
                    
                    st.session_state.files_created["Heatmap"] = str(output_path)
                    st.session_state.step = max(st.session_state.step, 4)
                    st.success(f"✅ Heatmap saved to: {output_path}")
                    
                    st.image(str(output_path), caption="Synergy Heatmap", use_container_width=True)
                    
                    with open(output_path, "rb") as f:
                        st.download_button("Download Heatmap", f, file_name=heatmap_output)
                except Exception as e:
                    st.error(f"Error: {str(e)}")


def upload_data_tab():
    st.markdown("<h2 class='sub-header'>Quick Start with Existing Data</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    Upload your existing data files to skip steps in the pipeline:
    - **RawInput.xlsx**: Raw experimental data with replicates
    - **PercInhibition.xlsx**: Pre-calculated percent inhibition values
    - **SynergyFinder_input.csv**: Data already in SynergyFinder format
    """)
    
    uploaded_files = {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        raw_file = st.file_uploader("Raw Input Data", type=["xlsx"])
        if raw_file:
            uploaded_files["raw"] = raw_file
        
        perc_file = st.file_uploader("Percent Inhibition", type=["xlsx"])
        if perc_file:
            uploaded_files["perc"] = perc_file
    
    with col2:
        sync_input_file = st.file_uploader("SynergyFinder Input", type=["csv"])
        if sync_input_file:
            uploaded_files["synergy_input"] = sync_input_file
        
        sync_block_file = st.file_uploader("SynergyFinder BlockID", type=["csv"])
        if sync_block_file:
            uploaded_files["synergy_block"] = sync_block_file
    
    if uploaded_files:
        if st.button("Process Uploaded Files", key="process_uploads"):
            try:
                for key, file in uploaded_files.items():
                    if key == "raw":
                        path = INPUT_DIR / "RawInput.xlsx"
                        save_uploaded_file(file, path)
                        st.info(f"📁 Saved: {path}")
                    elif key == "perc":
                        path = INPUT_DIR / "PercInhibition.xlsx"
                        save_uploaded_file(file, path)
                        st.session_state.files_created["% Inhibition"] = str(path)
                    elif key == "synergy_input":
                        path = INPUT_DIR / "SynergyFinder_input.csv"
                        save_uploaded_file(file, path)
                        st.session_state.files_created["SynergyFinder Input"] = str(path)
                    elif key == "synergy_block":
                        path = INPUT_DIR / "SynergyFinder_BlockID.csv"
                        save_uploaded_file(file, path)
                
                st.success(f"✅ {len(uploaded_files)} files uploaded successfully!")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.markdown("### Run Full Pipeline from Uploaded Data")
    
    start_step = st.selectbox("Start from step:", [
        "Step 2: Calculate % Inhibition",
        "Step 3: Convert to SynergyFinder",
        "Step 4: Calculate Synergy",
        "Step 5: Generate Heatmap"
    ])
    
    if st.button("Run Pipeline", key="run_pipeline"):
        try:
            run_pipeline_from_step(start_step)
        except Exception as e:
            st.error(f"Error: {str(e)}")


def run_pipeline_from_step(start_step):
    """Run the pipeline starting from the specified step."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    step_to_idx = {
        "Step 2: Calculate % Inhibition": 1,
        "Step 3: Convert to SynergyFinder": 2,
        "Step 4: Calculate Synergy": 3,
        "Step 5: Generate Heatmap": 4
    }
    
    start_idx = step_to_idx[start_step]
    
    try:
        if start_idx <= 1:
            status_text.text("Calculating % Inhibition...")
            input_path = INPUT_DIR / "RawInput.xlsx"
            output_path = OUTPUT_DIR / "PercInhibition.xlsx"
            if input_path.exists():
                calculate_percent_inhibition(str(input_path), str(output_path))
                st.session_state.files_created["% Inhibition"] = str(output_path)
            progress_bar.progress(25)
        
        if start_idx <= 2:
            status_text.text("Converting to SynergyFinder format...")
            input_path = INPUT_DIR / "PercInhibition.xlsx"
            if not input_path.exists():
                input_path = INPUT_DIR / "RawInput.xlsx"
            output_path = OUTPUT_DIR / "SynergyFinder_input.csv"
            if input_path.exists():
                generate_synergyfinder_input(str(input_path), str(output_path))
                st.session_state.files_created["SynergyFinder Input"] = str(output_path)
            progress_bar.progress(50)
        
        if start_idx <= 3:
            status_text.text("Calculating synergy scores...")
            input_path = INPUT_DIR / "SynergyFinder_input.csv"
            output_path = OUTPUT_DIR / "synergy_score_table.csv"
            if input_path.exists():
                calculate_synergy(str(input_path), str(output_path))
                st.session_state.files_created["Synergy Scores"] = str(output_path)
            progress_bar.progress(75)
        
        if start_idx <= 4:
            status_text.text("Generating heatmap...")
            summary_path = OUTPUT_DIR / "synergy_summary.csv"
            block_path = INPUT_DIR / "SynergyFinder_BlockID.csv"
            if not block_path.exists():
                block_path = OUTPUT_DIR / "SynergyFinder_BlockID.csv"
            output_path = OUTPUT_DIR / "heatmap.jpeg"
            
            if summary_path.exists() and block_path.exists():
                df_sum, df_block = load_files(str(summary_path), str(block_path))
                matrix = build_matrix(df_sum, df_block)
                plot_and_save(matrix, str(output_path))
                st.session_state.files_created["Heatmap"] = str(output_path)
                
                st.image(str(output_path), caption="Synergy Heatmap", use_container_width=True)
            progress_bar.progress(100)
        
        status_text.text("Pipeline complete!")
        st.success("✅ Pipeline completed successfully!")
        
        st.markdown("### Output Files")
        for name, path in st.session_state.files_created.items():
            if Path(path).exists():
                st.markdown(f"- **{name}**: `{path}`")
                with open(path, "rb") as f:
                    st.download_button(f"Download {name}", f, file_name=Path(path).name, key=f"dl_{name}")
        
    except Exception as e:
        st.error(f"Pipeline error: {str(e)}")
        progress_bar.empty()


if __name__ == "__main__":
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    main()
