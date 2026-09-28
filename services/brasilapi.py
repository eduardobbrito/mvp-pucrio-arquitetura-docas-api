"""
Cliente HTTP da BrasilAPI (https://brasilapi.com.br), rota de CEP v2.

Confirma os endereços dos pedidos e obtém coordenadas para calcular a distância
até o armazém. Nenhuma falha aqui pode travar a importação: as funções devolvem
None e quem chama usa o endereço do seed como fallback.
"""
import requests

import config
from logger import logger

CABECALHOS = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}


def consultar_cep(cep):
    """
    Consulta um CEP e devolve um dicionário normalizado ou None em caso de falha.

    Formato devolvido: cep, logradouro, bairro, cidade, uf, latitude, longitude
    (as coordenadas podem vir None, pois a BrasilAPI nem sempre as tem).
    """
    cep_limpo = "".join(c for c in str(cep) if c.isdigit())
    url = f"{config.URL_BRASILAPI}/api/cep/v2/{cep_limpo}"
    try:
        resposta = requests.get(url, headers=CABECALHOS, timeout=config.TIMEOUT_EXTERNO)
        if resposta.status_code != 200:
            logger.warning("BrasilAPI respondeu %s para o CEP %s", resposta.status_code, cep_limpo)
            return None
        dados = resposta.json()
    except (requests.RequestException, ValueError) as erro:
        logger.warning("Falha ao consultar a BrasilAPI para o CEP %s: %s", cep_limpo, erro)
        return None

    # As coordenadas vêm aninhadas em location.coordinates e como texto
    coordenadas = (dados.get("location") or {}).get("coordinates") or {}
    return {
        "cep": cep_limpo,
        "logradouro": dados.get("street") or "",
        "bairro": dados.get("neighborhood") or "",
        "cidade": dados.get("city") or "",
        "uf": dados.get("state") or "",
        "latitude": _para_float(coordenadas.get("latitude")),
        "longitude": _para_float(coordenadas.get("longitude")),
    }


def _para_float(valor):
    """Converte texto em float; devolve None se vazio ou inválido."""
    try:
        return float(valor) if valor not in (None, "") else None
    except (TypeError, ValueError):
        return None


def resolver_coordenadas_armazem():
    """
    Tenta atualizar as coordenadas do armazém (config.ARMAZEM) pela BrasilAPI.

    Chamada no startup. Se a consulta falhar ou vier sem coordenadas, mantém o
    padrão definido em config.py, e a API sobe normalmente.
    """
    dados = consultar_cep(config.ARMAZEM["cep"])
    if dados and dados["latitude"] is not None and dados["longitude"] is not None:
        config.ARMAZEM["latitude"] = dados["latitude"]
        config.ARMAZEM["longitude"] = dados["longitude"]
        logger.info("Coordenadas do armazém obtidas na BrasilAPI: %s, %s", dados["latitude"], dados["longitude"])
    else:
        logger.info("Usando coordenadas padrão do armazém definidas em config.py")
