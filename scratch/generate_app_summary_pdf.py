from pathlib import Path
from textwrap import wrap


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT = 54
RIGHT = 558
TOP = 742
BOTTOM = 50


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class PDFBuilder:
    def __init__(self):
        self.lines = []
        self.current_font = None
        self.current_size = None

    def set_font(self, font_name: str, size: int) -> None:
        if (font_name, size) != (self.current_font, self.current_size):
            self.lines.append(f"/{font_name} {size} Tf")
            self.current_font = font_name
            self.current_size = size

    def draw_text(self, x: int, y: int, text: str) -> None:
        safe = escape_pdf_text(text)
        self.lines.append(f"1 0 0 1 {x} {y} Tm ({safe}) Tj")

    def build_stream(self) -> bytes:
        body = "BT\n" + "\n".join(self.lines) + "\nET\n"
        return body.encode("latin-1", errors="replace")


def add_wrapped_text(pdf: PDFBuilder, text: str, x: int, y: int, width_chars: int, font: str, size: int, leading: int):
    pdf.set_font(font, size)
    lines = wrap(text, width=width_chars, break_long_words=False, break_on_hyphens=False) or [text]
    for idx, line in enumerate(lines):
        pdf.draw_text(x, y - (idx * leading), line)
    return y - (len(lines) * leading)


def main():
    output_dir = Path("output/pdf")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "gambit_app_summary.pdf"

    pdf = PDFBuilder()
    y = TOP

    pdf.set_font("F2", 18)
    pdf.draw_text(LEFT, y, "Gambit App Summary")
    y -= 24

    pdf.set_font("F1", 9)
    pdf.draw_text(LEFT, y, "Repo evidence date: 2026-04-17")
    y -= 18

    sections = [
        (
            "What It Is",
            [
                "Gambit is a FastAPI-based multiplayer narrative strategy engine built around an authored Neo4j story graph, Redis-backed session state, and AI-generated scene text.",
                "The current repo centers on one episode, 'The Regent Rebellion', with REST lobby setup and a WebSocket-driven live game loop.",
            ],
        ),
        (
            "Who It's For",
            [
                "Primary persona: a small group of 2 to 4 players and a host/tester running a live political story session locally via API calls and WebSocket clients.",
            ],
        ),
        (
            "What It Does",
            [
                "Creates multiplayer lobbies and returns a short session id.",
                "Lets 2 to 4 players join, then assigns story roles on game start.",
                "Streams live scene updates over WebSockets for each player.",
                "Runs spotlight turns for a single acting role and group votes for poll or interrogation scenes.",
                "Loads authored story beats and conditional transitions from Neo4j.",
                "Stores session state, revisions, votes, flags, and player traits in Redis with an in-process cache.",
                "Uses Groq to generate turn flavor and options, then Gemini to compare the ending against the canonical historical path.",
            ],
        ),
        (
            "How It Works",
            [
                "Client flow: players create/join/start sessions over REST, then connect to /ws/play/{session_id}/{player_id}.",
                "App layer: app/main.py owns the scene loop, validates choices, selects spotlight actors, and emits NARRATIVE_BEAT, SPOTLIGHT_CHOICE, POLL_REQUEST, WAITING, and GAME_OVER messages.",
                "State layer: app/services/state.py persists GameState in Redis and keeps a local cache plus per-session locks/events for coordination.",
                "Narrative layer: app/models/graph.py defines EpisodeNode and LEADS_TO relationships; seed_db.py loads a 15-node EP_01_REGENT graph into Neo4j.",
                "AI layer: app/services/ai_engine.py calls Groq for spotlight turn text and Gemini for ending comparison; fallback text is used if generation fails.",
            ],
        ),
        (
            "How To Run",
            [
                "1. Create .env with NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, REDIS_URL, GROQ_API_KEY, and GEMINI_API_KEY.",
                "2. Create a virtual environment and install requirements.txt.",
                "3. Seed Neo4j with: python seed_db.py",
                "4. Start the app with: uvicorn app.main:app --reload",
                "5. Create a lobby: POST /lobby/create, join players, start the game, then connect clients to ws://localhost:8000/ws/play/{session_id}/{player_id}.",
            ],
        ),
        (
            "Not Found In Repo",
            [
                "Dedicated browser/mobile UI, deployment instructions, automated test suite, and production architecture docs were not found in repo.",
            ],
        ),
    ]

    for heading, items in sections:
        pdf.set_font("F2", 11)
        pdf.draw_text(LEFT, y, heading)
        y -= 14
        for item in items:
            if heading == "What It Does":
                text = f"- {item}"
                y = add_wrapped_text(pdf, text, LEFT + 8, y, 82, "F1", 9, 11)
            elif heading in {"How It Works", "How To Run", "Not Found In Repo"}:
                text = f"- {item}"
                y = add_wrapped_text(pdf, text, LEFT + 8, y, 84, "F1", 8, 10)
            else:
                y = add_wrapped_text(pdf, item, LEFT, y, 90, "F1", 9, 11)
            y -= 2
        y -= 6

    if y < BOTTOM:
        raise RuntimeError(f"Content overflowed page bounds: y={y}")

    stream = pdf.build_stream()

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
    objects.append(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
        f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>".encode("latin-1")
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"endstream")

    pdf_bytes = bytearray(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf_bytes))
        pdf_bytes.extend(f"{idx} 0 obj\n".encode("latin-1"))
        pdf_bytes.extend(obj)
        pdf_bytes.extend(b"\nendobj\n")

    xref_pos = len(pdf_bytes)
    pdf_bytes.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf_bytes.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf_bytes.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf_bytes.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )

    output_path.write_bytes(pdf_bytes)
    print(output_path.resolve())


if __name__ == "__main__":
    main()
