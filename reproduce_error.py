import os
import sys
import asyncio
from neomodel import config, adb

# Ensure project root in PATH
sys.path.append(os.getcwd())

from app.core.config import settings

async def reproduce():
    print("--- Reproduction Test Start ---")
    
    # Imports MUST happen after path setup
    from app.models.graph import EpisodeNode
    
    # 1. Check if the class is setup
    print(f"[1] EpisodeNode setup: {hasattr(EpisodeNode, 'DoesNotExist')}")
    
    # 2. Try to access nodes manager - this is where the loop fails
    print("[2] Attempting EpisodeNode.nodes.get_or_none...")
    try:
        # We don't even need a real database to trigger the SETUP error
        # because the setup check happens before connection in neomodel's nodes manager
        node = await EpisodeNode.nodes.get_or_none(node_id="test_reproduction_id")
        print(f"[3] Success! (Got {node})")
    except RuntimeError as e:
        print(f"[!] Caught expected RuntimeError: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"[!] Caught unexpected Exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce())
