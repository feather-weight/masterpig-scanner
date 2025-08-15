from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    tatum_api_key: str | None = os.getenv("TATUM_API_KEY")
    infura_project_id: str | None = os.getenv("INFURA_PROJECT_ID")
    mongo_uri: str | None = os.getenv("MONGO_URI")
    mongo_db: str = os.getenv("MONGO_DB", "MasterPig")
    blockchair_key: str | None = os.getenv("BLOCKCHAIR_KEY")  # optional
    user_agent: str = "MasterPigScanner/1.0"

settings = Settings()
