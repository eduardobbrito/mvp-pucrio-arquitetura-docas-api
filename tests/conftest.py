"""
Configuração compartilhada dos testes (pytest).

Cada teste recebe uma sessão ligada a um banco SQLite em memória, criado do
zero e populado com os seeds de modalidades e tarifas. Assim os testes não
tocam o arquivo database/docas.sqlite3 nem dependem de rede.
"""
import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Permite importar os módulos da aplicação (config, model, services...) a partir de tests/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import model  # noqa: E402,F401 — registra os modelos na Base
from database import Base  # noqa: E402
from model import Modalidade, Pedido, Tarifa  # noqa: E402
from services.seeds import ler_json  # noqa: E402


@pytest.fixture
def sessao():
    """Sessão em um banco em memória com as tabelas criadas e os seeds carregados."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)
    with fabrica() as sessao_teste:
        for dados in ler_json("modalidades.json"):
            sessao_teste.add(Modalidade(**dados))
        for dados in ler_json("tarifas.json"):
            sessao_teste.add(Tarifa(**dados))
        sessao_teste.commit()
        yield sessao_teste
    engine.dispose()


@pytest.fixture
def novo_pedido(sessao):
    """Fábrica de pedidos gravados no banco de teste, com valores padrão ajustáveis."""

    def criar(**campos):
        """Grava um pedido com os campos informados sobrescrevendo os padrões."""
        dados = {
            "id_externo": campos.pop("id_externo", 1),
            "cliente_nome": "Cliente Teste",
            "cliente_email": "cliente@teste.com",
            "cep": "01310100",
            "logradouro": "Avenida Paulista",
            "numero": "1578",
            "bairro": "Bela Vista",
            "cidade": "São Paulo",
            "uf": "SP",
            "peso_cobrado": 2.0,
            "distancia_km": 690,
            "status": "recebido",
        }
        dados.update(campos)
        pedido = Pedido(**dados)
        sessao.add(pedido)
        sessao.commit()
        return pedido

    return criar
