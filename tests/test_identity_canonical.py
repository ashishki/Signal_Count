from app.identity.canonical import canonical_json_bytes
from app.identity.hashing import canonical_json_hash, keccak256_hex


def test_canonical_json_is_order_stable() -> None:
    left = {
        "thesis": "ETH outperforms",
        "asset": "ETH",
        "horizon_days": 30,
        "metadata": {"roles": ["risk", "regime"], "priority": 1},
    }
    right = {
        "metadata": {"priority": 1, "roles": ["risk", "regime"]},
        "horizon_days": 30,
        "asset": "ETH",
        "thesis": "ETH outperforms",
    }

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_bytes(left) == (
        b'{"asset":"ETH","horizon_days":30,'
        b'"metadata":{"priority":1,"roles":["risk","regime"]},'
        b'"thesis":"ETH outperforms"}'
    )


def test_keccak_hash_matches_fixture() -> None:
    payload = {"asset": "ETH", "horizon_days": 30, "thesis": "ETH outperforms"}

    assert canonical_json_hash(payload) == (
        "0x6e2105fcb991d498283d2b9becc8d22aa539f8df2a8aada41b8f139d7cef677a"
    )


def test_keccak_helper_uses_ethereum_keccak_not_sha3_256() -> None:
    assert keccak256_hex(b"hello") == (
        "0x1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8"
    )
