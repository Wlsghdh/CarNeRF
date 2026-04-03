import os
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "carnerf-demo-secret-key-change-in-production")
if SECRET_KEY == "carnerf-demo-secret-key-change-in-production":
    logger.warning("SECRET_KEY가 기본값입니다. 프로덕션에서는 반드시 환경변수로 설정하세요: export SECRET_KEY='...'")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'carnerf.db')}")

# Uploads
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")

# External APIs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CARAPIS_API_KEY = os.getenv("CARAPIS_API_KEY", "")
