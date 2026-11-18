
import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()


def claim_webhook_delivery(delivery_id: str) -> bool:
    """Register a delivery ID. Return False if it already exists."""
    if not delivery_id or not delivery_id.strip():
        raise ValueError("GitHub delivery ID cannot be empty.")

    database_path = os.getenv("CHECKPOINT_DB_PATH", "checkpoints.sqlite")
    connection = sqlite3.connect(database_path, timeout=10)

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                delivery_id TEXT PRIMARY KEY,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO webhook_deliveries (delivery_id)
            VALUES (?)
            """,
            (delivery_id.strip(),),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def release_webhook_delivery(delivery_id: str) -> None:
    """Remove a claimed delivery ID so a failed delivery can be retried."""
    if not delivery_id or not delivery_id.strip():
        raise ValueError("GitHub delivery ID cannot be empty.")

    database_path = os.getenv("CHECKPOINT_DB_PATH", "checkpoints.sqlite")
    connection = sqlite3.connect(database_path, timeout=10)

    try:
        connection.execute(
            """
            DELETE FROM webhook_deliveries
            WHERE delivery_id = ?
            """,
            (delivery_id.strip(),),
        )
        connection.commit()
    finally:
        connection.close()
