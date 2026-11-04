"""Settings for the FinStack AI backend, loaded from environment."""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    demo: bool = False
    aws_region: str = "us-east-1"
    aws_profile: str = ""
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"
    bedrock_guardrail_id: str = ""
    s3_bucket: str = ""
    opensearch_collection: str = ""
    opensearch_index: str = "filings"
    chat_history_table: str = ""
    filing_meta_table: str = ""
    langchain_api_key: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    sec_user_agent: str = "finstack-ai research contact@example.com"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            demo=os.getenv("DEMO", "0") == "1",
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_profile=os.getenv("AWS_PROFILE", ""),
            bedrock_model_id=os.getenv(
                "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
            ),
            bedrock_embed_model_id=os.getenv(
                "BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"
            ),
            bedrock_guardrail_id=os.getenv("BEDROCK_GUARDRAIL_ID", ""),
            s3_bucket=os.getenv("S3_BUCKET", ""),
            opensearch_collection=os.getenv("OPENSEARCH_COLLECTION", ""),
            opensearch_index=os.getenv("OPENSEARCH_INDEX", "filings"),
            chat_history_table=os.getenv("CHAT_HISTORY_TABLE", ""),
            filing_meta_table=os.getenv("FILING_META_TABLE", ""),
            langchain_api_key=os.getenv("LANGCHAIN_API_KEY", ""),
            langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            sec_user_agent=os.getenv(
                "SEC_USER_AGENT", "finstack-ai research contact@example.com"
            ),
        )


def boto_session(settings: Settings):
    """boto3 session honoring AWS_PROFILE/AWS_REGION (real AWS path only)."""
    import boto3

    if settings.aws_profile:
        return boto3.Session(
            profile_name=settings.aws_profile, region_name=settings.aws_region
        )
    return boto3.Session(region_name=settings.aws_region)
