import argparse
import json
import os
from src.vector_store import VectorStore
import config

def get_vector_store():
    persist_dir = getattr(config, "CHROMA_PERSIST_DIR", "data/chroma_db")
    collection_name = getattr(config, "CHROMA_COLLECTION_NAME", "pipeline_entities")
    return VectorStore(persist_directory=persist_dir, collection_name=collection_name)

def export_db(output_file):
    """Export all entities from ChromaDB to a JSONL file."""
    print(f"--- Exporting Database ---")
    vs = get_vector_store()
    
    # Retrieve all documents
    # ChromaDB's get() without where clause returns everything
    results = vs.collection.get()
    
    if not results or not results.get('ids'):
        print("Database is empty. Nothing to export.")
        return
        
    ids = results['ids']
    documents = results['documents']
    metadatas = results['metadatas']
    
    total = len(ids)
    print(f"Found {total} entities. Exporting to {output_file}...")
    
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for i in range(total):
            entity_data = {
                "id": ids[i],
                "name": documents[i],
                "metadata": metadatas[i] if metadatas else {}
            }
            f.write(json.dumps(entity_data, ensure_ascii=False) + "\n")
            
    print(f"Successfully exported {total} entities to {output_file}.")

def import_db(input_file):
    """Import entities from a JSONL file into ChromaDB."""
    print(f"--- Importing Database ---")
    if not os.path.exists(input_file):
        print(f"[Error] Input file {input_file} not found.")
        return
        
    vs = get_vector_store()
    
    ids = []
    documents = []
    metadatas = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            ids.append(data['id'])
            documents.append(data['name'])
            metadatas.append(data.get('metadata', {"name": data['name']}))
            
    if not ids:
        print("No entities found in the input file.")
        return
        
    print(f"Found {len(ids)} entities in {input_file}. Importing to ChromaDB...")
    
    # We do batch insertion to avoid memory issues with huge datasets
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        batch_docs = documents[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        
        vs.collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas
        )
        print(f"Imported batch {i//batch_size + 1} ({(min(i+batch_size, len(ids)))} / {len(ids)})")
        
    print(f"Successfully imported {len(ids)} entities.")
    print(f"Total entities currently in DB: {vs.collection.count()}")

def clear_db():
    """Clear all data in the ChromaDB collection."""
    print(f"--- Clearing Database ---")
    persist_dir = getattr(config, "CHROMA_PERSIST_DIR", "data/chroma_db")
    collection_name = getattr(config, "CHROMA_COLLECTION_NAME", "pipeline_entities")
    
    print(f"WARNING: This will permanently delete the collection '{collection_name}' in '{persist_dir}'.")
    confirm = input("Are you sure you want to proceed? (yes/y to confirm): ")
    
    if confirm.lower() in ['yes', 'y']:
        try:
            # We initialize just to get the client, then delete collection
            vs = get_vector_store()
            try:
                vs.client.delete_collection(collection_name)
                print(f"Collection '{collection_name}' deleted.")
            except Exception as e:
                print(f"Could not delete collection via API (might not exist): {e}")
            
            print("Database cleared successfully.")
        except Exception as e:
            print(f"Error while clearing DB: {e}")
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage the ChromaDB Entity Store")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export entities to a JSONL file")
    export_parser.add_argument("--file", type=str, default="data/db_export.jsonl", help="Output file path")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import entities from a JSONL file")
    import_parser.add_argument("--file", type=str, default="data/db_export.jsonl", help="Input file path")
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear all entities from the database")
    
    args = parser.parse_args()
    
    if args.command == "export":
        export_db(args.file)
    elif args.command == "import":
        import_db(args.file)
    elif args.command == "clear":
        clear_db()
    else:
        parser.print_help()