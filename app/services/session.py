from app.core.cache import redis_pool


class SessionManager:
    def get_session(self, session_id: str) -> dict:
        data = redis_pool.get(session_id)
        return {"session_id": session_id, "data": data}

    def save_session(self, session_id: str, payload: dict) -> None:
        redis_pool.set(session_id, str(payload))
