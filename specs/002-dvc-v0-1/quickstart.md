# Quickstart — DVC v0.1 Core

1. Author a small program (JSON IR)
```
[
  {"op":"PUSHI","arg":"2"},
  {"op":"PUSHI","arg":"3"},
  {"op":"ADD"},
  {"op":"PRINT"},
  {"op":"HALT"}
]
```

2. Run program and produce trace
```
dvc run --program examples/add.json --trace out/trace.json --limit 10000 --format json
```

3. Verify the trace
```
dvc verify --trace out/trace.json --semantic --format json
```

Expected: valid verification, final_root present, outputs ["5"].

