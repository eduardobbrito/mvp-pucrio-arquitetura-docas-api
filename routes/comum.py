"""
Utilidades compartilhadas pelos blueprints: respostas de erro padronizadas e
descrições dos códigos HTTP no Swagger.
"""
from flask_openapi3.utils import HTTP_STATUS

# Descrições das respostas no Swagger em português. O flask-openapi3 usa as
# frases padrão do HTTP em inglês ("Bad Request"...) a partir deste dicionário,
# então o atualizamos aqui: este módulo é importado por todos os blueprints
# antes dos decoradores de rota, que é quando a documentação é montada.
HTTP_STATUS.update(
    {
        "200": "Sucesso",
        "201": "Criado",
        "400": "Dados inválidos",
        "404": "Não encontrado",
        "409": "Conflito com o estado atual (ex.: transição de status inválida)",
        "502": "Falha em API externa",
    }
)


def erro(mensagem, status):
    """Monta uma resposta no formato de ErroSchema com o código HTTP informado."""
    return {"mensagem": mensagem}, status
