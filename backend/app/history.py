"""Chat history stores: DynamoDB (production), JSON file, or in-memory."""

import json
import os

from app.config import Settings, boto_session


class InMemoryHistoryStore:
    def __init__(self) -> None:
        self.sessions: dict[str, list[dict]] = {}

    def append(self, session_id: str, role: str, content: str) -> None:
        self.sessions.setdefault(session_id, []).append(
            {"role": role, "content": content}
        )

    def get(self, session_id: str) -> list[dict]:
        return list(self.sessions.get(session_id, []))


class LocalJsonHistoryStore:
    def __init__(self, path: str = "chat_history.json"):
        self.path = path
        self.data: dict[str, list[dict]] = {}
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    self.data = json.load(fh)
            except Exception:
                self.data = {}

    def append(self, session_id: str, role: str, content: str) -> None:
        self.data.setdefault(session_id, []).append(
            {"role": role, "content": content}
        )
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh)

    def get(self, session_id: str) -> list[dict]:
        return list(self.data.get(session_id, []))


class DynamoHistoryStore:
    def __init__(self, settings: Settings):
        self.table = boto_session(settings).resource("dynamodb").Table(
            settings.chat_history_table
        )

    def append(self, session_id: str, role: str, content: str) -> None:
        import time

        self.table.put_item(
            Item={
                "session_id": session_id,
                "ts": int(time.time() * 1000),
                "role": role,
                "content": content,
            }
        )

    def get(self, session_id: str) -> list[dict]:
        resp = self.table.query(
            KeyConditionExpression="session_id = :s",
            ExpressionAttributeValues={":s": session_id},
        )
        items = sorted(resp.get("Items", []), key=lambda i: i["ts"])
        return [{"role": i["role"], "content": i["content"]} for i in items]


def get_history_store(settings: Settings):
    if settings.demo:
        return InMemoryHistoryStore()
    if settings.chat_history_table:
        return DynamoHistoryStore(settings)
    return LocalJsonHistoryStore()
