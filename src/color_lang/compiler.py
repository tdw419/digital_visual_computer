import json
from typing import List, Dict, Any, Tuple

from PIL import Image

from .decoder import PngDecoder
from .palette import ColorPalette, PaletteError
from .lower import ColorLowerer # New import

class ColorCompiler:
    def __init__(self, palette: ColorPalette):
        self.palette = palette
        self.decoder = PngDecoder(palette)
        self.lowerer = ColorLowerer() # New instance

    def compile_png_to_dvc_ir(self, file_path: str) -> Dict[str, Any]: # Changed return type
        """Compiles a PNG file into DVC JSON Intermediate Representation."""
        decoded_opcodes, grid_width, grid_height = self.decoder.decode_png(file_path)
        
        dvc_ir = self.lowerer.lower_to_dvc_ir(decoded_opcodes) # Use lowerer
        
        # Add compiler-specific metadata
        dvc_ir["metadata"]["source_file"] = file_path
        dvc_ir["metadata"]["compiler"] = "ColorCompiler-v0.1" # Override lowerer's compiler info
        dvc_ir["metadata"]["grid_size"] = {"width": grid_width, "height": grid_height}
        
        return dvc_ir # Only return dvc_ir

    def generate_compilation_summary(self, dvc_ir: Dict[str, Any]) -> str:
        """Generates a human-readable summary of the compilation process."""
        summary = f"Compilation Summary for {dvc_ir['metadata']['source_file']}:\n"
        summary += f"  Compiler: {dvc_ir['metadata']['compiler']}:\n"
        summary += f"  Total Instructions: {len(dvc_ir['program'])}\n"
        summary += f"  Unrecognized Colors: {dvc_ir['metadata']['unrecognized_colors']}\n"
        summary += f"  Grid Size: {dvc_ir['metadata']['grid_size']['width']}x{dvc_ir['metadata']['grid_size']['height']}\n"
        
        # You could add more details here, like opcode distribution, warnings, etc.
        
        return summary

    def compile_and_summarize(self, file_path: str) -> Tuple[Dict[str, Any], str]:
        """Compiles a PNG and returns both the DVC IR and a compilation summary."""
        dvc_ir = self.compile_png_to_dvc_ir(file_path) # Removed grid_size
        summary = self.generate_compilation_summary(dvc_ir)
        return dvc_ir, summary
