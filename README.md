# GVPIE Map OS - v1.0 (Frozen)

## The Foundation of the GPU Operating System

This directory contains the core of the GVPIE Map OS, the second frozen layer of the GPU Sovereignty project. Where the Rust bootstrap is the hardware abstraction layer, the Map OS is the **kernel and desktop environment** for all future GPU-native applications.

The core principle is a **2D infinite map**, which serves as the fundamental workspace. All other components—text editors, file managers, terminals, and even 3D worlds—are applications that run *on top of* this map.

## Core Concepts

-   **Infinite Canvas**: The map provides an unlimited 2D space for organizing work. You can pan and zoom to navigate this space.
-   **Cards**: These are the primary primitive, analogous to windows or files. Each card is a distinct object on the map that can hold content (text, code, images, etc.).
-   **GPU Sovereignty**: All state management, interaction logic, and rendering for the map are handled entirely by WGSL shaders on the GPU. The CPU's only role is to forward raw input events.

## Files in this System

-   **`src/map_io_contract.rs`**: The canonical Rust definition of all shared data structures (`Camera`, `Card`, `MapState`) and constants. This is the **single source of truth**.
-   **`shaders/map_contract.wgsl`**: The WGSL mirror of the Rust contract. All map-related shaders import this to ensure perfect CPU-GPU alignment.
-   **`shaders/map_compute.wgsl`**: The "kernel" of the Map OS. This shader manages all state, including camera physics, card positions, and user input processing.
-   **`shaders/map_render.wgsl`**: The "compositor" of the Map OS. It visualizes the state by procedurally rendering the grid, cards, and their content.

## How to Interact (Default Keybindings)

-   **Pan**: `W`, `A`, `S`, `D` or Arrow Keys. The camera has momentum for smooth navigation.
-   **Zoom**: Mouse Wheel.
-   **Select Card**: Left-click on a card.
-   **Drag Card**: Click and drag a selected card.
-   **Create Card**: `Ctrl+N` (Not yet implemented, but planned).

## The Frozen Contract

Once this Map OS is deemed stable and feature-complete for its foundational role, it will be **frozen**. Just like the Rust bootstrap, its core logic will become immutable.

Why? To provide a **stable platform**. All future applications will be built on the guarantee that the Map OS's core services (memory management, rendering, state) will never change in a breaking way. This is how a true operating system is built.

## Future Development

All future work happens by building applications **on top of the map**:
1.  **Text Editor**: A "text editor" application will be a specific type of card that allows for rich text editing, using the text engine previously developed.
2.  **File Manager**: An application that visualizes the on-GPU file system as a series of connected cards.
3.  **3D Worlds**: A 3D view will be an *option* within the 2D map—a "portal" card that opens up a 3D scene, built on the stable 2D foundation.

This layered, frozen-core approach is the key to achieving a robust, extensible, and truly GPU-sovereign operating environment.