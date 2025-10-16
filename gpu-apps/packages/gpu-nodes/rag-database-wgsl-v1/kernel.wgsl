// RAG Database and Query Kernels
// This file defines the on-GPU data structures for the RAG corpus
// and the compute shader for performing semantic search.

// --- DATA STRUCTURES ---

struct RagEntry {
    id: u32,
    title_hash: u32,
    category: u32,
    tags: array<u32, 8>,
    code_ptr: u32,
    embedding_ptr: u32,
    score: f32,
};

struct RagDatabase {
    entry_count: u32,
    // entries are packed after this header
};

struct QueryParams {
    query_vector_dim: u32,
    num_entries: u32,
    result_limit: u32,
    threshold: f32,
};

// --- BINDINGS ---

@group(0) @binding(0) var<uniform> params: QueryParams;
@group(0) @binding(1) var<storage, read> query_embedding: array<f32>;
@group(0) @binding(2) var<storage, read> corpus_entries: array<RagEntry>;
@group(0) @binding(3) var<storage, read> corpus_embeddings: array<f32>;
@group(0) @binding(4) var<storage, read_write> results: array<RagEntry>;
@group(0) @binding(5) var<storage, read_write> result_count: atomic<u32>;

// --- KERNELS ---

fn cosine_similarity(query_vec: array<f32>, entry_emb_ptr: u32) -> f32 {
    var dot_product: f32 = 0.0;
    var q_norm_sq: f32 = 0.0;
    var c_norm_sq: f32 = 0.0;

    for (var i: u32 = 0u; i < params.query_vector_dim; i = i + 1u) {
        let q_i = query_vec[i];
        let c_i = corpus_embeddings[entry_emb_ptr + i];
        dot_product = dot_product + q_i * c_i;
        q_norm_sq = q_norm_sq + q_i * q_i;
        c_norm_sq = c_norm_sq + c_i * c_i;
    }

    return dot_product / (sqrt(q_norm_sq * c_norm_sq) + 1e-6);
}

@compute @workgroup_size(64)
fn rag_query(@builtin(global_invocation_id) gid: vec3<u32>) {
    let entry_index = gid.x;
    if (entry_index >= params.num_entries) { return; }

    let entry = corpus_entries[entry_index];
    let similarity = cosine_similarity(query_embedding, entry.embedding_ptr);

    if (similarity > params.threshold) {
        var result = entry;
        result.score = similarity;

        let result_idx = atomicAdd(&result_count, 1u);
        if (result_idx < params.result_limit) {
            results[result_idx] = result;
        }
    }
}