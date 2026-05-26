# DENV Drug Combination Analysis - GUI Application

Anti-DENV drug combination efficacy and safety evaluation with a user-friendly web interface.

## Overview

This application provides a complete pipeline for evaluating drug combinations against Dengue virus (DENV). It calculates percent inhibition from raw experimental data, converts to SynergyFinder format, performs drug synergy analysis using multiple mathematical models, and generates publication-quality heatmaps.

## Features

- **Web-based GUI**: Easy-to-use Streamlit interface
- **Full Pipeline Integration**: All steps in one application
- **Docker Containerized**: Portable and reproducible deployment
- **Volume Persistence**: All intermediate and final outputs saved to mounted volumes

## Pipeline Steps

1. **Generate Template** (Optional): Create experiment templates from configuration
2. **Calculate % Inhibition**: Convert raw data to percent inhibition values
3. **Convert to SynergyFinder Format**: Format data for synergy analysis
4. **Calculate Synergy Scores**: Analyze using ZIP, Bliss, Loewe, and HSA models
5. **Generate Heatmap**: Create publication-quality visualization

## Quick Start with Docker

### Option 1: Docker Compose (Recommended)

```bash
# Build and run
docker-compose up -d

# Access the application
open http://localhost:8501
```

### Option 2: Docker directly

```bash
# Build the image
docker build -t jukjik_v1_app2:latest .

# Run the container
docker run -d \
  -p 8501:8501 \
  -v $(pwd)/data/input:/app/data/input \
  -v $(pwd)/data/output:/app/data/output \
  --name jukjik_denv_analysis \
  jukjik_v1_app2:latest

# Access the application
open http://localhost:8501
```

## Volume Mounts

All data is persisted through mounted volumes:

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./data/input` | `/app/data/input` | Input files (uploaded or placed here) |
| `./data/output` | `/app/data/output` | All intermediate and final outputs |

### Output Files

- `PercInhibition.xlsx` - Percent inhibition calculated from raw data
- `SynergyFinder_input.csv` - Data formatted for synergy analysis
- `SynergyFinder_BlockID.csv` - Block summary for drug pairs
- `synergy_score_table.csv` - Detailed synergy scores per concentration
- `synergy_summary.csv` - Summary statistics for each model
- `heatmap.jpeg` - Publication-quality synergy heatmap

## Usage

1. Open the application at `http://localhost:8501`
2. Navigate through the tabs:
   - **Run Pipeline**: Step-by-step analysis with file uploads
   - **Upload Existing Data**: Quick start with pre-processed data
3. Upload your data files at each step
4. Download results or access them directly from the mounted volumes

## Synergy Interpretation

| Score Range | Effect |
|-------------|--------|
| > 5 | Synergistic |
| < -5 | Antagonistic |
| -5 to 5 | Additive |

## Input Formats

### RawInput.xlsx

| Single drugs | Drugs | Rep1 | Rep2 | Rep3 |
|--------------|-------|------|------|------|
| Control | 0 | 100 | 105 | 98 |
| DrugA | 0.78 | 85 | 82 | 88 |
| ... | ... | ... | ... | ... |

### SynergyFinder Input CSV

| block_id | drug1 | drug2 | conc1 | conc2 | response | conc_unit |
|----------|-------|-------|-------|-------|----------|-----------|
| 1 | DrugA | DrugB | 0 | 0 | 0 | uM |
| 1 | DrugA | DrugB | 1.56 | 0 | 12.5 | uM |
| ... | ... | ... | ... | ... | ... | ... |

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py
```

## License

MIT License

## References

- Yadav B, et al. (2015) Searching for Drug Synergy in Complex Dose-Response Landscape Using an Interaction Potency Model. Computational and Structural Biotechnology Journal.
- Ritz C, et al. (2015) Dose-Response Analysis Using R. PLoS ONE.
