"""
Ponto de entrada da API Docas.

Cria a aplicação flask-openapi3 (que gera Swagger, ReDoc e RapiDoc a partir dos
schemas Pydantic) e registra a rota raiz. Os blueprints de cada recurso são
registrados nos passos seguintes do plano.
"""
from datetime import date

from flask import make_response, redirect
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_openapi3 import Info, OpenAPI, Tag

import config
from database import criar_tabelas
from logger import logger
from routes import bp_cotacoes, bp_painel, bp_pedidos, bp_tarifas
from schemas import ErroSchema
from services.brasilapi import resolver_coordenadas_armazem
from services.seeds import carregar_seeds

info = Info(
    title="Docas API",
    version="1.0.0",
    description=(
        "API de expedição e cotação de frete para lojas online. Importa pedidos da "
        "DummyJSON, confirma endereços na BrasilAPI, calcula cotações por faixas de "
        "peso e distância e acompanha o fluxo recebido → cotado → contratado → "
        "em trânsito → entregue."
    ),
)


class ProvedorJson(DefaultJSONProvider):
    """
    Serializador JSON da aplicação.

    O Flask converte datas para o formato HTTP ("Tue, 06 Oct 2026 00:00:00 GMT");
    aqui usamos ISO 8601 ("2026-10-06"), que a interface e o Swagger entendem.
    ensure_ascii = False mantém os acentos legíveis.
    """

    ensure_ascii = False

    @staticmethod
    def default(objeto):
        """Converte date/datetime em texto ISO; demais tipos seguem o padrão do Flask."""
        if isinstance(objeto, date):
            return objeto.isoformat()
        return DefaultJSONProvider.default(objeto)


def erro_validacao(erro_pydantic):
    """
    Converte erros de validação do Pydantic em HTTP 400 no formato ErroSchema.

    Por padrão o flask-openapi3 responde 422 com a lista crua do Pydantic; aqui
    juntamos as mensagens em uma frase, como pede a convenção da API.
    """
    detalhes = "; ".join(
        f"{'.'.join(str(parte) for parte in item['loc'])}: {item['msg']}" for item in erro_pydantic.errors()
    )
    return make_response({"mensagem": f"Dados inválidos — {detalhes}"}, 400)


app = OpenAPI(
    __name__,
    info=info,
    validation_error_status=400,
    validation_error_model=ErroSchema,
    validation_error_callback=erro_validacao,
)
# Datas em ISO 8601 e acentos legíveis no JSON das respostas
app.json = ProvedorJson(app)

# CORS: só a interface (origens do .env, variável FRONT_URL) pode chamar a API pelo navegador
CORS(app, origins=config.ORIGENS_CORS)

# Garante que as tabelas existem antes de atender requisições
criar_tabelas()
carregar_seeds()
# Origem dos fretes: tenta a BrasilAPI e, se falhar, mantém o padrão de config.py
resolver_coordenadas_armazem()

tag_documentacao = Tag(name="Documentação", description="Seleção da documentação: Swagger, ReDoc ou RapiDoc.")


@app.get("/", tags=[tag_documentacao])
def inicio():
    """Redireciona para /openapi, onde se escolhe o estilo de documentação."""
    return redirect("/openapi")


# Registro dos blueprints (um por recurso)
app.register_api(bp_pedidos)
app.register_api(bp_cotacoes)
app.register_api(bp_tarifas)
app.register_api(bp_painel)


if __name__ == "__main__":
    logger.info("Iniciando a API Docas na porta %s", config.PORTA)
    app.run(host="0.0.0.0", port=config.PORTA, debug=True)
