from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    llm_model: str = "gpt-4o-mini"
    top_k_seed_nodes: int = 5
    traversal_depth: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
