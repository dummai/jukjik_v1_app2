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
                    st.sidebar.download_button(f"📥 {filename}", f, file_name=filename)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Start New Analysis"):
        reset_pipeline()


def reset_pipeline():
    st.session_state.pipeline_complete = False
    st.session_state.output_files = {}
    st.rerun()


def run_pipeline_tab():
    st.markdown("## Run Full Analysis Pipeline")
    st.markdown("Upload your raw experimental data and click **Run Pipeline** to execute all steps automatically.")
    
    st.markdown("---")
    
    with st.expander("📋 Step 1: Generate Experiment Template (Optional)", expanded=False):
        st.markdown("Generate a template file for data entry. This step is optional.")
        
        template_config = st.file_uploader("Upload GenExcel.xlsx", type=["xlsx"], key="template_config")
        
        if template_config:
            if st.button("Generate Template", key="gen_template"):
                try:
                    temp_path = INPUT_DIR / "GenExcel_temp.xlsx"
                    save_uploaded_file(template_config, temp_path)
                    
                    output_path = OUTPUT_DIR / "drug_combination_results.xlsx"
                    generate_from_excel(str(temp_path), str(output_path))
                    
                    st.session_state.output_files["template"] = str(output_path)
                    st.success(f"✅ Template saved!")
                    
                    with open(output_path, "rb") as f:
                        st.download_button("Download Template", f, file_name="drug_combination_results.xlsx")
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
        help="Leave empty for auto-detection"
    )
    heatmap_dpi = col2.slider("Heatmap DPI", min_value=100, max_value=600, value=300)
    
    st.markdown("---")
    
    if raw_input_file:
        if st.button("🚀 Run Full Pipeline", type="primary", use_container_width=True):
            run_full_pipeline(raw_input_file, drug_pairs_input, heatmap_dpi)
    else:
        st.info("👆 Please upload RawInput.xlsx to start the pipeline.")
    
    if st.session_state.pipeline_complete:
        display_results()


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


def display_results():
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
                    st.download_button(f"📥 {filename}", f, file_name=filename, key=f"dl_{key}")
    
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
    drug_pairs_input = col1.text_input("Drug Pairs (optional)", placeholder="DrugA:DrugB")
    start_step = col2.selectbox("Start from step:", [
        "Step 2: Calculate % Inhibition",
        "Step 3: Convert to SynergyFinder", 
        "Step 4: Calculate Synergy",
        "Step 5: Generate Heatmap"
    ])
    
    heatmap_dpi = st.slider("Heatmap DPI", min_value=100, max_value=600, value=300)
    
    if st.button("▶️ Run from Selected Step", type="primary"):
        run_from_step(raw_file, perc_file, syn_file, block_file, drug_pairs_input, start_step, heatmap_dpi)
    
    if st.session_state.pipeline_complete:
        display_results()


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
