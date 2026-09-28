"""
Carga inicial de dados (seeds).

Popula modalidades e tarifas a partir dos arquivos JSON da pasta seeds/ quando
as tabelas estão vazias, e oferece a lista de endereços reais usada para
"entregar" os pedidos da DummyJSON (que não têm endereço brasileiro).
"""
import json
import os
import random

from database import Session
from logger import logger
from model import Modalidade, Tarifa

PASTA_SEEDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seeds")


def ler_json(nome_arquivo):
    """Lê e devolve o conteúdo de um arquivo JSON da pasta seeds/."""
    with open(os.path.join(PASTA_SEEDS, nome_arquivo), encoding="utf-8") as arquivo:
        return json.load(arquivo)


def carregar_seeds():
    """
    Insere modalidades e tarifas se as respectivas tabelas estiverem vazias.

    Assim o primeiro startup já tem uma tabela de frete utilizável, e edições
    feitas depois pelo operador (CRUD de tarifas) não são sobrescritas.
    """
    with Session() as sessao:
        if sessao.query(Modalidade).count() == 0:
            for dados in ler_json("modalidades.json"):
                sessao.add(Modalidade(**dados))
            logger.info("Seeds: modalidades carregadas")
        if sessao.query(Tarifa).count() == 0:
            for dados in ler_json("tarifas.json"):
                sessao.add(Tarifa(**dados))
            logger.info("Seeds: tarifas carregadas")
        sessao.commit()


def sortear_endereco():
    """Devolve uma cópia de um endereço real sorteado de seeds/enderecos.json."""
    return dict(random.choice(ler_json("enderecos.json")))
