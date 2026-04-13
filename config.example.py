# Configuration file for LLM Service and Database

# Your Model API Key
API_KEY = "your_api_key_here"

# LLM Base URL (Compatible with OpenAI SDK)
LLM_BASE_URL = "https://api.openai.com/v1"

# Model selection
MODEL_NAME = "gpt-4o-mini"

# Entity extraction and linking
MIN_ENTITIES_PER_ARTICLE = 5
MAX_ENTITIES_PER_ARTICLE = 10
ENTITY_CANDIDATE_TOP_K = 3
ENTITY_DISTANCE_THRESHOLD = 1.2

# Input filtering
MIN_ARTICLE_CONTENT_LENGTH = 100

# Vector Database paths
CHROMA_PERSIST_DIR = "data/chroma_db"
CHROMA_COLLECTION_NAME = "pipeline_entities"
