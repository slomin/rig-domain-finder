from __future__ import annotations

__all__ = ["check_domains", "choose_suggested_best"]


def __getattr__(name: str):
    if name in {"check_domains", "choose_suggested_best"}:
        from .checker import check_domains, choose_suggested_best

        return {"check_domains": check_domains, "choose_suggested_best": choose_suggested_best}[name]
    raise AttributeError(name)
