# GPU-Accelerated RAG Search

This project demonstrates a GPU-accelerated vector search for a Retrieval-Augmented Generation (RAG) database of WGSL code snippets.

The core of the project is the `gpu_rag_search.py` script, which uses the `wgpu` library to perform a brute-force similarity search on a database of WGSL code examples (`wgsl_examples.jsonl`).

## Setup

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the search script:

```bash
python3 gpu_rag_search.py
```

The script will initialize the `wgpu` device, load the database (with dummy embeddings), perform the search on the GPU, and print the top 5 most similar results to a random query vector.