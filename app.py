"""
DENV Drug Combination Analysis GUI Application

A Streamlit-based GUI for anti-DENV drug combination efficacy and safety evaluation.
Full pipeline: Raw Data -> % Inhibition -> SynergyFinder Format -> Synergy Analysis -> Heatmap
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path

from calculate_inhibition import calculate_percent_inhibition
from synergyfinder_input import generate_synergyfinder_input
from synergy_analysis import calculate_synergy
from heatmap_generator import load_files, build_matrix, plot_and_save
from drug_combination_template import generate_from_excel

DATA_DIR = Path("/app/data")
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
SAMPLES_DIR = Path("/app/samples")

st.set_page_config(
    page_title="DENV Drug Combination Analysis",
    page_icon="🧬",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1f77b4; text-align: center;}
    .sub-header {font-size: 1.5rem; color: #2ca02c;}
    .step-complete {color: #28a745; font-weight: bold;}
    .step-pending {color: #6c757d;}
</style>
""", unsafe_allow_html=True)

if "pipeline_complete" not in st.session_state:
    st.session_state.pipeline_complete = False
if "output_files" not in st.session_state:
    st.session_state.output_files = {}


def save_uploaded_file(uploaded_file, dest_path):
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest_path


def main():
    st.markdown("<h1 class='main-header'>DENV Drug Combination Analysis</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Anti-DENV drug combination efficacy and safety evaluation</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    sidebar_status()
    
    tab1, tab2 = st.tabs(["🚀 Run Pipeline", "📁 Upload Existing Data"])
    
    with tab1:
        run_pipeline_tab()
    
    with tab2:
        upload_data_tab()


def sidebar_status():
    st.sidebar.markdown("## Pipeline Status")
    
    steps = [
        ("1️⃣ Template (Optional)", "template"),
        ("2️⃣ % Inhibition", "perc_inhibition"),
        ("3️⃣ SynergyFinder Format", "synergyfinder"),
        ("4️⃣ Synergy Scores", "synergy_scores"),
        ("5️⃣ Heatmap", "heatmap")
    ]
    
    for step_name, key in steps:
        if st.session_state.output_files.get(key):
            st.sidebar.markdown(f"✅ {step_name}")
        else:
            st.sidebar.markdown(f"⬜ {step_name}")
    
    st.sidebar.markdown("---")
    
    if st.session_state.pipeline_complete:
        st.sidebar.markdown("### Download Outputs")
        for name, path in st.session_state.output_files.items():
            if path and Path(path).exists():
                with open(path, "rb") as f:
                    filename = Path(path).name
                    st.sidebar.download_button(f"📥 {filename}", f, file_name=filename, key=f"sidebar_dl_{name}")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Start New Analysis", key="sidebar_reset_btn"):
        reset_pipeline()


def reset_pipeline():
    st.session_state.pipeline_complete = False
    st.session_state.output_files = {}
    st.rerun()


def run_pipeline_tab():
    st.markdown("## Run Full Analysis Pipeline")
    st.markdown("Upload your raw experimental data and click **Run Pipeline** to execute all steps automatically.")
    
    st.markdown("---")
    
    with st.expander("📋 Step 1: Generate Data Entry Template (Optional)", expanded=False):
        st.markdown("""
        **Generate an empty data entry template for your experiments.**
        
        1. Download the **GenExcel.xlsx template** below
        2. Fill in your drug names, concentrations, and experiment details  
        3. Upload the filled template to generate a data entry Excel file
        4. Fill the data entry file with your experimental results
        5. Save it as `RawInput.xlsx` and upload in Step 2
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Download Template:**")
            genexcel_path = SAMPLES_DIR / "GenExcel.xlsx"
            if genexcel_path.exists():
                with open(genexcel_path, "rb") as f:
                    st.download_button(
                        "📥 Download GenExcel.xlsx Template",
                        f,
                        file_name="GenExcel.xlsx",
                        key="download_genexcel_template",
                        help="Empty template for you to fill in"
                    )
        
        with col2:
            st.markdown("**Download Sample (with example data):**")
            sample_path = SAMPLES_DIR / "GenExcel_sample.xlsx"
            if sample_path.exists():
                with open(sample_path, "rb") as f:
                    st.download_button(
                        "📥 Download GenExcel_sample.xlsx",
                        f,
                        file_name="GenExcel_sample.xlsx",
                        key="download_genexcel_sample",
                        help="Sample file with example data"
                    )
        
        st.markdown("---")
        st.markdown("**Generate Data Entry Template:**")
        
        template_config = st.file_uploader(
            "Upload your filled GenExcel.xlsx",
            type=["xlsx"],
            key="template_config",
            help="Upload the GenExcel.xlsx file you filled with your drug info"
        )
        
        if template_config:
            if st.button("Generate Data Entry Template", key="gen_template_btn"):
                try:
                    temp_path = INPUT_DIR / "GenExcel_temp.xlsx"
                    save_uploaded_file(template_config, temp_path)
                    
                    output_path = OUTPUT_DIR / "drug_combination_results.xlsx"
                    generate_from_excel(str(temp_path), str(output_path))
                    
                    st.session_state.output_files["template"] = str(output_path)
                    st.success("✅ Data entry template generated!")
                    
                    with open(output_path, "rb") as f:
                        st.download_button(
                            "📥 Download drug_combination_results.xlsx",
                            f,
                            file_name="drug_combination_results.xlsx",
                            key="download_template_result",
                            help="Fill this file with your experimental data"
                        )
                    
                    st.info("💡 Fill the downloaded Excel file with your experimental data, then upload it as RawInput.xlsx in Step 2.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.markdown("### Step 2: Upload Raw Data")
    st.markdown("Upload your `RawInput.xlsx` file containing raw experimental data with replicates.")
    
    raw_input_file = st.file_uploader(
        "Upload RawInput.xlsx",
        type=["xlsx"],
        key="raw_input",
        help="Excel file with columns: Single drugs, Drugs, Rep1, Rep2, Rep3, ..."
    )
    
    col1, col2 = st.columns(2)
    drug_pairs_input = col1.text_input(
        "Drug Pairs (optional)",
        placeholder="e.g., DrugA:DrugB DrugA:DrugC",
        help="Leave empty for auto-detection",
        key="drug_pairs_pipeline"
    )
    heatmap_dpi = col2.slider("Heatmap DPI", min_value=100, max_value=600, value=300, key="dpi_pipeline")
    
    st.markdown("---")
    
    if raw_input_file:
        if st.button("🚀 Run Full Pipeline", type="primary", use_container_width=True, key="run_pipeline_btn"):
            run_full_pipeline(raw_input_file, drug_pairs_input, heatmap_dpi)
    else:
        st.info("👆 Please upload RawInput.xlsx to start the pipeline.")
    
    if st.session_state.pipeline_complete:
        display_results(key_prefix="pipeline_")


def run_full_pipeline(raw_input_file, drug_pairs_input, dpi):
    progress_bar = st.progress(0, text="Initializing...")
    status = st.empty()
    
    try:
        status.markdown("**Step 2: Calculating % Inhibition...**")
        progress_bar.progress(10, text="Step 2/5: Calculating % Inhibition...")
        
        input_path = INPUT_DIR / "RawInput.xlsx"
        save_uploaded_file(raw_input_file, input_path)
        
        perc_output = OUTPUT_DIR / "PercInhibition.xlsx"
        calculate_percent_inhibition(str(input_path), str(perc_output))
        st.session_state.output_files["perc_inhibition"] = str(perc_output)
        
        status.markdown("**Step 3: Converting to SynergyFinder format...**")
        progress_bar.progress(30, text="Step 3/5: Converting to SynergyFinder format...")
        
        syn_input = OUTPUT_DIR / "SynergyFinder_input.csv"
        drug_pairs = None
        if drug_pairs_input.strip():
            drug_pairs = [tuple(p.split(":")) for p in drug_pairs_input.strip().split()]
        
        generate_synergyfinder_input(str(perc_output), str(syn_input), drug_pairs)
        st.session_state.output_files["synergyfinder"] = str(syn_input)
        
        block_id_path = OUTPUT_DIR / "SynergyFinder_BlockID.csv"
        if block_id_path.exists():
            st.session_state.output_files["block_id"] = str(block_id_path)
        
        status.markdown("**Step 4: Calculating synergy scores...**")
        progress_bar.progress(50, text="Step 4/5: Calculating synergy scores...")
        
        syn_output = OUTPUT_DIR / "synergy_score_table.csv"
        calculate_synergy(str(syn_input), str(syn_output))
        st.session_state.output_files["synergy_scores"] = str(syn_output)
        
        summary_path = OUTPUT_DIR / "synergy_summary.csv"
        if summary_path.exists():
            st.session_state.output_files["synergy_summary"] = str(summary_path)
        
        status.markdown("**Step 5: Generating heatmap...**")
        progress_bar.progress(80, text="Step 5/5: Generating heatmap...")
        
        heatmap_path = OUTPUT_DIR / "heatmap.jpeg"
        
        if summary_path.exists() and block_id_path.exists():
            df_sum, df_block = load_files(str(summary_path), str(block_id_path))
            matrix = build_matrix(df_sum, df_block)
            plot_and_save(matrix, str(heatmap_path), dpi=dpi)
            st.session_state.output_files["heatmap"] = str(heatmap_path)
        
        progress_bar.progress(100, text="Complete!")
        st.session_state.pipeline_complete = True
        
        st.success("✅ Pipeline completed successfully!")
        st.rerun()
        
    except Exception as e:
        progress_bar.empty()
        status.empty()
        st.error(f"❌ Pipeline error: {str(e)}")
        st.exception(e)


def display_results(key_prefix=""):
    st.markdown("---")
    st.markdown("## 📊 Results")
    
    st.markdown("### Output Files")
    
    files_to_show = [
        ("Percent Inhibition", "perc_inhibition", "PercInhibition.xlsx"),
        ("SynergyFinder Input", "synergyfinder", "SynergyFinder_input.csv"),
        ("Block ID Summary", "block_id", "SynergyFinder_BlockID.csv"),
        ("Synergy Score Table", "synergy_scores", "synergy_score_table.csv"),
        ("Synergy Summary", "synergy_summary", "synergy_summary.csv"),
        ("Heatmap", "heatmap", "heatmap.jpeg"),
    ]
    
    cols = st.columns(3)
    for i, (display_name, key, filename) in enumerate(files_to_show):
        path = st.session_state.output_files.get(key)
        if path and Path(path).exists():
            with cols[i % 3]:
                st.markdown(f"**{display_name}**")
                with open(path, "rb") as f:
                    st.download_button(f"📥 {filename}", f, file_name=filename, key=f"{key_prefix}dl_results_{key}")
    
    heatmap_path = st.session_state.output_files.get("heatmap")
    if heatmap_path and Path(heatmap_path).exists():
        st.markdown("### 🗺️ Synergy Heatmap")
        st.image(str(heatmap_path), caption="Drug Synergy Heatmap", use_container_width=True)
    
    summary_path = st.session_state.output_files.get("synergy_summary")
    if summary_path and Path(summary_path).exists():
        st.markdown("### 📈 Synergy Summary")
        df = pd.read_csv(summary_path)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("""
        **Synergy Interpretation:**
        - **Score > 5**: Synergistic effect
        - **Score < -5**: Antagonistic effect  
        - **-5 to 5**: Additive effect
        """)


def upload_data_tab():
    st.markdown("<h2 class='sub-header'>Upload Existing Data</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    Use this tab if you have already processed some steps externally. Upload your intermediate files 
    and run the remaining pipeline steps.
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Input Files")
        raw_file = st.file_uploader("RawInput.xlsx", type=["xlsx"], key="upload_raw")
        perc_file = st.file_uploader("PercInhibition.xlsx", type=["xlsx"], key="upload_perc")
    
    with col2:
        st.markdown("### Intermediate Files")
        syn_file = st.file_uploader("SynergyFinder_input.csv", type=["csv"], key="upload_syn")
        block_file = st.file_uploader("SynergyFinder_BlockID.csv", type=["csv"], key="upload_block")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    drug_pairs_input = col1.text_input("Drug Pairs (optional)", placeholder="DrugA:DrugB", key="drug_pairs_upload")
    start_step = col2.selectbox("Start from step:", [
        "Step 2: Calculate % Inhibition",
        "Step 3: Convert to SynergyFinder", 
        "Step 4: Calculate Synergy",
        "Step 5: Generate Heatmap"
    ], key="start_step_select")
    
    heatmap_dpi = st.slider("Heatmap DPI", min_value=100, max_value=600, value=300, key="dpi_upload")
    
    if st.button("▶️ Run from Selected Step", type="primary", key="run_from_step_btn"):
        run_from_step(raw_file, perc_file, syn_file, block_file, drug_pairs_input, start_step, heatmap_dpi)
    
    if st.session_state.pipeline_complete:
        display_results(key_prefix="upload_")


def run_from_step(raw_file, perc_file, syn_file, block_file, drug_pairs_input, start_step, dpi):
    step_map = {
        "Step 2: Calculate % Inhibition": 2,
        "Step 3: Convert to SynergyFinder": 3,
        "Step 4: Calculate Synergy": 4,
        "Step 5: Generate Heatmap": 5
    }
    start_idx = step_map[start_step]
    
    progress_bar = st.progress(0, text="Initializing...")
    status = st.empty()
    
    try:
        drug_pairs = None
        if drug_pairs_input.strip():
            drug_pairs = [tuple(p.split(":")) for p in drug_pairs_input.strip().split()]
        
        if start_idx <= 2 and raw_file:
            status.markdown("**Step 2: Calculating % Inhibition...**")
            progress_bar.progress(10, text="Step 2/5: Calculating % Inhibition...")
            
            input_path = INPUT_DIR / "RawInput.xlsx"
            save_uploaded_file(raw_file, input_path)
            
            perc_output = OUTPUT_DIR / "PercInhibition.xlsx"
            calculate_percent_inhibition(str(input_path), str(perc_output))
            st.session_state.output_files["perc_inhibition"] = str(perc_output)
        
        if start_idx == 2 and not raw_file:
            st.error("Please upload RawInput.xlsx for Step 2")
            return
        
        if start_idx <= 3:
            status.markdown("**Step 3: Converting to SynergyFinder format...**")
            progress_bar.progress(30, text="Step 3/5: Converting format...")
            
            if start_idx == 3 and perc_file:
                perc_path = INPUT_DIR / "PercInhibition.xlsx"
                save_uploaded_file(perc_file, perc_path)
            else:
                perc_path = OUTPUT_DIR / "PercInhibition.xlsx"
            
            if perc_path.exists():
                syn_input = OUTPUT_DIR / "SynergyFinder_input.csv"
                generate_synergyfinder_input(str(perc_path), str(syn_input), drug_pairs)
                st.session_state.output_files["synergyfinder"] = str(syn_input)
                
                block_id_path = OUTPUT_DIR / "SynergyFinder_BlockID.csv"
                if block_id_path.exists():
                    st.session_state.output_files["block_id"] = str(block_id_path)
        
        if start_idx <= 4:
            status.markdown("**Step 4: Calculating synergy scores...**")
            progress_bar.progress(50, text="Step 4/5: Calculating synergy...")
            
            if start_idx == 4 and syn_file:
                syn_path = INPUT_DIR / "SynergyFinder_input.csv"
                save_uploaded_file(syn_file, syn_path)
            else:
                syn_path = OUTPUT_DIR / "SynergyFinder_input.csv"
            
            if syn_path.exists():
                syn_output = OUTPUT_DIR / "synergy_score_table.csv"
                calculate_synergy(str(syn_path), str(syn_output))
                st.session_state.output_files["synergy_scores"] = str(syn_output)
                
                summary_path = OUTPUT_DIR / "synergy_summary.csv"
                if summary_path.exists():
                    st.session_state.output_files["synergy_summary"] = str(summary_path)
        
        if start_idx <= 5:
            status.markdown("**Step 5: Generating heatmap...**")
            progress_bar.progress(80, text="Step 5/5: Generating heatmap...")
            
            if start_idx == 5 and block_file:
                block_path = INPUT_DIR / "SynergyFinder_BlockID.csv"
                save_uploaded_file(block_file, block_path)
            else:
                block_path = OUTPUT_DIR / "SynergyFinder_BlockID.csv"
            
            summary_path = OUTPUT_DIR / "synergy_summary.csv"
            heatmap_path = OUTPUT_DIR / "heatmap.jpeg"
            
            if summary_path.exists() and block_path.exists():
                df_sum, df_block = load_files(str(summary_path), str(block_path))
                matrix = build_matrix(df_sum, df_block)
                plot_and_save(matrix, str(heatmap_path), dpi=dpi)
                st.session_state.output_files["heatmap"] = str(heatmap_path)
        
        progress_bar.progress(100, text="Complete!")
        st.session_state.pipeline_complete = True
        st.success("✅ Pipeline completed successfully!")
        st.rerun()
        
    except Exception as e:
        progress_bar.empty()
        status.empty()
        st.error(f"❌ Pipeline error: {str(e)}")


if __name__ == "__main__":
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    main()
