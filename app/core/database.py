from neomodel import adb
from app.core.config import settings
async def init_neo4j_async():
    """
    Initializes the async Neo4j connection for neomodel.
    Uses neo4j+ssc to bypass SSL validation on Windows/AuraDB.
    """
    uri = settings.neo4j_uri
    username = settings.neo4j_username
    password = settings.neo4j_password
    
    # Ensure protocol is shifted to neo4j+ssc for SSL bypass if needed
    if "://" in uri:
        host = uri.split("://")[1]
    else:
        host = uri
        
    db_url = f"neo4j+ssc://{username}:{password}@{host}"
    
    # CRITICAL: Neomodel registry requires this sync config even for async nodes.
    from neomodel import config
    config.DATABASE_URL = db_url
    
    # neomodel 6.x async connection
    await adb.set_connection(db_url)
