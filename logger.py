"""
Configuração de logging da API Docas.

Segue o padrão usado na disciplina: um logger nomeado, saída no console e em
arquivo rotativo dentro da pasta log/.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

PASTA_LOG = "log"
os.makedirs(PASTA_LOG, exist_ok=True)

FORMATO = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

logger = logging.getLogger("docas")
logger.setLevel(logging.INFO)

# Evita handlers duplicados quando o módulo é importado mais de uma vez
if not logger.handlers:
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(FORMATO))
    logger.addHandler(console)

    arquivo = RotatingFileHandler(
        os.path.join(PASTA_LOG, "docas.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    arquivo.setFormatter(logging.Formatter(FORMATO))
    logger.addHandler(arquivo)
