from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.blockchain.hash_utils import stable_json_hash, stringify_value


@dataclass(slots=True)
class AuditBlock:
    index: int
    timestamp: datetime
    data: dict[str, Any]
    previous_hash: str
    hash: str = field(init=False)

    def __post_init__(self) -> None:
        self.hash = stable_json_hash(
            {
                "index": self.index,
                "timestamp": stringify_value(self.timestamp),
                "data": self.data,
                "previous_hash": self.previous_hash,
            }
        )

    @classmethod
    def genesis(cls) -> "AuditBlock":
        return cls(
            index=0,
            timestamp=datetime.now(timezone.utc),
            data={
                "action_type": "GENESIS",
                "performed_by": {"role": "system", "id": "system", "name": "Smart Civic"},
                "metadata": {"description": "Genesis block for Smart Civic transparency audit ledger"},
            },
            previous_hash="0" * 64,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "chain_type": "audit",
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            # Backward-compatible aliases for existing ledger viewers/tools.
            "prev_hash": self.previous_hash,
            "block_hash": self.hash,
            "mined_at": self.timestamp,
            "algorithm": "sha256",
            "is_genesis": self.index == 0,
        }
