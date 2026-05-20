"""
Chunk clean texts, embed locally with sentence-transformers,
and upsert to Supabase. No API rate limits.

Model: all-mpnet-base-v2 → 768-dim vectors (matches Supabase vector(768))
"""
import os
import glob
import time
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

load_dotenv(os.path.join(PROJECT_DIR, ".env.local"))

SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

CHUNK_SIZE    = 2500
CHUNK_OVERLAP = 300
BATCH_SIZE    = 50   # larger batches are fine with local model

print("Loading embedding model (all-mpnet-base-v2, 768 dims)...")
model = SentenceTransformer("all-mpnet-base-v2")
print("Model loaded.\n")


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            nl = text.rfind("\n", max(start, end - 200), end)
            if nl != -1:
                end = nl + 1
            else:
                dot = text.rfind(". ", max(start, end - 200), end)
                if dot != -1:
                    end = dot + 2
        chunk = text[start:end].strip()
        if len(chunk) >= 50:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def ingest_file(filepath: str, source_name: str, character_id: str):
    print(f"\n{'='*60}")
    print(f"Processing: {source_name} (Character: {character_id})")
    print(f"{'='*60}")

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)
    total  = len(chunks)
    print(f"  Chunks: {total}")

    inserted = 0
    errors   = 0

    # Process in batches — encode the whole batch at once (fast on CPU/GPU)
    for batch_start in range(0, total, BATCH_SIZE):
        batch_chunks = chunks[batch_start : batch_start + BATCH_SIZE]

        try:
            # encode returns numpy array; convert to list[list[float]]
            embeddings = model.encode(
                batch_chunks,
                batch_size=BATCH_SIZE,
                show_progress_bar=False,
                normalize_embeddings=True,
            ).tolist()

            records = [
                {
                    "content":      chunk,
                    "source":       source_name,
                    "embedding":    emb,
                    "character_id": character_id,
                }
                for chunk, emb in zip(batch_chunks, embeddings)
            ]

            supabase.table("osho_corpus").insert(records).execute()
            inserted += len(records)
            print(f"  Inserted {inserted}/{total} chunks...")

        except Exception as e:
            print(f"  [ERROR] batch {batch_start}: {e}")
            errors += len(batch_chunks)

    print(f"  Done: {inserted} inserted, {errors} errors.")


def clear_table(character_id: str):
    """Delete all existing rows for this character so we start fresh."""
    print(f"Clearing existing corpus rows for character '{character_id}'...")
    supabase.table("osho_corpus").delete().eq("character_id", character_id).execute()
    print("Table cleared.\n")


def main():
    parser = argparse.ArgumentParser(description="Embed text and upload to Supabase.")
    parser.add_argument("--character", type=str, default="osho", help="The character ID (e.g. osho, ssr, tesla).")
    parser.add_argument("--dir", type=str, default="texts", help="Subdirectory inside 'corpus/' containing the .txt files.")
    parser.add_argument("--clear", action="store_true", help="Clear existing vectors for this character before inserting.")
    args = parser.parse_args()

    text_dir = os.path.join(PROJECT_DIR, "corpus", args.dir)
    txt_files = sorted(glob.glob(os.path.join(text_dir, "*.txt")))
    
    if not txt_files:
        print(f"No .txt files found in {text_dir}")
        return

    if args.clear:
        clear_table(args.character)

    print(f"Found {len(txt_files)} text files to ingest for {args.character}.")
    for filepath in txt_files:
        basename    = os.path.basename(filepath).replace(".txt", "")
        source_name = basename.replace("_", " ").title()
        ingest_file(filepath, source_name, args.character)

    print("\nAll files ingested!")


if __name__ == "__main__":
    main()
