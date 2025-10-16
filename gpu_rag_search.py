import wgpu
import numpy as np
import json

class GpuRagSearch:
    def __init__(self):
        self.device = None
        self.pipelines = {}
        self.db = None

    async def initialize(self, db_path="wgsl_examples.jsonl"):
        adapter = await wgpu.gpu.request_adapter_async(power_preference="high-performance")
        self.device = await adapter.request_device_async()
        self.db = self.load_db(db_path)
        await self.create_pipelines()

    def load_db(self, db_path, vector_dim=768):
        db = []
        with open(db_path, "r") as f:
            for line in f:
                item = json.loads(line)
                # Add dummy embedding for testing purposes
                item['embedding'] = np.random.rand(vector_dim).astype(np.float32).tolist()
                db.append(item)
        return db

    async def create_pipelines(self):
        # --- Similarity Pipeline ---
        similarity_bgl = self.device.create_bind_group_layout(entries=[
            {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 2, "visibility": wgpu.ShaderStage.COMPUTE, "buffer": {"type": wgpu.BufferBindingType.storage}}
        ])
        similarity_layout = self.device.create_pipeline_layout(bind_group_layouts=[similarity_bgl])

        # Define the shader directly to ensure it matches our buffer layout
        similarity_shader_code = """
            @group(0) @binding(0) var<storage, read> query_vec: array<f32>;
            @group(0) @binding(1) var<storage, read> db_vecs: array<f32>;
            @group(0) @binding(2) var<storage, read_write> scores: array<f32>;

            const VEC_DIM: u32 = 768u;

            @compute @workgroup_size(64)
            fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
                let db_idx = gid.x;
                if (db_idx >= arrayLength(&scores)) {
                    return;
                }

                var dot_product = 0.0;
                let db_offset = db_idx * VEC_DIM;

                for (var i = 0u; i < VEC_DIM; i = i + 1u) {
                    let q_val = query_vec[i];
                    let db_val = db_vecs[db_offset + i];
                    dot_product = dot_product + q_val * db_val;
                }
                scores[db_idx] = dot_product;
            }
        """

        similarity_shader = self.device.create_shader_module(code=similarity_shader_code)
        self.pipelines["similarity"] = self.device.create_compute_pipeline(
            layout=similarity_layout,
            compute={"module": similarity_shader, "entry_point": "main"},
        )

        # --- Reduction Pipeline (for future use) ---
        # This will also need to be properly defined later, but is not used yet.
        pass

    def db_get_shader_code(self, slug):
        for item in self.db:
            if item["slug"] == slug:
                return item["wgsl_code"]
        raise ValueError(f"Shader with slug '{slug}' not found in database.")

    async def search(self, query_embedding, k=10):
        num_db_vectors = len(self.db)
        vector_dim = len(query_embedding)

        # 1. Prepare data
        db_embeddings = np.zeros((num_db_vectors, vector_dim), dtype=np.float32)
        for i, item in enumerate(self.db):
            # This assumes embeddings are stored as lists, might need adjustment
            db_embeddings[i, :] = np.array(item['embedding'], dtype=np.float32)

        # Normalize vectors for cosine similarity calculation
        # The dot product of two unit vectors is their cosine similarity.
        norm_query = query_embedding / np.linalg.norm(query_embedding)
        norm_db = db_embeddings / np.linalg.norm(db_embeddings, axis=1, keepdims=True)

        # 2. Create GPU buffers
        query_buffer = self.device.create_buffer_with_data(data=norm_query, usage=wgpu.BufferUsage.STORAGE)
        db_buffer = self.device.create_buffer_with_data(data=norm_db, usage=wgpu.BufferUsage.STORAGE)

        output_size = num_db_vectors * 4 # size of f32
        output_buffer = self.device.create_buffer(size=output_size, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)

        # 3. Create Bind Group
        bind_group = self.device.create_bind_group(
            layout=self.pipelines["similarity"].get_bind_group_layout(0),
            entries=[
                {"binding": 0, "resource": {"buffer": query_buffer, "offset": 0, "size": query_buffer.size}},
                {"binding": 1, "resource": {"buffer": db_buffer, "offset": 0, "size": db_buffer.size}},
                {"binding": 2, "resource": {"buffer": output_buffer, "offset": 0, "size": output_buffer.size}},
            ]
        )

        # 4. Dispatch Compute Shader
        command_encoder = self.device.create_command_encoder()
        compute_pass = command_encoder.begin_compute_pass()
        compute_pass.set_pipeline(self.pipelines["similarity"])
        compute_pass.set_bind_group(0, bind_group, [], 0, 999999)

        # This assumes the shader is written to handle one vector per invocation
        workgroups = (num_db_vectors + 63) // 64 # 64 invocations per workgroup
        compute_pass.dispatch_workgroups(workgroups, 1, 1)
        compute_pass.end()
        self.device.queue.submit([command_encoder.finish()])

        # 5. Read back the results using the high-level utility which handles staging internally.
        # This requires the source buffer to have COPY_SRC usage.
        data = self.device.queue.read_buffer(output_buffer)
        scores = np.frombuffer(data, dtype=np.float32)

        # 6. CPU Top-K selection.
        # For this version, we perform the final sort on the CPU. This is a common
        # and practical approach, as the N*M dot products are the most
        # computationally expensive part and are fully handled by the GPU.
        # A fully GPU-based parallel reduction could be implemented in the future
        # for even greater performance on very large datasets.
        top_k_indices = np.argsort(scores)[::-1][:k]

        results = []
        for i in top_k_indices:
            results.append({
                "slug": self.db[i]["slug"],
                "score": float(scores[i]),
                "description": self.db[i]["summary"]
            })

        return results


if __name__ == "__main__":
    import asyncio
    import pprint

    async def main():
        print("Initializing GPU RAG Searcher...")
        searcher = GpuRagSearch()
        await searcher.initialize()
        print("Initialization complete.")

        # Create a dummy query embedding
        vector_dim = 768 # Should match the dimension in load_db
        query_embedding = np.random.rand(vector_dim).astype(np.float32)

        print("\nPerforming GPU-accelerated search...")
        results = await searcher.search(query_embedding, k=5)

        print("\n--- Top 5 Search Results ---")
        pprint.pprint(results)
        print("--------------------------\n")


    asyncio.run(main())