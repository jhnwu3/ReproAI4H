# Bridging the Reproducibility Divide: Open Source Software's Role in Standardizing Healthcare AI4H

## Overview
This repository contains the reproducibility study conducted for our submitted publication "Bridging the Reproducibility Divide: Open Source Software's Role in Standardizing Healthcare AI4H". We provide a step-by-step guide for those who wish to reproduce our data collection and analysis procedures.

## Data
The complete dataset used in our analysis can be found in:
- `data/processed_final.csv`

## Analysis and Visualization
Our figures and numerical analyses are implemented in the following Jupyter notebooks:

1. `plot_general.ipynb`
   - Contains all code for generating Figure 1

2. `plot_code.ipynb`
   - Contains all code for generating Figure 2

3. `plot_data.ipynb`
   - Contains all code for generating Figure 3

## Requirements

### Dependencies
While it is suggested to create a new environment for this project, please follow these steps to set up the environment and install the prerequisite packages:

1. Create a new conda environment named "reproAI4H":
```bash
conda create -n reproAI4H python=3.10
```

2. Activate the environment:
```bash
conda activate reproAI4H
```

3. Install the required packages from requirements.txt:
```bash
pip install -r requirements.txt
```

*Note: Make sure you have Anaconda or Miniconda installed on your system before running these commands.*

### System Requirements
We note that it is crucial that you have enough GPU memory to run open source 70B LLMs for topic classification and conference paper title and author extraction. We ran all of our experiments using a single A6000 GPU with 48GB of VRAM. 

While one can potentially attempt to use smaller 8B or 7B models, their performance is typically poor.

### API's

We note that getting access to each service's API's may not be trivial. For getting access to SemanticScholar API, you will have to apply for it [here](https://www.semanticscholar.org/product/api). 


## Scraping Conference Papers


### Retrieving Conference Papers


### Cleaning PDFs

### Measuring Code Sharing and Public Dataset Usage



### Retrieving Citation Data (Semantic Scholar and SerpAPI)



## Scraping PubMed

### Medline Affiliation Extraction 


### Code Sharing and Public Dataset Usage


## Papers with Code API Check

## Topic Classification


## Manual Evaluation Results
We also include manual evaluation results in 
- `data/validation.csv`
  
which can be used to compute the final validation results in the Appendix table using
- `validation.ipynb`
