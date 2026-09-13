---
license: cc-by-4.0
task_categories:
- text-generation
language:
- hi
tags:
- BFCL
- Hindi
pretty_name: Hindi BFCL
size_categories:
- 1K<n<10K
---

## Dataset Description:
The BFCL-Hi (Hindi BFCL) dataset evaluates the function-calling capability of large language models (LLMs) when questions are asked in Hindi. This is the GCP-translated version of the English BFCL dataset, in which question-function-answer pairs across various domains and multiple languages are originally curated in English.

This dataset is ready for commercial/non-commercial use.
The evaluation steps are described [here](https://huggingface.co/datasets/nvidia/BFCL-Hi/blob/main/EVAL.md). <br>
Other Hindi benchmark datasets: [ [IFEval-Hi](https://huggingface.co/datasets/nvidia/IFEval-Hi) | [MT-Bench-Hi](https://huggingface.co/datasets/nvidia/MT-Bench-Hi) | [GSM8K-Hi](https://huggingface.co/datasets/nvidia/GSM8K-Hi) | [BFCL-Hi](https://huggingface.co/datasets/nvidia/BFCL-Hi) | [ChatRAG-Hi](https://huggingface.co/datasets/nvidia/ChatRAG-Hi) ]

## Dataset Owner:
NVIDIA Corporation


## Dataset Creation Date:
April 2025

## License/Terms of Use: 
This dataset is licensed under the Creative Commons Attribution 4.0 International License (CC-BY-4.0). Additional Information: Apache
2.0 License.

## Intended Usage:
Evaluate LLM's ability to call functions and tools when queries are asked in the Hindi language.

## Dataset Characterization
Data Collection Method<br>
* Synthetic<br>

Labeling Method<br>
* Not Applicable <br>

## Dataset Format
Text

## Dataset Quantification
6.9MB of prompt-label pairs, comprising 2251 individual samples.

## Ethical Considerations:
NVIDIA believes Trustworthy AI is a shared responsibility, and we have established policies and practices to enable development for a wide array of AI applications.  When downloaded or used in accordance with our terms of service, developers should work with their internal model team to ensure this model meets requirements for the relevant industry and use case and addresses unforeseen product misuse.   

Please report security vulnerabilities or NVIDIA AI Concerns [here](https://www.nvidia.com/en-us/support/submit-security-vulnerability/).

## Citing

If you find our work helpful, please consider citing our paper:
```
@article{kamath2025benchmarking,
  title={Benchmarking Hindi LLMs: A New Suite of Datasets and a Comparative Analysis},
  author={Kamath, Anusha and Singla, Kanishk and Paul, Rakesh and Joshi, Raviraj and Vaidya, Utkarsh and Chauhan, Sanjay Singh and Wartikar, Niranjan},
  journal={arXiv preprint arXiv:2508.19831},
  year={2025}
}
```
