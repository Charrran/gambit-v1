import asyncio
import traceback
from neomodel import adb
from app.models.graph import EpisodeNode
from app.core.config import settings

async def test():
    host = settings.neo4j_uri.split("://")[-1]
    url = f"neo4j+ssc://{settings.neo4j_username}:{settings.neo4j_password}@{host}"
    await adb.set_connection(url)
    try:
        nodes = await EpisodeNode.nodes.all()
        print("ASYNC SET.ALL WORKS", [n.node_id for n in nodes])
    except Exception as e:
        print("ASYNC SET ERROR!!", e)
        traceback.print_exc()

asyncio.run(test())
