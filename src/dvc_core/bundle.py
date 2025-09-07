import zipfile
import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class DVCBundleError(Exception):
    """Custom exception for DVC bundle operations."""
    pass

class DVCBundle:
    def __init__(self, bundle_path: Path):
        self.bundle_path = bundle_path
        self.manifest: Dict[str, Any] = {}

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """Calculates the SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _normalize_zip_info(zip_info: zipfile.ZipInfo):
        """Normalizes ZipInfo attributes for deterministic zipping."""
        zip_info.date_time = (1980, 1, 1, 0, 0, 0)  # Normalize timestamp
        zip_info.create_system = 3  # Unix
        zip_info.external_attr = 0o644 << 16  # rw-r--r--
        # zip_info.compress_type = zipfile.ZIP_STORED # No compression for determinism

    def pack(self, 
             image_path: Path, 
             palette_path: Path, 
             program_path: Path, 
             trace_path: Path, 
             output_bundle_path: Path,
             deterministic_meta: bool = False) -> Dict[str, Any]:
        """Packs DVC assets into a deterministic .dvcf bundle."""
        self.bundle_path = output_bundle_path
        
        if self.bundle_path.exists():
            raise DVCBundleError(f"Output bundle already exists: {self.bundle_path}")

        # Create manifest data
        manifest_data = {
            "version": "dvcf-v0.1",
            "created_at": datetime.now().isoformat(),
            "tool": "dvc-cli",
            "tool_version": "0.1", # Placeholder
            "program": {
                "path": str(Path("build") / program_path.name),
                "sha256": self._calculate_sha256(program_path)
            },
            "trace": {
                "path": str(Path("trace") / trace_path.name),
                "sha256": self._calculate_sha256(trace_path),
                "final_root": "" # Will be populated from trace.json
            },
            "assets": [
                {
                    "path": str(Path("assets") / image_path.name),
                    "sha256": self._calculate_sha256(image_path)
                },
                {
                    "path": str(Path("assets") / palette_path.name),
                    "sha256": self._calculate_sha256(palette_path)
                }
            ],
            "provenance": {},
            "meta": {}
        }

        # Populate final_root from trace.json
        try:
            with open(trace_path, 'r') as f:
                trace_content = json.load(f)
            manifest_data["trace"]["final_root"] = trace_content.get("meta", {}).get("final_root", "")
            
            # Populate provenance from trace.json if available
            if "color_provenance" in trace_content.get("meta", {}):
                manifest_data["provenance"] = trace_content["meta"]["color_provenance"]

        except json.JSONDecodeError as e:
            raise DVCBundleError(f"Invalid JSON in trace file {trace_path}: {e}")
        except FileNotFoundError:
            raise DVCBundleError(f"Trace file not found: {trace_path}")

        # Write manifest.json to a temporary location
        temp_manifest_path = self.bundle_path.parent / "manifest.json.tmp"
        with open(temp_manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        manifest_data_sha256 = self._calculate_sha256(temp_manifest_path)
        manifest_data["sha256"] = manifest_data_sha256 # Add manifest hash to manifest itself
        
        # Re-write manifest with its own hash included
        with open(temp_manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)

        # Create the ZIP archive
        with zipfile.ZipFile(self.bundle_path, 'w', zipfile.ZIP_STORED) as zf:
            # Add manifest.json
            manifest_arcname = "manifest.json"
            manifest_info = zipfile.ZipInfo(manifest_arcname)
            self._normalize_zip_info(manifest_info)
            with open(temp_manifest_path, 'rb') as f:
                zf.writestr(manifest_info, f.read())

            # Add assets
            asset_files = [
                (image_path, Path("assets") / image_path.name),
                (palette_path, Path("assets") / palette_path.name)
            ]
            for src_path, arc_path in asset_files:
                info = zipfile.ZipInfo(str(arc_path))
                self._normalize_zip_info(info)
                with open(src_path, 'rb') as f:
                    zf.writestr(info, f.read())

            # Add program.json
            program_arcname = Path("build") / program_path.name
            program_info = zipfile.ZipInfo(str(program_arcname))
            self._normalize_zip_info(program_info)
            with open(program_path, 'rb') as f:
                zf.writestr(program_info, f.read())

            # Add trace.json
            trace_arcname = Path("trace") / trace_path.name
            trace_info = zipfile.ZipInfo(str(trace_arcname))
            self._normalize_zip_info(trace_info)
            with open(trace_path, 'rb') as f:
                zf.writestr(trace_info, f.read())

        # Clean up temporary manifest file
        os.remove(temp_manifest_path)

        return manifest_data

    def unpack(self, output_dir: Path):
        """Unpacks a .dvcf bundle to the specified directory."""
        if not self.bundle_path.exists():
            raise DVCBundleError(f"Bundle file not found: {self.bundle_path}")
        
        with zipfile.ZipFile(self.bundle_path, 'r') as zf:
            zf.extractall(output_dir)

    def verify(self) -> Dict[str, Any]:
        """Verifies the integrity and contents of a .dvcf bundle."""
        if not self.bundle_path.exists():
            raise DVCBundleError(f"Bundle file not found: {self.bundle_path}")

        with zipfile.ZipFile(self.bundle_path, 'r') as zf:
            # Read manifest
            try:
                with zf.open("manifest.json", 'r') as f:
                    manifest_content = f.read()
                    manifest = json.loads(manifest_content)
            except KeyError:
                raise DVCBundleError("Bundle is missing manifest.json")
            except json.JSONDecodeError as e:
                raise DVCBundleError(f"Invalid JSON in manifest.json: {e}")

            # Verify manifest's own hash (if present)
            if "sha256" in manifest:
                calculated_manifest_hash = hashlib.sha256(manifest_content).hexdigest()
                if calculated_manifest_hash != manifest["sha256"]:
                    raise DVCBundleError("Manifest SHA256 hash mismatch")

            # Verify program file
            program_info = manifest.get("program")
            if not program_info:
                raise DVCBundleError("Manifest is missing program information")
            
            try:
                with zf.open(program_info["path"], 'r') as f:
                    program_content = f.read()
                    if hashlib.sha256(program_content).hexdigest() != program_info["sha256"]:
                        raise DVCBundleError(f"Program file SHA256 mismatch: {program_info['path']}")
            except KeyError:
                raise DVCBundleError(f"Program file not found in bundle: {program_info['path']}")

            # Verify trace file
            trace_info = manifest.get("trace")
            if not trace_info:
                raise DVCBundleError("Manifest is missing trace information")
            
            try:
                with zf.open(trace_info["path"], 'r') as f:
                    trace_content = f.read()
                    if hashlib.sha256(trace_content).hexdigest() != trace_info["sha256"]:
                        raise DVCBundleError(f"Trace file SHA256 mismatch: {trace_info['path']}")
                    
                    # Verify final_root from trace.json against manifest
                    loaded_trace = json.loads(trace_content)
                    if loaded_trace.get("meta", {}).get("final_root") != trace_info["final_root"]:
                        raise DVCBundleError("Trace final_root mismatch with manifest")

            except KeyError:
                raise DVCBundleError(f"Trace file not found in bundle: {trace_info['path']}")
            except json.JSONDecodeError as e:
                raise DVCBundleError(f"Invalid JSON in trace file {trace_info['path']}: {e}")

            # Verify asset files
            assets_info = manifest.get("assets", [])
            for asset in assets_info:
                try:
                    with zf.open(asset["path"], 'r') as f:
                        asset_content = f.read()
                        if hashlib.sha256(asset_content).hexdigest() != asset["sha256"]:
                            raise DVCBundleError(f"Asset file SHA256 mismatch: {asset['path']}")
                except KeyError:
                    raise DVCBundleError(f"Asset file not found in bundle: {asset['path']}")

            # TODO: Add more comprehensive verification for provenance and meta

        return {"status": "valid", "message": "Bundle integrity verified successfully."}