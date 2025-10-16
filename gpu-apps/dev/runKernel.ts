export async function runKernel(
  device: GPUDevice,
  moduleWGSL: string,
  bindEntries: GPUBindGroupEntry[],
  workgroups: [number,number,number]=[Math.ceil(1024/16),Math.ceil(1024/16),1],
  entry="main"
) {
  const module = device.createShaderModule({ code: moduleWGSL });
  const pipe = device.createComputePipeline({ layout: "auto", compute: { module, entryPoint: entry }});
  const bg = device.createBindGroup({ layout: pipe.getBindGroupLayout(0), entries: bindEntries });
  const enc = device.createCommandEncoder();
  const pass = enc.beginComputePass();
  pass.setPipeline(pipe); pass.setBindGroup(0, bg);
  pass.dispatchWorkgroups(...workgroups); pass.end();
  device.queue.submit([enc.finish()]);
}