import json
import argparse
import time
import os
import config

print("Starting main.py...")

from src.models import Article
from src.vector_store import VectorStore
from src.pipeline import Pipeline
from src.llm_service import MockLLMService

def process_file(input_file: str, output_file: str, max_articles: int = None, use_mock: bool = False):
    print("--- Initializing Pipeline ---")
    min_entities_per_article = getattr(config, "MIN_ENTITIES_PER_ARTICLE", 5)
    max_entities_per_article = getattr(config, "MAX_ENTITIES_PER_ARTICLE", 10)
    candidate_top_k = getattr(config, "ENTITY_CANDIDATE_TOP_K", 3)
    distance_threshold = getattr(config, "ENTITY_DISTANCE_THRESHOLD", 1.2)
    min_article_content_length = getattr(config, "MIN_ARTICLE_CONTENT_LENGTH", 100)

    if not use_mock:
        api_key = os.environ.get("API_KEY")
        if not api_key:
            api_key = getattr(config, "API_KEY", None)

        if not api_key:
            print("[Error] No API key provided. Please set API_KEY env var, or configure it in config.py.")
            return

        try:
            from src.llm_service import LLMService
            llm = LLMService(
                api_key=api_key,
                base_url=getattr(config, "LLM_BASE_URL", None),
                model_name=getattr(config, "MODEL_NAME", None),
                min_entities=min_entities_per_article,
                max_entities=max_entities_per_article
            )
            print("Using REAL LLM Service.")
        except ImportError as e:
            print(f"[Warning] Failed to import LLMService: {e}. Falling back to MockLLMService.")
            from src.llm_service import MockLLMService
            llm = MockLLMService(min_entities=min_entities_per_article, max_entities=max_entities_per_article)
        except Exception as e:
            print(f"[Error] Failed to initialize real LLM service: {e}")
            import traceback
            traceback.print_exc()
            return
    else:
        from src.llm_service import MockLLMService
        llm = MockLLMService(min_entities=min_entities_per_article, max_entities=max_entities_per_article)
        print("Using MOCK LLM Service.")

    vector_store = VectorStore(
        persist_directory=getattr(config, "CHROMA_PERSIST_DIR", "data/chroma_db"), 
        collection_name=getattr(config, "CHROMA_COLLECTION_NAME", "pipeline_entities")
    )
    pipeline = Pipeline(
        llm_service=llm,
        vector_store=vector_store,
        candidate_top_k=candidate_top_k,
        distance_threshold=distance_threshold,
        min_entities_per_article=min_entities_per_article,
        max_entities_per_article=max_entities_per_article
    )

    print(f"\n--- Loading Articles from {input_file} ---")
    if not os.path.exists(input_file):
        print(f"[Error] Input file not found: {input_file}")
        return

    articles = []
    with open(input_file, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if max_articles is not None and i >= max_articles:
                break
            try:
                data = json.loads(line)
                title = data.get("title", "").strip()
                content = data.get("content", "").strip()
                
                if not title or not content or len(content) < min_article_content_length:
                    print(f"[Warning] Skipping line {i+1} due to missing or extremely short title/content (<{min_article_content_length} chars).")
                    continue
                    
                articles.append(Article(
                    id=data.get("id", f"article_{i+1:03d}"),
                    title=title,
                    content=content
                ))
            except json.JSONDecodeError:
                print(f"[Warning] Failed to parse line {i+1} as JSON. Skipping.")
                continue

    print(f"Loaded {len(articles)} articles.")

    print("\n--- Running Pipeline ---")
    results = []
    start_time = time.time()
    
    for i, article in enumerate(articles):
        print(f"\n[{i+1}/{len(articles)}] Processing Article: {article.title}")
        try:
            result = pipeline.process_article(article)
            if result:
                results.append(result)
        except Exception as e:
            print(f"[Error] Pipeline failed fatally on article '{article.title}': {e}")
            continue

    end_time = time.time()
    print(f"\n--- Pipeline Finished in {end_time - start_time:.2f}s ---")
    
    # Save results
    if output_file:
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            for res in results:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
        print(f"Saved results to {output_file}")
        
    print(f"Total unique entities in VectorStore: {vector_store.collection.count()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LLM Wikidata Pipeline")
    parser.add_argument("--input", type=str, default="data/articles_content.jsonl", help="Input JSONL file") 
    parser.add_argument("--output", type=str, default="data/pipeline_results.jsonl", help="Output JSONL file")
    parser.add_argument("--limit", type=int, default=None, help="Max number of articles to process")
    parser.add_argument("--mock", action="store_true", help="Use the mock LLM service instead of the real API")

    args = parser.parse_args()
    process_file(args.input, args.output, args.limit, args.mock)
