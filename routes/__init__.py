"""Blueprints da API Docas, um por recurso."""
from routes.cotacoes import bp_cotacoes
from routes.painel import bp_painel
from routes.pedidos import bp_pedidos
from routes.tarifas import bp_tarifas

__all__ = ["bp_pedidos", "bp_cotacoes", "bp_tarifas", "bp_painel"]
