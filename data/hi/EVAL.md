# BFCL-Hi Evaluation

## Overview

BFCL-Hi (Berkeley Function-Calling Leaderboard - Hindi) is a Hindi adaptation of the BFCL benchmark, designed to evaluate the function-calling capabilities of Large Language Models in Hindi. This benchmark assesses models' ability to understand function descriptions and generate appropriate function calls based on natural language instructions.

## Evaluation Workflow

BFCL-Hi follows the **BFCL v2 evaluation methodology** from the original GitHub repository, utilizing the same framework for assessing function-calling capabilities.

### Evaluation Steps

1. **Load the dataset** (see important note below about dataset loading)
2. **Generate model responses** with function calls based on the prompts
3. **Evaluate function-calling accuracy** using the BFCL v2 evaluation scripts
4. **Obtain metrics** including execution accuracy, structural correctness, and other BFCL metrics

## Important: Dataset Loading

⚠️ **DO NOT use the HuggingFace `load_dataset` method** to load the BFCL-Hi dataset.

The dataset files are hosted on HuggingFace but are **not compatible** with the HuggingFace datasets package. This is consistent with the English version of the dataset. 

**Recommended Approach:**
- Download the JSON files directly from the HuggingFace repository
- Load them manually using standard JSON loading methods
- Follow the BFCL v2 repository's data loading methodology

## Implementation

Please follow the **same methodology as BFCL v2 (English)** as documented in the official resources below.

## Setup and Usage

### Step 1: Installation

Clone the Gorilla repository and install dependencies:

```bash
git clone https://github.com/ShishirPatil/gorilla.git
cd gorilla/berkeley-function-call-leaderboard
pip install -r requirements.txt
```

### Step 2: Prepare Your Dataset

- Place your dataset files in the appropriate directory
- Follow the data format specifications from the English BFCL v2

### Step 3: Generate Model Responses

Run inference to generate function calls from your model:

```bash
python openfunctions_evaluation.py \
  --model <model_name> \
  --test-category <category> \
  --num-gpus <num_gpus>
```

**Key Parameters:**
- `--model`: Your model name or path
- `--test-category`: Category to test (e.g., `all`, `simple`, `multiple`, `parallel`, etc.)
- `--num-gpus`: Number of GPUs to use

**For Hindi (BFCL-Hi):**
- Ensure you load the Hindi version of the dataset
- Modify the inference code according to your model and hosted inference framework

**Available Test Categories in BFCL-Hi:**
- `simple`: Single function calls
- `multiple`: Multiple function calls
- `parallel`: Parallel function calls
- `parallel_multiple`: Combination of parallel and multiple function calls
- `relevance`: Testing function relevance detection
- `irrelevance`: Testing irrelevant function call handling

### Step 4: Evaluate Results

Evaluate the generated function calls against ground truth:

```bash
python eval_runner.py \
  --model <model_name> \
  --test-category <category>
```

This will:
- Parse the generated function calls
- Compare with ground truth
- Calculate accuracy metrics
- Generate detailed error analysis

### Step 5: View Results

Results will be saved in the output directory with metrics including:
- **Execution Accuracy**: Whether the function call executes correctly
- **Structural Correctness**: Whether the function call structure is valid
- **Argument Accuracy**: Whether arguments are correctly formatted
- **Overall Score**: Aggregated performance metric

You can also create custome Evaluation Script based on the above for more control over the evaluation process. 

### Official BFCL v2 Resources

- **GitHub Repository**: [Berkeley Function-Calling Leaderboard](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard)
  - Complete evaluation framework and scripts
  - Dataset loading instructions
  - Evaluation metrics implementation

- **BFCL v2 Documentation**: [BFCL v2 Release](https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html)
  - Overview of v2 improvements and methodology
  
- **Gorilla Project**: [https://gorilla.cs.berkeley.edu/](https://gorilla.cs.berkeley.edu/)
  - Main project page with additional resources

- **Research Paper**: [Gorilla: Large Language Model Connected with Massive APIs](https://arxiv.org/abs/2305.15334)
  - Patil et al., arXiv:2305.15334 (2023)