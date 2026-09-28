"""
Configuração do banco de dados SQLite com SQLAlchemy.

Expõe:
- engine: conexão com o arquivo database/docas.sqlite3;
- Session: fábrica de sessões usada pelas rotas e serviços;
- Base: classe base declarativa dos modelos;
- criar_tabelas(): cria as tabelas que ainda não existem (chamada no startup).
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# O arquivo do banco fica na mesma pasta deste módulo
PASTA_BANCO = os.path.dirname(os.path.abspath(__file__))
URL_BANCO = os.getenv("URL_BANCO", f"sqlite:///{os.path.join(PASTA_BANCO, 'docas.sqlite3')}")

# check_same_thread=False permite usar a conexão nas threads do servidor web
engine = create_engine(URL_BANCO, echo=False, connect_args={"check_same_thread": False})

# expire_on_commit=False mantém os objetos legíveis após o commit (útil ao serializar a resposta)
Session = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe base de todos os modelos SQLAlchemy da aplicação."""


def criar_tabelas():
    """Importa os modelos (para registrá-los na Base) e cria as tabelas ausentes."""
    import model  # noqa: F401 — o import registra os modelos no metadata

    Base.metadata.create_all(engine)
