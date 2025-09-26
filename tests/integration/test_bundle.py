import pytest
import json
import zipfile
import hashlib
from pathlib import Path
from argparse import Namespace
from io import StringIO
import sys

from dvc_cli.main import cmd_pack, cmd_verify

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path

@pytest.fixture
def dummy_files(temp_dir):
    image_path = temp_dir / "test_image.png"
    palette_path = temp_dir / "test_palette.json"
    program_path = temp_dir / "test_program.json"
    trace_path = temp_dir / "test_trace.json"

    image_path.write_bytes(b"dummy_image_data")
    palette_path.write_text('{"version": "palette-v0.1", "tile_size": 1, "opcodes": {"FF0000": "RED_OP"}}')
    program_path.write_text('[{"op": "RED_OP"}]')
    trace_path.write_text('{"meta": {"final_root": "test_root", "color_provenance": {}}}')

    return {"image": image_path, "palette": palette_path, "program": program_path, "trace": trace_path}

def calculate_file_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

class TestDVCBundleCommands:
    def test_pack_command_success(self, dummy_files, temp_dir):
        output_bundle = temp_dir / "output.dvcf"
        args = Namespace(
            image=dummy_files["image"],
            palette=dummy_files["palette"],
            program=dummy_files["program"],
            trace=dummy_files["trace"],
            out=output_bundle,
            format="json"
        )

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        return_code = cmd_pack(args)
        sys.stdout = old_stdout

        assert return_code == 0
        summary = json.loads(captured_output.getvalue())
        assert summary["status"] == "success"
        assert output_bundle.exists()

        with zipfile.ZipFile(output_bundle, 'r') as zf:
            assert "manifest.json" in zf.namelist()

    def test_verify_bundle_command_success(self, dummy_files, temp_dir):
        output_bundle = temp_dir / "output.dvcf"
        pack_args = Namespace(image=dummy_files["image"], palette=dummy_files["palette"], program=dummy_files["program"], trace=dummy_files["trace"], out=output_bundle, format="json")
        
        # Capture pack output to avoid polluting test output
        with StringIO() as captured_output:
            old_stdout = sys.stdout
            sys.stdout = captured_output
            cmd_pack(pack_args)
            sys.stdout = old_stdout

        verify_args = Namespace(bundle=output_bundle, trace=None, strict=False, replay=False, format="json")
        
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        return_code = cmd_verify(verify_args)
        sys.stdout = old_stdout

        assert return_code == 0
        summary = json.loads(captured_output.getvalue())
        assert summary["status"] == "valid"

    def test_verify_bundle_command_missing_file_failure(self, temp_dir):
        corrupted_bundle = temp_dir / "corrupted.dvcf"
        with zipfile.ZipFile(corrupted_bundle, 'w') as zf:
            zf.writestr("manifest.json", '{"program": {"path": "missing.json"}}')

        verify_args = Namespace(bundle=corrupted_bundle, trace=None, strict=False, replay=False, format="json")

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        return_code = cmd_verify(verify_args)
        sys.stdout = old_stdout

        assert return_code == 1
        summary = json.loads(captured_output.getvalue())
        assert summary["status"] == "error"
        assert "Manifest is missing its own SHA256 hash" in summary["error"]

    def test_verify_bundle_command_hash_mismatch_failure(self, dummy_files, temp_dir):
        output_bundle = temp_dir / "output.dvcf"
        pack_args = Namespace(image=dummy_files["image"], palette=dummy_files["palette"], program=dummy_files["program"], trace=dummy_files["trace"], out=output_bundle, format="json", deterministic_meta=True)
        with StringIO() as captured_output: # Suppress output
            old_stdout = sys.stdout
            sys.stdout = captured_output
            cmd_pack(pack_args)
            sys.stdout = old_stdout

        corrupted_bundle = temp_dir / "corrupted_hash.dvcf"
        with zipfile.ZipFile(corrupted_bundle, 'w') as zf_corrupt:
            with zipfile.ZipFile(output_bundle, 'r') as zf_orig:
                for item in zf_orig.infolist():
                    if item.filename == "manifest.json":
                        manifest = json.loads(zf_orig.read(item.filename))
                        manifest["program"]["sha256"] = "corrupted" # Deliberately corrupt the hash
                        zf_corrupt.writestr(item.filename, json.dumps(manifest, indent=2))
                    else:
                        zf_corrupt.writestr(item, zf_orig.read(item.filename))

        verify_args = Namespace(bundle=corrupted_bundle, trace=None, strict=False, replay=False, format="json")

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        return_code = cmd_verify(verify_args)
        sys.stdout = old_stdout

        assert return_code == 1
        summary = json.loads(captured_output.getvalue())
        assert summary["status"] == "error"
        assert summary["error"] == "Manifest SHA256 hash mismatch"

    def test_pack_determinism(self, dummy_files, temp_dir):
        output_bundle_1 = temp_dir / "output_1.dvcf"
        output_bundle_2 = temp_dir / "output_2.dvcf"

        args_1 = Namespace(image=dummy_files["image"], palette=dummy_files["palette"], program=dummy_files["program"], trace=dummy_files["trace"], out=output_bundle_1, format=None, deterministic_meta=True)
        args_2 = Namespace(image=dummy_files["image"], palette=dummy_files["palette"], program=dummy_files["program"], trace=dummy_files["trace"], out=output_bundle_2, format=None, deterministic_meta=True)

        cmd_pack(args_1)
        cmd_pack(args_2)

        bytes_1 = output_bundle_1.read_bytes()
        bytes_2 = output_bundle_2.read_bytes()

        assert bytes_1 == bytes_2