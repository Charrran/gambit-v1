"""
Start the real Gambit server (uvicorn + app.main) for an end-to-end run.

    python -m sim.e2e_server [--port 8765] [--offline-llm] [--os-trust-store]
                             [--groq-model openai/gpt-oss-20b] [--gemini-model gemini-flash-latest]

Redis and Neo4j are replaced in-process by sim.harness fakes (the hosted instances
in .env are no longer reachable); the LLM Director uses the real Groq/Gemini keys
from .env unless --offline-llm is given. Everything else -- FastAPI routes, the
WebSocket game loop, scene/choice/finale logic -- is the production code.
"""
import argparse
import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8765)
ap.add_argument("--offline-llm", action="store_true")
ap.add_argument("--os-trust-store", action="store_true",
                help="also trust the Windows certificate store (needed when antivirus/proxy TLS inspection "
                     "re-signs api.groq.com, e.g. AVG Web Shield; certifi alone then fails every LLM call)")
ap.add_argument("--groq-model", default=None,
                help="override the Groq model id hardcoded in ai_engine (llama-3.1-8b-instant is retired)")
ap.add_argument("--gemini-model", default=None,
                help="override the Gemini model id hardcoded in ai_engine (gemini-2.0-flash is retired)")
args = ap.parse_args()

if args.os_trust_store:
    import ssl
    import tempfile

    import certifi

    pems = [Path(certifi.where()).read_text(encoding="utf-8")]
    for store in ("ROOT", "CA"):
        for der, encoding, _trust in ssl.enum_certificates(store):
            if encoding == "x509_asn":
                pems.append(ssl.DER_cert_to_PEM_cert(der))
    bundle = Path(tempfile.gettempdir()) / "gambit_e2e_ca_bundle.pem"
    bundle.write_text(chr(10).join(pems), encoding="utf-8")
    os.environ["SSL_CERT_FILE"] = str(bundle)
    os.environ["REQUESTS_CA_BUNDLE"] = str(bundle)

env = dotenv_values(ROOT / ".env")
for key in ("GROQ_API_KEY", "GEMINI_API_KEY"):
    if env.get(key) and not args.offline_llm:
        os.environ[key] = env[key]

from sim.harness import install_offline_backends  # noqa: E402  (sets offline Redis/Neo4j placeholders)

install_offline_backends(llm_stubs=args.offline_llm)


def _override_model(owner, attr, model):
    original = getattr(owner, attr)

    def call(*a, **kw):
        kw["model"] = model
        return original(*a, **kw)

    setattr(owner, attr, call)


if not args.offline_llm:
    from app.services.ai_engine import ai_engine

    if args.groq_model:
        _override_model(ai_engine.groq_client.chat.completions, "create", args.groq_model)
    if args.gemini_model:
        _override_model(ai_engine.gemini_client.chat.completions, "create", args.gemini_model)
        _override_model(ai_engine.raw_gemini_client.models, "generate_content", args.gemini_model)

import uvicorn  # noqa: E402

import app.main as main  # noqa: E402


async def _no_neo4j():
    return None


main.init_neo4j_async = _no_neo4j
print(f"[e2e] LLM Director: {'offline stubs' if args.offline_llm else 'LIVE (Groq/Gemini)'}", flush=True)
uvicorn.run(main.app, host="127.0.0.1", port=args.port, log_level="warning")
