from typing import List, Dict, Any

class ColorLowerer:
    def __init__(self):
        pass

    def lower_to_dvc_ir(self, decoded_opcodes: List[Any]) -> Dict[str, Any]:
        """Converts a list of decoded opcodes into DVC JSON Intermediate Representation."""
        program = []
        unrecognized_colors_count = 0

        for opcode in decoded_opcodes:
            if opcode is None:
                unrecognized_colors_count += 1
                program.append({"opcode": "NOP", "comment": "Unrecognized color"})
            else:
                program.append({"opcode": opcode})
        
        dvc_ir = {
            "metadata": {
                "compiler": "ColorLowerer-v0.1",
                "unrecognized_colors": unrecognized_colors_count
            },
            "program": program
        }
        return dvc_ir
