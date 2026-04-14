import asyncio
import os
from dotenv import load_dotenv
from neomodel import adb
from app.models.graph import EpisodeNode
from app.core.config import settings

load_dotenv()

async def verify():
    host = settings.neo4j_uri.split("://")[-1]
    url = f"neo4j+ssc://{settings.neo4j_username}:{settings.neo4j_password}@{host}"
    print(f"[*] Connecting with URL: neo4j+ssc://***@{host}")
    await adb.set_connection(url)
    nodes = await EpisodeNode.nodes.all()
    print(f"[✓] Found {len(nodes)} node(s):")
    for n in nodes:
        print(f"    - {n.node_id}")
    await adb.close_connection()

if __name__ == "__main__":
    asyncio.run(verify())
