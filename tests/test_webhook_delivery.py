
import pytest

from app.services.webhook_delivery_service import claim_webhook_delivery


def test_new_delivery_is_accepted(tmp_path, monkeypatch):
    database_path = tmp_path / "test_checkpoints.sqlite"
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(database_path))

    result = claim_webhook_delivery("delivery-001")

    assert result is True


def test_duplicate_delivery_is_rejected(tmp_path, monkeypatch):
    database_path = tmp_path / "test_checkpoints.sqlite"
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(database_path))

    first_result = claim_webhook_delivery("delivery-001")
    second_result = claim_webhook_delivery("delivery-001")

    assert first_result is True
    assert second_result is False


def test_different_deliveries_are_accepted(tmp_path, monkeypatch):
    database_path = tmp_path / "test_checkpoints.sqlite"
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(database_path))

    first_result = claim_webhook_delivery("delivery-001")
    second_result = claim_webhook_delivery("delivery-002")

    assert first_result is True
    assert second_result is True


def test_empty_delivery_id_is_rejected():
    with pytest.raises(ValueError, match="cannot be empty"):
        claim_webhook_delivery("")

def test_released_delivery_can_be_retried(tmp_path, monkeypatch):
    from app.services.webhook_delivery_service import release_webhook_delivery

    database_path = tmp_path / "test_checkpoints.sqlite"
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(database_path))

    assert claim_webhook_delivery("delivery-003") is True

    release_webhook_delivery("delivery-003")

    assert claim_webhook_delivery("delivery-003") is True
