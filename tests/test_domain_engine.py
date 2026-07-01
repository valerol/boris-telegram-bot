from __future__ import annotations

from boris.engine import boris_run
from domain.engine import domain_run
from sima.engine import sima_run


def test_domain_layer_detects_architecture_context() -> None:
    sima = sima_run("Расскажи о BOIS")
    domain = domain_run(sima)
    boris = boris_run(sima, domain)

    assert domain["domain"] == "architecture"
    assert domain["signals"] == ["architecture"]
    assert boris["domain"] == "architecture"
    assert "preserve architecture scope" in boris["constraints"]


def test_boris_constraints_change_by_domain() -> None:
    technical_sima = sima_run("Как настроить PostgreSQL server")
    business_sima = sima_run("Расскажи бизнес план")

    technical = boris_run(technical_sima, domain_run(technical_sima))
    business = boris_run(business_sima, domain_run(business_sima))

    assert technical["domain"] == "technical"
    assert business["domain"] == "business"
    assert technical["constraints"] != business["constraints"]
    assert "include runnable steps" in technical["constraints"]
    assert "state assumptions" in business["constraints"]
