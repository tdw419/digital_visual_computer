#!/usr/bin/env python3
# scripts/pxrom_cam_decode.py
# Read PxROM frames from a live screen using a webcam and reconstruct the payload.
# Assumptions:
#  - The screen shows exact PxROM PNGs full-screen (no scaling/filters).
#  - The camera is roughly aligned; small misalignment tolerated by center sampling.
# Controls:
#  SPACE or ENTER: capture current frame
#  A: auto-capture every N ms (toggle)   (default off)
#  Q or ESC: quit (write what we have so far)
#
# Example:
#   python3 scripts/pxrom_cam_decode.py --out artifacts/tinycore_cam.iso \
#       --tiles 128x72 --tile-size 8 --camera 0 --interval-ms 500
import argparse, time, zlib, sys, hashlib
from pathlib import Path

try:
    import cv2  # type: ignore
except Exception:
    print("This tool requires OpenCV (pip install opencv-python).", file=sys.stderr)
    raise

from PIL import Image
import numpy as np

# Reuse parser from pxrom
# Ensure scripts is on path if run from repo root
sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
import pxrom  # noqa: E402

def sample_grid_center(img_bgr, tiles_x, tiles_y):
    h, w = img_bgr.shape[:2]
    # derive tile size from image extents
    tile_w = w // tiles_x
    tile_h = h // tiles_y
    # center sampling
    out = bytearray()
    for ty in range(tiles_y):
        cy = ty * tile_h + tile_h // 2
        for tx in range(tiles_x):
            cx = tx * tile_w + tile_w // 2
            b, g, r = img_bgr[cy, cx]  # OpenCV is BGR
            out.extend((r, g, b))
    return bytes(out), tile_w, tile_h

def try_decode_frame(img_bgr, tiles_x, tiles_y):
    raw, tile_w, tile_h = sample_grid_center(img_bgr, tiles_x, tiles_y)
    try:
        hdr = pxrom._unpack_header(raw[:pxrom.HEADER_LEN])
        payload = raw[pxrom.HEADER_LEN:pxrom.HEADER_LEN + hdr["payload_len"]]
        if (zlib.crc32(payload) & 0xFFFFFFFF) != hdr["payload_crc32"]:
            return None
        return hdr, payload, (tile_w, tile_h)
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tiles", required=True, help="WxH, e.g., 128x72")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--interval-ms", type=int, default=750)
    ap.add_argument("--show", action="store_true", help="Show live view window")
    args = ap.parse_args()
    tiles_x, tiles_y = map(int, args.tiles.lower().split("x"))

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise SystemExit("Cannot open camera")

    captured = {}
    expected_total = None
    auto = False
    last = 0.0

    win = "PxROM Cam"
    if args.show:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    print("[cam] Controls: SPACE/ENTER capture | A auto toggle | Q/ESC quit")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[cam] frame read failed")
            break

        now = time.time()
        if args.show:
            cv2.imshow(win, frame)

        key = cv2.waitKey(1) & 0xFF  # non-blocking
        capture = False
        if key in (13, 32):  # enter or space
            capture = True
        elif key in (ord('a'), ord('A')):
            auto = not auto
            print(f"[cam] auto={auto}")
        elif key in (ord('q'), 27):  # q or esc
            break

        if auto and (now - last) * 1000.0 >= args.interval_ms:
            capture = True

        if capture:
            last = now
            # Optional: crop slight borders if needed; here we sample full frame
            res = try_decode_frame(frame, tiles_x, tiles_y)
            if res is None:
                print("[cam] capture failed CRC/header; adjust alignment/lighting")
            else:
                hdr, payload, (tw, th) = res
                if expected_total is None:
                    expected_total = hdr["total_frames"]
                    print(f"[cam] total_frames={expected_total}, tile={tw}x{th} px")
                captured[hdr["frame_idx"]] = payload
                print(f"[cam] got frame {hdr['frame_idx']}/{expected_total-1}  (collected {len(captured)})")
                if expected_total is not None and len(captured) >= expected_total:
                    print("[cam] all frames collected")
                    break

    cap.release()
    if args.show:
        cv2.destroyAllWindows()

    # Write out in index order
    if not captured:
        print("[cam] no frames captured; exiting")
        return
    total = expected_total if expected_total is not None else (max(captured.keys()) + 1)
    out = bytearray()
    missing = [i for i in range(total) if i not in captured]
    if missing:
        print(f"[cam] WARNING missing frames: {missing[:10]}{'...' if len(missing)>10 else ''}")
        # still write what we have in order up to the last contiguous index
        last_contig = -1
        for i in range(total):
            if i in captured:
                out.extend(captured[i])
                last_contig = i
            else:
                break
        print(f"[cam] wrote contiguous up to frame {last_contig}")
    else:
        for i in range(total):
            out.extend(captured[i])

    out_path = Path(args.out)
    out_path.write_bytes(bytes(out))
    sha = hashlib.sha256(bytes(out)).hexdigest()
    print(f"[cam] wrote {out_path} ({len(out)/1_048_576:.2f} MiB), sha256={sha}")

if __name__ == "__main__":
    main()
