from __future__ import annotations

from pathlib import Path

from march_mania.publication.portfolio_contract import validate_repository


def test_employer_portfolio_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_repository(root) == []
