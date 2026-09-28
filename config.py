"""
Constantes de configuração da API Docas.

Centraliza URLs das APIs externas, dados do armazém de origem, parâmetros de
paginação e variáveis lidas do ambiente (.env). Manter tudo aqui evita
"números mágicos" espalhados pelo código.
"""
import os

from dotenv import load_dotenv

# Carrega o arquivo .env, se existir (em produção as variáveis vêm do ambiente)
load_dotenv()

# --- Servidor -----------------------------------------------------------------
PORTA = int(os.getenv("PORTA", "5000"))

# Origens autorizadas no CORS (a interface). Várias origens separadas por vírgula.
ORIGENS_CORS = [
    origem.strip()
    for origem in os.getenv("FRONT_URL", "http://localhost:3000,http://localhost:5173").split(",")
    if origem.strip()
]

# --- APIs externas -----------------------------------------------------------
URL_DUMMYJSON = "https://dummyjson.com"
URL_BRASILAPI = "https://brasilapi.com.br"

# Tempo máximo (em segundos) de espera por uma resposta externa
TIMEOUT_EXTERNO = 8

# Identifica o projeto nas chamadas externas (boa prática com APIs públicas)
USER_AGENT = "DocasMVP/1.0 (PUC-Rio - Arquitetura de Software)"

# --- Armazém (origem de todos os fretes) --------------------------------------
# Praia de Botafogo, 300 — Botafogo, Rio de Janeiro/RJ.
# As coordenadas abaixo são o padrão; no startup a API tenta atualizá-las pela
# BrasilAPI (ver resolver_coordenadas_armazem em services/brasilapi.py).
ARMAZEM = {
    "logradouro": "Praia de Botafogo",
    "numero": "300",
    "bairro": "Botafogo",
    "cidade": "Rio de Janeiro",
    "uf": "RJ",
    "cep": "22250040",
    "latitude": -22.9463,
    "longitude": -43.1822,
}

# --- Paginação ---------------------------------------------------------------
POR_PAGINA_PADRAO = 10
POR_PAGINA_MAXIMO = 100

# --- Frete --------------------------------------------------------------------
# Fator de cubagem rodoviário: peso cubado (kg) = volume (cm³) / 6000
FATOR_CUBAGEM = 6000
