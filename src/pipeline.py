import json
from typing import List, Dict, Any
from src.models import Article, Entity
from src.vector_store import VectorStore

class Pipeline:
    def __init__(self, llm_service, vector_store: VectorStore, candidate_top_k: int = 3, distance_threshold: float = 1.2, min_entities_per_article: int = 5, max_entities_per_article: int = 10):
        self.llm = llm_service
        self.vector_store = vector_store
        self.candidate_top_k = candidate_top_k
        self.distance_threshold = distance_threshold
        self.min_entities_per_article = min_entities_per_article
        self.max_entities_per_article = max_entities_per_article
        
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
        entity_details = []
        seen_entity_names = set()

        def is_valid_entity(name):
            if not name:
                return False
            name_lower = str(name).strip().lower()
            return name_lower not in ["", "null", "none", "n/a", "undefined"]

        def normalize_entity_name(name):
            return str(name).strip().lower()

        def append_entity(entity: Entity, entity_type: str):
            normalized_name = normalize_entity_name(entity.name)
            if normalized_name in seen_entity_names:
                return False

            if len(entity_details) >= self.max_entities_per_article:
                return False

            seen_entity_names.add(normalized_name)
            resolved_entities.append(entity)
            entity_details.append({"name": entity.name, "type": entity_type})
            return True
        
        # 2. Process each keyword
        for keyword in extraction.keywords:
            if len(entity_details) >= self.max_entities_per_article:
                print(f"[Pipeline] Reached max entity limit ({self.max_entities_per_article}) for article '{article.title}'.")
                break

            if not is_valid_entity(keyword):
                continue
                
            print(f"\n  -> Processing keyword: '{keyword}'")
            
            candidates = self.vector_store.search_similar(
                keyword,
                top_k=self.candidate_top_k,
                distance_threshold=self.distance_threshold
            )
            
            if not candidates:
                print("     [Branch A] No similar entities found. Treating as completely new.")
                new_entity = Entity(name=keyword, source_article_id=article.id)
                self.vector_store.add_entity(new_entity)
                append_entity(new_entity, "conservative")
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
                        append_entity(cons_entity, "conservative")
                    
                    granular = resolution.granular_entity
                    if is_valid_entity(granular) and len(entity_details) < self.max_entities_per_article:
                        gran_entity = Entity(name=granular, source_article_id=article.id)
                        self.vector_store.add_entity(gran_entity)
                        append_entity(gran_entity, "granular")
                except Exception as e:
                    print(f"     [Error] Entity resolution failed for keyword '{keyword}': {e}. Skipping to next keyword.")
                    continue

        if len(entity_details) < self.min_entities_per_article:
            print(f"[Pipeline] Article '{article.title}' produced {len(entity_details)} entities, below configured minimum {self.min_entities_per_article}.")

        # 3. Update Knowledge Graph
        self.knowledge_graph[article.id] = [e.id for e in resolved_entities]
        
        return {
            "article_id": article.id,
            "article_title": article.title,
            "summary": extraction.summary,
            "linked_entities": entity_details
        }
