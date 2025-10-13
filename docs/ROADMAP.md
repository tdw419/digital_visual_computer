# GVPIE Development Roadmap
## Building the Future in WGSL

## Core Philosophy

**CPU Sovereignty Ended: October 2025**
- Bootstrap is frozen.
- All innovation happens in shaders.
- The I/O contract is the only interface to the host.

**GPU Sovereignty Principles:**
1.  Compute-first architecture.
2.  Massive parallelism for all complex operations.
3.  Persistent state lives entirely in GPU memory.
4.  Procedural generation over data transfer.

---

## Phase 1: Foundation (COMPLETE)

### ✅ Text Buffer Engine
- [x] Gap buffer implementation for O(1) edits.
- [x] Cursor management and navigation.
- [x] Line indexing for fast line-based operations.

### ✅ Rendering Pipeline
- [x] Procedural, instanced character rendering.
- [x] Viewport scrolling and cursor blinking.
- [x] Font atlas support.

**Status**: The core engine is operational. Ready for the feature layer.

---

## Phase 2: Core Editor Features (4-6 Weeks)

### 2.1: Advanced Navigation & Selection
- **Goal**: Implement modern text selection and navigation.
- **Features**:
    - Word jumping (Ctrl+Arrow).
    - Shift-based text selection.
    - Clipboard integration via I/O contract (`REQUEST_CLIPBOARD_READ/WRITE`).

### 2.2: File Operations
- **Goal**: Load from and save to the file system.
- **Features**:
    - Request file open/save via I/O contract.
    - Handle file data payload from `file_io` buffer.
    - Display file path and modification status.

### 2.3: Undo/Redo
- **Goal**: Implement a robust undo/redo system.
- **Architecture**:
    - An `UndoStack` in the `EditorState` buffer.
    - Store inverse operations (e.g., an `INSERT` undoes a `DELETE`).
    - Coalesce rapid, single-character edits into larger operations.

### 2.4: Search & Replace
- **Goal**: Basic text search and replace functionality.
- **Architecture**:
    - A simple, single-threaded search for now.
    - UI will be command-driven (no on-screen widgets yet).
    - Later, this will be a prime candidate for parallelization.

---

## Phase 3: Advanced Capabilities (6-10 Weeks)

### 3.1: Parallel Syntax Highlighting
- **Goal**: Fast, incremental syntax highlighting.
- **Architecture**:
    - A compute shader pass that tokenizes the text.
    - Each workgroup processes a chunk of lines.
    - Store token types in a new `SyntaxState` buffer.
    - Re-parse only dirty lines on edit.

### 3.2: LSP Integration
- **Goal**: Provide modern IDE features like completion and diagnostics.
- **Architecture**:
    - Extend the I/O contract with LSP request types (`REQUEST_LSP_COMPLETION`, etc.).
    - The host acts as a simple proxy to a standard language server.
    - Render diagnostics (squiggles) and completion menus in the render shader.

### 3.3: Multi-Cursor Editing
- **Goal**: Enable multiple simultaneous editing points.
- **Architecture**:
    - Store an array of cursor positions in `EditorState`.
    - Modify editing logic (`insert_char`, etc.) to operate on all cursors in parallel.
    - Requires careful sorting of cursors to avoid conflicts.

---

## Phase 4: The Ecosystem (10+ Weeks)

### 4.1: Plugin System
- **Goal**: Allow third-party extension of the editor.
- **Architecture**:
    - Plugins are themselves compute shaders.
    - The main compute shader dispatches to plugin shaders based on registered hooks (e.g., `on_key_press`).
    - Plugins get a sandboxed region of GPU memory to manage their own state.

### 4.2: Git Integration
- **Goal**: Provide in-editor Git status and operations.
- **Architecture**:
    - I/O contract requests for `git status`, `git diff`, etc.
    - The host runs the Git commands and returns results in a buffer.
    - Render gutter indicators (+/-/~) for changed lines.

### 4.3: Terminal Emulator
- **Goal**: A fully functional terminal, rendered on the GPU.
- **Architecture**:
    - A complete VT100-style terminal emulator written in a WGSL compute shader.
    - Manages its own screen buffer and state.
    - I/O contract for shell process communication.

---

## The Vision: GPU-Native Development

Where does this lead? To features impossible in traditional, CPU-bound editors:
- **Real-time, whole-project semantic analysis**: Run a language server for your entire codebase, in parallel, on every keystroke.
- **Live, collaborative editing with hundreds of users**: Use parallel CRDT algorithms to merge changes with near-zero latency.
- **Integrated data visualization**: Render charts, graphs, or 3D models directly in your editor from data files.

The bootstrap is frozen. The GPU is sovereign. This roadmap is the path to building the future of computing.