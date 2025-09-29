from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, Any, List
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .program import Program
from .vm_state import VMState
from .trace_models import TraceStep, step_to_ordered_dict
from .hash_chain import step_hash, ZERO_HASH


ISO = "%Y-%m-%dT%H:%M:%SZ"
FONT_PATH = "assets/Roboto-Regular.ttf"

def _to_str_list(vals: List[int]) -> List[str]:
    return [str(v) for v in vals]


def execute(
    program: Program,
    width: int = 800,
    height: int = 600,
    step_limit: int = 10_000,
    deterministic_meta: bool = False,
) -> Dict[str, Any]:
    state = VMState(ip=0, stack=[], outputs=[], status="running")
    state.framebuffer = np.zeros((height, width, 3), dtype=np.uint8)
    steps: List[TraceStep] = []
    prev = ZERO_HASH

    if deterministic_meta:
        started_at = "1970-01-01T00:00:00Z"
    else:
        started_at = datetime.now(timezone.utc).strftime(ISO)

    faulted = False

    def push(x: int) -> None:
        state.stack.append(x)

    def pop() -> int:
        if not state.stack:
            raise RuntimeError("stack underflow")
        return state.stack.pop()

    i = 0
    while state.status == "running" and i < step_limit and state.ip < len(program.instructions):
        instr = program.instructions[state.ip]
        step = TraceStep(
            index=i,
            ip=state.ip,
            op=instr.op,
            arg=instr.arg if instr.arg is not None else None,
            stack_before=_to_str_list(state.stack),
        )

        try:
            if instr.op == "NOP":
                state.ip += 1
            elif instr.op == "HALT":
                state.status = "halted"
                state.ip += 1
            elif instr.op == "PUSHI":
                assert instr.arg is not None
                push(int(instr.arg))
                state.ip += 1
            elif instr.op == "POP":
                _ = pop()
                state.ip += 1
            elif instr.op == "ADD":
                b, a = pop(), pop()
                push(a + b)
                state.ip += 1
            elif instr.op == "SUB":
                b, a = pop(), pop()
                push(a - b)
                state.ip += 1
            elif instr.op == "MUL":
                b, a = pop(), pop()
                push(a * b)
                state.ip += 1
            elif instr.op == "DIV":
                b, a = pop(), pop()
                if b == 0:
                    raise RuntimeError("division by zero")
                # truncate toward zero
                push(int(a / b))
                state.ip += 1
            elif instr.op == "PRINT":
                val = pop()
                state.outputs.append(val)
                step.output = str(val)
                state.ip += 1
            elif instr.op == "RECT_FILL":
                color_packed = pop()
                h = pop()
                w = pop()
                y = pop()
                x = pop()
                r = (color_packed >> 16) & 0xFF
                g = (color_packed >> 8) & 0xFF
                b = color_packed & 0xFF
                color = (r, g, b)

                fb = state.framebuffer
                if fb is not None:
                    x0 = max(0, x)
                    y0 = max(0, y)
                    x1 = min(width, x + w)
                    y1 = min(height, y + h)
                    fb[y0:y1, x0:x1] = color
                state.ip += 1
            elif instr.op == "TEXT_RENDER":
                text = instr.arg
                assert text is not None
                size = pop()
                color_packed = pop()
                y = pop()
                x = pop()

                r = (color_packed >> 16) & 0xFF
                g = (color_packed >> 8) & 0xFF
                b = color_packed & 0xFF
                color = (r, g, b)

                font = ImageFont.truetype(FONT_PATH, size)

                # Render text on a temporary transparent surface
                text_width, text_height = font.getbbox(text)[2:]
                text_surface = Image.new('RGBA', (text_width, text_height), (0,0,0,0))
                draw = ImageDraw.Draw(text_surface)
                draw.text((0, 0), text, font=font, fill=(*color, 255))

                # Alpha blend this surface onto the framebuffer
                fb = state.framebuffer
                if fb is not None:
                    img_fb = Image.fromarray(fb)
                    img_fb.paste(text_surface, (x, y), text_surface)
                    state.framebuffer = np.array(img_fb)

                state.ip += 1
            else:
                raise RuntimeError(f"unknown opcode: {instr.op}")
        except Exception as e:
            step.fault = str(e)
            state.status = "faulted"
            faulted = True

        step.stack_after = _to_str_list(state.stack)
        core = step_to_ordered_dict(step)
        h = step_hash(core, prev)
        step.step_hash = h
        prev = h
        steps.append(step)
        i += 1

    if i >= step_limit and state.status == "running":
        # exceeded step limit - halt gracefully (not a fault)
        state.status = "halted"

    if deterministic_meta:
        finished_at = "1970-01-01T00:00:00Z"
    else:
        finished_at = datetime.now(timezone.utc).strftime(ISO)
    meta = {
        "version": "dvc-trace-0.1",
        "step_limit": step_limit,
        "halted": state.status == "halted",
        "faulted": faulted,
        "outputs": _to_str_list(state.outputs),
        "final_root": prev,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    trace = {
        "meta": meta,
        "steps": [
            {
                **step_to_ordered_dict(s),
                "step_hash": s.step_hash,
            }
            for s in steps
        ],
        "framebuffer": state.framebuffer.tolist() if state.framebuffer is not None else None,
    }
    return trace

