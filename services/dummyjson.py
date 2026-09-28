"""
Cliente HTTP da DummyJSON (https://dummyjson.com).

A DummyJSON simula a loja online: seus "carts" são tratados como pedidos, e os
produtos e usuários completam os dados de itens e cliente. Usamos apenas rotas
de leitura, pois as de escrita não persistem.
"""
import requests

import config
from logger import logger
from services.erros import ErroApiExterna

CABECALHOS = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}


def _obter(caminho, parametros=None):
    """
    Faz um GET na DummyJSON e devolve o JSON.

    Centraliza timeout, cabeçalhos e tratamento de erro: qualquer falha de rede
    ou status HTTP inesperado vira ErroApiExterna, que a rota traduz em 502.
    """
    url = f"{config.URL_DUMMYJSON}{caminho}"
    try:
        resposta = requests.get(url, params=parametros, headers=CABECALHOS, timeout=config.TIMEOUT_EXTERNO)
        resposta.raise_for_status()
        return resposta.json()
    except (requests.RequestException, ValueError) as erro:
        logger.error("Falha ao consultar a DummyJSON em %s: %s", url, erro)
        raise ErroApiExterna(f"Não foi possível consultar a DummyJSON ({caminho})") from erro


def listar_carts():
    """Devolve a lista de todos os carts (limit=0 pede todos de uma vez)."""
    return _obter("/carts", {"limit": 0}).get("carts", [])


def buscar_cart(cart_id):
    """Devolve um cart pelo id."""
    return _obter(f"/carts/{cart_id}")


def buscar_produto(produto_id):
    """Devolve um produto; usamos weight (kg), dimensions (cm) e sku."""
    return _obter(f"/products/{produto_id}")


def buscar_usuario(usuario_id):
    """Devolve um usuário; usamos nome, sobrenome e e-mail."""
    return _obter(f"/users/{usuario_id}")
