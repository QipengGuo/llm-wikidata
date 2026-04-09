import chromadb
from typing import List
from .models import Entity

class VectorStore:
    def __init__(self, persist_directory: str = "data/chroma_db", collection_name: str = "entities"):
        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create the collection
        # We don't specify an embedding_function here, so Chroma will automatically 
        # use the default sentence-transformers/all-MiniLM-L6-v2 function.
        self.collection = self.client.get_or_create_collection(name=collection_name)
        
    def add_entity(self, entity: Entity) -> None:
        """
        Add a new entity to the vector store.
        The entity.name will be used as the document to embed.
        """
        # Simple deduplication check based on name
        results = self.collection.get(where={"name": entity.name})
        if results and results["ids"]:
            print(f"[VectorStore] Entity '{entity.name}' already exists. Skipping insertion.")
            return

        self.collection.add(
            ids=[entity.id],
            documents=[entity.name],
            metadatas=[{"name": entity.name, "description": (entity.description or ""), "source_article_id": (entity.source_article_id or "")}]
        )
        print(f"[VectorStore] Added entity: '{entity.name}' (ID: {entity.id})")

    def search_similar(self, keyword: str, top_k: int = 5, distance_threshold: float = 1.5) -> List[Entity]:
        """
        Search for entities similar to the given keyword.
        Returns a list of Entity objects that are within the distance_threshold.
        """
        # If the collection is empty, return empty list
        if self.collection.count() == 0:
            return []
            
        results = self.collection.query(
            query_texts=[keyword],
            n_results=min(top_k, self.collection.count())
        )
        
        # ChromaDB query returns a dictionary with lists of lists
        # keys: 'ids', 'distances', 'metadatas', 'documents'
        
        entities = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            
            for i in range(len(ids)):
                # Chroma uses L2 distance by default (lower is more similar)
                if distances[i] <= distance_threshold:
                    entity = Entity(
                        id=ids[i],
                        name=documents[i],
                        description=metadatas[i].get("description", ""),
                        source_article_id=metadatas[i].get("source_article_id", "")
                    )
                    entities.append(entity)
                    
        return entities
