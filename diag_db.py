import neomodel
import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

print("--- Neomodel Registration Diagnostic ---")

try:
    from app.core.config import settings
    print(f"[1] Settings Loaded. Neo4j URI: {settings.neo4j_uri}")
    
    # Try importing graph models - this triggers metaclass
    print("[2] Importing app.models.graph...")
    from app.models.graph import EpisodeNode
    
    print(f"[3] current neomodel.config.DATABASE_URL: {neomodel.config.DATABASE_URL}")
    
    # Check if EpisodeNode has the required metadata
    # The error "This class hasn't been setup properly" comes from accessing DoesNotExist
    print("[4] Checking EpisodeNode.DoesNotExist...")
    has_meta = hasattr(EpisodeNode, "DoesNotExist")
    print(f"    - Has DoesNotExist attribute: {has_meta}")
    
    if has_meta:
        print(f"    - DoesNotExist class: {EpisodeNode.DoesNotExist}")
        # check if it has the _model_class property (Neomodel internal)
        print(f"    - DoesNotExist has _model_class: {hasattr(EpisodeNode.DoesNotExist, '_model_class')}")
    
    print("\n--- Diagnostic Complete ---")

except Exception as e:
    print(f"\n[!] Diagnostic Failed with error: {e}")
    import traceback
    traceback.print_exc()
