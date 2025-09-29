#!/usr/bin/env python3
# pixel_corpus.py — Build + query a PNG-based "vector DB"
# v0: docs.pxb.png (bytes), vecs.pxv.png (float32), idx.pxi.png (fixed index)

import os, re, math, json, struct, argparse, glob
import sqlite3
from pathlib import Path
from typing import List, Tuple
import numpy as np
from PIL import Image

# ------------------------------
# Tiny, local embedding (replace later if you want)
# ------------------------------
def tiny_embed(text: str, dim: int = 256, seed: int = 1337) -> np.ndarray:
    """Hash-based bag-of-ngrams -> fixed dim vector. Offline, deterministic."""
    rng = np.random.RandomState(seed)
    proj = rng.normal(0, 1/ math.sqrt(dim), size=(65536, dim)).astype(np.float32)
    vec = np.zeros((dim,), dtype=np.float32)
    # crude normalization
    text = re.sub(r"\s+", " ", text.strip().lower())
    # 3-gram hashes
    for i in range(len(text)-2):
        h = hash(text[i:i+3]) & 0xFFFF
        vec += proj[h]
    n = np.linalg.norm(vec) + 1e-8
    return vec / n

# ------------------------------
# PNG writers/readers
# ------------------------------
def write_pxv(vecs: np.ndarray, path: Path):
    """vecs: [N, dim] float32; 1 pixel = 1 float32 (RGBA bytes)."""
    N, dim = vecs.shape
    W, H = dim, N
    im = Image.new("RGBA", (W, H))
    px = im.load()
    for y in range(H):
        row = vecs[y].astype(np.float32)
        raw = row.view(np.uint8).reshape(dim, 4)  # little-endian float32 bytes
        for x in range(W):
            r,g,b,a = raw[x]
            px[x, y] = (int(r), int(g), int(b), int(a))
    im.info["PXV1"] = json.dumps({"n": int(N), "dim": int(dim)})
    im.save(path, optimize=False)

def load_pxv(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    data = np.frombuffer(im.tobytes(), dtype=np.uint8).reshape(H, W, 4)
    vecs = data.view(np.float32).reshape(H, W)
    return vecs.copy()  # [N, dim]

def write_pxb(byte_stream: bytes, path: Path, width: int = 1024):
    """Pack 3 bytes per pixel into RGB."""
    total = len(byte_stream)
    pix = math.ceil(total / 3)
    W = width
    H = math.ceil(pix / W)
    im = Image.new("RGB", (W, H))
    px = im.load()
    i = 0
    for p in range(pix):
        r = byte_stream[i] if i < total else 0; i+=1
        g = byte_stream[i] if i < total else 0; i+=1
        b = byte_stream[i] if i < total else 0; i+=1
        x, y = p % W, p // W
        px[x, y] = (r, g, b)
    im.info["PXB1"] = json.dumps({"bytes": total, "width": W})
    im.save(path, optimize=False)

def read_range_from_pxb(path: Path, offset: int, length: int) -> bytes:
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    start_pix = offset // 3
    start_mod = offset % 3
    out = bytearray()
    p = start_pix
    while len(out) < length:
        x, y = p % W, p // W
        if y >= H:
            break
        r, g, b = px[x, y]
        for byte in (r, g, b):
            if len(out) >= length:
                break
            if start_mod > 0:
                start_mod -= 1
                continue
            out.append(byte)
        p += 1
    return bytes(out)

def write_pxi(records: List[Tuple[int,int,int,int,int]], path: Path):
    """Each record: (doc_id:u32, byte_offset:u32, byte_len:u32, flags:u16, title_off:u16).
       16 bytes -> 4 RGBA pixels."""
    N = len(records)
    W, H = 4, N
    im = Image.new("RGBA", (W, H))
    px = im.load()
    for y, rec in enumerate(records):
        doc_id, off, lng, flags, title_off = rec
        data = struct.pack("<IIIHH", doc_id, off, lng, flags, title_off)
        for x in range(4):
            r,g,b,a = data[4*x:4*x+4]
            px[x, y] = (r, g, b, a)
    im.info["PXI1"] = json.dumps({"n": N})
    im.save(path, optimize=False)

def load_pxi(path: Path) -> List[Tuple[int,int,int,int,int]]:
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    px = im.load()
    recs = []
    for y in range(H):
        raw = bytearray(16)
        for x in range(4):
            r,g,b,a = px[x, y]
            raw[4*x:4*x+4] = bytes([r,g,b,a])
        recs.append(struct.unpack("<IIIHH", raw))
    return recs

# ------------------------------
# Corpus building / querying
# ------------------------------
def chunk_text(s: str, target_chars=1000) -> List[str]:
    s = s.replace("\r\n", "\n")
    out, cur = [], []
    count = 0
    for para in s.split("\n\n"):
        if count + len(para) > target_chars and count > 0:
            out.append("\n\n".join(cur))
            cur, count = [], 0
        cur.append(para)
        count += len(para) + 2
    if cur:
        out.append("\n\n".join(cur))
    # ensure non-empty, trimmed chunks
    return [c.strip() for c in out if c.strip()]

def read_text_file(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def build_corpus(in_dir: Path, out_dir: Path, dim: int = 256, chunk_chars: int = 1000, pxb_width: int = 1024):
    out_dir.mkdir(parents=True, exist_ok=True)
    # Gather docs
    files = sorted([*in_dir.glob("**/*.txt"), *in_dir.glob("**/*.md")])
    if not files:
        raise SystemExit("No .txt/.md files found.")
    doc_map = []
    chunks = []
    vecs = []

    byte_stream = bytearray()
    records = []  # (doc_id, offset, length, flags, title_off)
    doc_id = 0
    for f in files:
        text = read_text_file(f)
        if not text.strip():
            continue
        doc_map.append({"doc_id": doc_id, "path": str(f)})
        parts = chunk_text(text, target_chars=chunk_chars)
        for part in parts:
            b = part.encode("utf-8")
            off = len(byte_stream)
            byte_stream += b
            records.append((doc_id, off, len(b), 0, 0))
            vecs.append(tiny_embed(part, dim=dim))
        doc_id += 1

    if not records:
        raise SystemExit("No chunks produced.")

    vecs_np = np.stack(vecs, axis=0).astype(np.float32)
    write_pxv(vecs_np, out_dir / "vecs.pxv.png")
    write_pxb(bytes(byte_stream), out_dir / "docs.pxb.png", width=pxb_width)
    write_pxi(records, out_dir / "idx.pxi.png")
    # also write a tiny manifest (optional; convenience)
    (out_dir / "manifest.json").write_text(json.dumps({"docs": doc_map}, indent=2), encoding="utf-8")
    print(f"Built corpus: {len(records)} chunks from {len(doc_map)} docs → {out_dir}")

def cosine(a: np.ndarray, B: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    B = B.astype(np.float32)
    denom = (np.linalg.norm(a) * np.linalg.norm(B, axis=1) + 1e-8)
    return (B @ a) / denom

def query_corpus(corpus_dir: Path, question: str, top_k: int = 5):
    vecs = load_pxv(corpus_dir / "vecs.pxv.png")  # [N, dim]
    q = tiny_embed(question, dim=vecs.shape[1])
    scores = cosine(q, vecs)
    top_idx = np.argsort(-scores)[:top_k]
    recs = load_pxi(corpus_dir / "idx.pxi.png")
    results = []
    docs_png = corpus_dir / "docs.pxb.png"
    manifest = {}
    man_path = corpus_dir / "manifest.json"
    if man_path.exists():
        manifest = {d["doc_id"]: d for d in json.loads(man_path.read_text(encoding="utf-8")).get("docs", [])}

    for i in top_idx:
        doc_id, off, lng, flags, t_off = recs[int(i)]
        text = read_range_from_pxb(docs_png, off, lng).decode("utf-8", errors="ignore")
        meta = manifest.get(doc_id, {"path": f"(doc {doc_id})"})
        results.append({
            "rank": len(results)+1,
            "score": float(scores[int(i)]),
            "doc_id": int(doc_id),
            "path": meta.get("path"),
            "snippet": text[:400].replace("\n", " ") + ("…" if len(text) > 400 else "")
        })
    return results

def export_to_sqlite(corpus_dir: Path, out_file: Path):
    """Exports the pixel corpus data to a SQLite database."""
    print(f"Exporting pixel corpus from {corpus_dir} to {out_file}...")
    if out_file.exists():
        print(f"Output file {out_file} already exists. Deleting.")
        out_file.unlink()

    # Load all data from the pixel corpus
    manifest_path = corpus_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("manifest.json not found in corpus directory.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    docs = {d["doc_id"]: d for d in manifest.get("docs", [])}

    recs = load_pxi(corpus_dir / "idx.pxi.png")
    vecs = load_pxv(corpus_dir / "vecs.pxv.png")
    docs_png_path = corpus_dir / "docs.pxb.png"

    with sqlite3.connect(out_file) as con:
        cur = con.cursor()

        # Create tables
        cur.execute("""
            CREATE TABLE documents (
                doc_id INTEGER PRIMARY KEY,
                path TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE chunks (
                chunk_id INTEGER PRIMARY KEY,
                doc_id INTEGER,
                content TEXT,
                embedding BLOB,
                FOREIGN KEY (doc_id) REFERENCES documents (doc_id)
            )
        """)

        # Insert documents
        for doc_id, doc_info in docs.items():
            cur.execute("INSERT INTO documents (doc_id, path) VALUES (?, ?)", (doc_id, doc_info['path']))

        # Insert chunks
        for i, rec in enumerate(recs):
            doc_id, off, lng, _, _ = rec
            content = read_range_from_pxb(docs_png_path, off, lng).decode("utf-8", errors="ignore")
            embedding_blob = vecs[i].tobytes()

            cur.execute(
                "INSERT INTO chunks (chunk_id, doc_id, content, embedding) VALUES (?, ?, ?, ?)",
                (i, doc_id, content, embedding_blob)
            )

        con.commit()

    print(f"Successfully exported {len(docs)} documents and {len(recs)} chunks to {out_file}")


# ------------------------------
# CLI
# ------------------------------
def main():
    ap = argparse.ArgumentParser(description="Pixel Corpus (v0) — encode & query docs in PNGs")
    sub = ap.add_subparsers(dest="cmd", required=True)

    enc = sub.add_parser("encode", help="Build PNG corpus from a folder of .txt/.md")
    enc.add_argument("--in", dest="in_dir", required=True, help="Input folder")
    enc.add_argument("--out", dest="out_dir", required=True, help="Output folder")
    enc.add_argument("--dim", type=int, default=256, help="Embedding dim (default 256)")
    enc.add_argument("--chunk", type=int, default=1000, help="Chunk size in chars (default 1000)")
    enc.add_argument("--pxb-width", type=int, default=1024, help="Width for docs.pxb.png (default 1024)")

    qry = sub.add_parser("query", help="Query an existing PNG corpus")
    qry.add_argument("--corpus", required=True, help="Corpus folder (with the three PNGs)")
    qry.add_argument("-q", "--question", required=True, help="Your question / search text")
    qry.add_argument("-k", "--topk", type=int, default=5, help="Top-K results (default 5)")

    exp = sub.add_parser("export", help="Export corpus to a SQLite database")
    exp.add_argument("--corpus", required=True, help="Corpus folder to export from")
    exp.add_argument("--out", dest="out_file", required=True, help="Output SQLite file path")

    args = ap.parse_args()
    if args.cmd == "encode":
        build_corpus(Path(args.in_dir), Path(args.out_dir), dim=args.dim, chunk_chars=args.chunk, pxb_width=args.pxb_width)
    elif args.cmd == "query":
        results = query_corpus(Path(args.corpus), args.question, top_k=args.topk)
        for r in results:
            print(f"[{r['rank']}] score={r['score']:.4f} doc={r['doc_id']} path={r['path']}\n    {r['snippet']}\n")
    elif args.cmd == "export":
        export_to_sqlite(Path(args.corpus), Path(args.out_file))

if __name__ == "__main__":
    main()