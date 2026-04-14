import neomodel
from app.core.config import settings

# ZERO-POINT INITIALIZATION: Ensuring Neomodel OGM registry is hydrated
# BEFORE any submodules (models, services) are imported by FastAPI/Uvicorn.
_uri = settings.neo4j_uri
_host = _uri.split("://")[1] if "://" in _uri else _uri
neomodel.config.DATABASE_URL = f"neo4j+ssc://{settings.neo4j_username}:{settings.neo4j_password}@{_host}"
