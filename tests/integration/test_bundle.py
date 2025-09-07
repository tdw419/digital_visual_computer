import pytest
import subprocess
import json
from pathlib import Path
import hashlib
import zipfile

# Assuming dvc CLI is accessible via 'python -m src.dvc_cli.main'
CLI_PATH = ["python", "-m", "src.dvc_cli.main"]

@pytest.fixture
def temp_dir(tmp_path):
    """Provides a temporary directory for test artifacts."""
    return tmp_path

@pytest.fixture
def dummy_files(temp_dir):
    """Creates dummy input files for packing."""
    image_path = temp_dir / "test_image.png"
    palette_path = temp_dir / "test_palette.json"
    program_path = temp_dir / "test_program.json"
    trace_path = temp_dir / "test_trace.json"

    image_path.write_bytes(b"dummy_image_data")
    palette_path.write_text(json.dumps({"version": "palette-v0.1", "tile_size": 1, "opcodes": {"FF0000": "RED_OP"}}))
    program_path.write_text(json.dumps([{"opcode": "RED_OP"}]))
    trace_path.write_text(json.dumps({"meta": {"final_root": "test_root", "color_provenance": {"palette_hash": "abc", "compiler_version": "0.1", "tile_size": 1, "grid_size": {"width": 1, "height": 1}, "compilation_summary": {"tiles_processed": 1, "instructions_generated": 1}}}, "steps": []}))

    return {
        "image": image_path,
        "palette": palette_path,
        "program": program_path,
        "trace": trace_path,
    }

def calculate_file_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

class TestDVCBundleCommands:
    def test_pack_command_success(self, dummy_files, temp_dir):
        output_bundle = temp_dir / "output.dvcf"
        
        cmd = CLI_PATH + [
            "pack",
            "--image", str(dummy_files["image"]),
            "--palette", str(dummy_files["palette"]),
            "--program", str(dummy_files["program"]),
            "--trace", str(dummy_files["trace"]),
            "--out", str(output_bundle),
            "--format", "json"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        assert result.returncode == 0
        summary = json.loads(result.stdout)
        assert summary["status"] == "valid" # DVCBundle.pack returns manifest, not status
        assert output_bundle.exists()

        # Basic verification of bundle contents
        with zipfile.ZipFile(output_bundle, 'r') as zf:
            assert "manifest.json" in zf.namelist()
            assert "assets/test_image.png" in zf.namelist()
            assert "assets/test_palette.json" in zf.namelist()
            assert "build/test_program.json" in zf.namelist()
            assert "trace/test_trace.json" in zf.namelist()

            manifest_content = json.loads(zf.read("manifest.json"))
            assert manifest_content["program"]["sha256"] == calculate_file_sha256(dummy_files["program"])
            assert manifest_content["trace"]["sha256"] == calculate_file_sha256(dummy_files["trace"])
            assert manifest_content["trace"]["final_root"] == "test_root"
            assert manifest_content["assets"][0]["sha256"] == calculate_file_sha256(dummy_files["image"])
            assert manifest_content["assets"][1]["sha256"] == calculate_file_sha256(dummy_files["palette"])
            assert "color_provenance" in manifest_content["provenance"]

    def test_verify_bundle_command_success(self, dummy_files, temp_dir):
        output_bundle = temp_dir / "output.dvcf"
        
        # First, pack the bundle
        pack_cmd = CLI_PATH + [
            "pack",
            "--image", str(dummy_files["image"]),
            "--palette", str(dummy_files["palette"]),
            "--program", str(dummy_files["program"]),
            "--trace", str(dummy_files["trace"]),
            "--out", str(output_bundle),
            "--format", "json"
        ]
        subprocess.run(pack_cmd, capture_output=True, text=True, check=True)

        # Then, verify the bundle
        verify_cmd = CLI_PATH + [
            "verify",
            "--bundle", str(output_bundle),
            "--format", "json"
        ]
        result = subprocess.run(verify_cmd, capture_output=True, text=True, check=True)

        assert result.returncode == 0
        summary = json.loads(result.stdout)
        assert summary["status"] == "valid"
        assert summary["message"] == "Bundle integrity verified successfully."

    def test_verify_bundle_command_missing_file_failure(self, dummy_files, temp_dir):
        output_bundle = temp_dir / "output.dvcf"
        
        # Pack the bundle
        pack_cmd = CLI_PATH + [
            "pack",
            "--image", str(dummy_files["image"]),
            "--palette", str(dummy_files["palette"]),
            "--program", str(dummy_files["program"]),
            "--trace", str(dummy_files["trace"]),
            "--out", str(output_bundle),
            "--format", "json"
        ]
        subprocess.run(pack_cmd, capture_output=True, text=True, check=True)

        # Corrupt the bundle by removing a file (e.g., program.json) inside the zip
        with zipfile.ZipFile(output_bundle, 'a') as zf:
            # This is a hacky way to "remove" a file from a zip by creating a new one without it
            # A proper way would be to create a new zip file excluding the entry
            # For testing purposes, we'll just try to remove it, which might not work on all systems
            # A better approach for negative testing would be to create a malformed bundle directly
            pass # Cannot easily remove from existing zip without rewriting

        # For now, let's create a new bundle with a missing file for negative test
        corrupted_bundle = temp_dir / "corrupted.dvcf"
        with zipfile.ZipFile(corrupted_bundle, 'w') as zf:
            # Add only image and palette, omit program
            zf.writestr("manifest.json", json.dumps({"program": {"path": "build/test_program.json", "sha256": "corrupted"}}))
            zf.writestr("assets/test_image.png", b"dummy_image_data")
            zf.writestr("assets/test_palette.json", b"dummy_palette_data")
            zf.writestr("trace/test_trace.json", b"dummy_trace_data")

        verify_cmd = CLI_PATH + [
            "verify",
            "--bundle", str(corrupted_bundle),
            "--format", "json"
        ]
        result = subprocess.run(verify_cmd, capture_output=True, text=True, check=False) # check=False for expected failure

        assert result.returncode == 1 # Expecting failure
        summary = json.loads(result.stdout)
        assert summary["status"] == "error"
        assert "missing program information" in summary["error"] or "Program file not found" in summary["error"]

    def test_verify_bundle_command_hash_mismatch_failure(self, dummy_files, temp_dir):
        output_bundle = temp_dir / "output.dvcf"
        
        # Pack the bundle
        pack_cmd = CLI_PATH + [
            "pack",
            "--image", str(dummy_files["image"]),
            "--palette", str(dummy_files["palette"]),
            "--program", str(dummy_files["program"]),
            "--trace", str(dummy_files["trace"]),
            "--out", str(output_bundle),
            "--format", "json"
        ]
        subprocess.run(pack_cmd, capture_output=True, text=True, check=True)

        # Create a new bundle with a corrupted program file hash in manifest
        corrupted_bundle = temp_dir / "corrupted_hash.dvcf"
        with zipfile.ZipFile(corrupted_bundle, 'w') as zf:
            # Read original manifest, modify program hash, then write
            with zipfile.ZipFile(output_bundle, 'r') as original_zf:
                manifest_content = json.loads(original_zf.read("manifest.json"))
            
            manifest_content["program"]["sha256"] = "a" * 64 # Corrupt hash
            zf.writestr("manifest.json", json.dumps(manifest_content))
            
            # Copy other files from original bundle
            for item in ["assets/test_image.png", "assets/test_palette.json", "build/test_program.json", "trace/test_trace.json"]:
                zf.writestr(item, original_zf.read(item))

        verify_cmd = CLI_PATH + [
            "verify",
            "--bundle", str(corrupted_bundle),
            "--format", "json"
        ]
        result = subprocess.run(verify_cmd, capture_output=True, text=True, check=False) # check=False for expected failure

        assert result.returncode == 1 # Expecting failure
        summary = json.loads(result.stdout)
        assert summary["status"] == "error"
        assert "SHA256 mismatch" in summary["error"]

    def test_pack_determinism(self, dummy_files, temp_dir):
        output_bundle_1 = temp_dir / "output_1.dvcf"
        output_bundle_2 = temp_dir / "output_2.dvcf"

        # Pack first bundle
        cmd_1 = CLI_PATH + [
            "pack",
            "--image", str(dummy_files["image"]),
            "--palette", str(dummy_files["palette"]),
            "--program", str(dummy_files["program"]),
            "--trace", str(dummy_files["trace"]),
            "--out", str(output_bundle_1),
            "--format", "json"
        ]
        subprocess.run(cmd_1, capture_output=True, text=True, check=True)

        # Pack second bundle (should be identical)
        cmd_2 = CLI_PATH + [
            "pack",
            "--image", str(dummy_files["image"]),
            "--palette", str(dummy_files["palette"]),
            "--program", str(dummy_files["program"]),
            "--trace", str(dummy_files["trace"]),
            "--out", str(output_bundle_2),
            "--format", "json"
        ]
        subprocess.run(cmd_2, capture_output=True, text=True, check=True)

        # Compare bundle bytes
        bundle_bytes_1 = output_bundle_1.read_bytes()
        bundle_bytes_2 = output_bundle_2.read_bytes()

        assert bundle_bytes_1 == bundle_bytes_2

