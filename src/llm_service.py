import time
import json
from typing import List, Optional
from openai import OpenAI
from .models import Article, ExtractionResult, Entity, ResolutionResult

def retry_on_exception(max_retries=3, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"      [Warning] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay}s...")
                    last_exception = e
                    time.sleep(delay)
            raise Exception(f"Failed after {max_retries} attempts. Last error: {last_exception}")
        return wrapper
    return decorator

def normalize_keywords(keywords: List[str], max_entities: int) -> List[str]:
    normalized_keywords = []
    seen = set()

    for keyword in keywords or []:
        if keyword is None:
            continue

        normalized = str(keyword).strip()
        normalized_key = normalized.lower()

        if not normalized or normalized_key in {"null", "none", "n/a", "undefined"}:
            continue

        if normalized_key in seen:
            continue

        seen.add(normalized_key)
        normalized_keywords.append(normalized)

        if len(normalized_keywords) >= max_entities:
            break

    return normalized_keywords

class MockLLMService:
    """
    A mock service used for Phase 1-3 development to avoid hitting real API limits
    and ensure fast, controllable debugging.
    """
    
    def __init__(self, min_entities: int = 5, max_entities: int = 10):
        self.min_entities = min_entities
        self.max_entities = max_entities

    @retry_on_exception(max_retries=3, delay=1)
    def extract_summary_and_keywords(self, article: Article) -> ExtractionResult:
        print(f"[MockLLM] Extracting summary and keywords for article: '{article.title}'")
        
        # Hardcode some dummy responses based on keyword parsing
        if "Agent" in article.title:
            keywords = ["AI Agent", "硅谷初创公司", "自动化工具", "OpenClaw"]
        elif "模型" in article.title:
            keywords = ["大模型", "Meta", "Alexandr Wang", "Llama 4", "Muse Spark"]
        else:
            keywords = ["科技", "人工智能", "创新"]
            
        keywords = normalize_keywords(keywords, self.max_entities)

        return ExtractionResult(
            summary=f"This is a mock 1-sentence summary for the article '{article.title}'.",
            keywords=keywords
        )

    @retry_on_exception(max_retries=3, delay=1)
    def resolve_entities(self, keyword: str, candidates: List[Entity]) -> ResolutionResult:
        print(f"[MockLLM] Resolving keyword '{keyword}' against {len(candidates)} candidates")
        
        # Simple mock logic:
        # If there are candidates, we assume the first one is the "conservative" one.
        if candidates:
            conservative = candidates[0].name
            # Mock the optimization rule: If keyword is exactly the same, omit granular
            if keyword.lower() == conservative.lower():
                granular = None
            else:
                granular = f"{keyword} (具体)"
            
            return ResolutionResult(
                conservative_entity=conservative,
                granular_entity=granular
            )
        else:
            # This branch shouldn't ideally be hit if VectorStore handles Branch A properly
            # but we return something safe.
            return ResolutionResult(
                conservative_entity=keyword,
                granular_entity=None
            )

class LLMService:
    """
    A real LLM service using OpenAI API (or compatible APIs).
    """
    def __init__(self, api_key: str, base_url: Optional[str] = None, model_name: Optional[str] = None, min_entities: int = 5, max_entities: int = 10):
        base_url = base_url or "https://api.openai.com/v1"
        self.model_name = model_name or "gpt-4o-mini"
        self.min_entities = min_entities
        self.max_entities = max_entities
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    @retry_on_exception(max_retries=3, delay=2)
    def extract_summary_and_keywords(self, article: Article) -> ExtractionResult:
        print(f"[RealLLM] Extracting summary and keywords for article: '{article.title}'")
        
        prompt = f"""
Please analyze the following article and extract:
1. A 1-sentence summary of the article.
2. {self.min_entities} to {self.max_entities} key entities or concepts.

Prefer precision over padding. Return distinct items only. If the article is not information-dense, it is acceptable to return fewer than {self.min_entities}, but never return more than {self.max_entities}.

Respond strictly in JSON format matching this schema:
{{
    "summary": "Your 1-sentence summary here",
    "keywords": ["keyword1", "keyword2", "keyword3"]
}}

Article Title: {article.title}
Article Content: {article.content}
"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured information from text. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        extraction = ExtractionResult(**data)
        extraction.keywords = normalize_keywords(extraction.keywords, self.max_entities)
        return extraction

    @retry_on_exception(max_retries=3, delay=2)
    def resolve_entities(self, keyword: str, candidates: List[Entity]) -> ResolutionResult:
        print(f"[RealLLM] Resolving keyword '{keyword}' against {len(candidates)} candidates")
        
        candidate_names = [c.name for c in candidates]
        prompt = f"""
You are an expert ontology manager building a knowledge graph.
We have a new keyword: "{keyword}"
And we have found the following similar existing entities in our database:
{json.dumps(candidate_names, ensure_ascii=False)}

Your task is to merge or split this concept to avoid duplicate nodes while preserving useful details.
1. "conservative_entity": Choose the most stable, correct, and broad entity from the existing candidates that represents this concept. If none fit, use the keyword itself.
2. "granular_entity": Provide a specific, fine-grained entity that highlights the unique difference of the current keyword. If the keyword is identical or extremely similar to the conservative_entity, set this to null.

Respond strictly in JSON format matching this schema:
{{
    "conservative_entity": "Chosen broad entity",
    "granular_entity": "Specific entity or null"
}}
"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an expert ontology manager. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        return ResolutionResult(
            conservative_entity=data.get("conservative_entity", keyword),
            granular_entity=data.get("granular_entity")
        )
