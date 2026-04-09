import json
from typing import List, Dict, Any
from src.models import Article, Entity
from src.vector_store import VectorStore

class Pipeline:
    def __init__(self, llm_service, vector_store: VectorStore):
        self.llm = llm_service
        self.vector_store = vector_store
        
        # In a real app, this might be a separate Graph DB (e.g. Neo4j)
        # Here we just keep a local dict to show relationships: article_id -> [entity_ids]
        self.knowledge_graph: Dict[str, List[str]] = {}

    def process_article(self, article: Article) -> Dict[str, Any]:
        print(f"\n========== Processing Article: {article.id} ==========")
        
        # 1. Extraction
        try:
            extraction = self.llm.extract_summary_and_keywords(article)
            print(f"Summary: {extraction.summary}")
            print(f"Extracted Keywords: {extraction.keywords}")
        except Exception as e:
            print(f"[Error] Failed to extract summary and keywords: {e}")
            return {
                "article_id": article.id,
                "summary": "Extraction Failed",
                "linked_entities": [],
                "error": str(e)
            }
        
        resolved_entities = []
        entity_details = [] # List of dicts to store entity metadata (name, type)

        def is_valid_entity(name):
            if not name:
                return False
            name_lower = str(name).strip().lower()
            return name_lower not in ["", "null", "none", "n/a", "undefined"]
        
        # 2. Process each keyword
        for keyword in extraction.keywords:
            if not is_valid_entity(keyword):
                continue
                
            print(f"\n  -> Processing keyword: '{keyword}'")
            
            # Search similar in VectorStore
            # Using a threshold of 1.2 as a rough cutoff for Branch A vs B
            candidates = self.vector_store.search_similar(keyword, top_k=3, distance_threshold=1.2)
            
            if not candidates:
                print("     [Branch A] No similar entities found. Treating as completely new.")
                # Create a single new entity
                new_entity = Entity(name=keyword, source_article_id=article.id)
                self.vector_store.add_entity(new_entity)
                resolved_entities.append(new_entity)
                entity_details.append({"name": new_entity.name, "type": "conservative"})
            else:
                print(f"     [Branch B] Found {len(candidates)} candidates. Asking LLM to resolve...")
                for c in candidates:
                    print(f"       - Candidate: {c.name}")
                    
                try:
                    resolution = self.llm.resolve_entities(keyword, candidates)
                    print(f"     [Resolution] Conservative: '{resolution.conservative_entity}', Granular: '{resolution.granular_entity}'")
                    
                    # Process conservative entity
                    if is_valid_entity(resolution.conservative_entity):
                        cons_entity = next((c for c in candidates if c.name.lower() == resolution.conservative_entity.lower()), None)
                        if not cons_entity:
                            cons_entity = Entity(name=resolution.conservative_entity, source_article_id=article.id)
                            self.vector_store.add_entity(cons_entity)
                        resolved_entities.append(cons_entity)
                        entity_details.append({"name": cons_entity.name, "type": "conservative"})
                    
                    # Process granular entity
                    granular = resolution.granular_entity
                    if is_valid_entity(granular):
                        gran_entity = Entity(name=granular, source_article_id=article.id)
                        self.vector_store.add_entity(gran_entity)
                        resolved_entities.append(gran_entity)
                        entity_details.append({"name": gran_entity.name, "type": "granular"})
                except Exception as e:
                    print(f"     [Error] Entity resolution failed for keyword '{keyword}': {e}. Skipping to next keyword.")
                    continue

        # 3. Update Knowledge Graph
        self.knowledge_graph[article.id] = [e.id for e in resolved_entities]
        
        return {
            "article_id": article.id,
            "article_title": article.title,
            "summary": extraction.summary,
            "linked_entities": entity_details
        }
