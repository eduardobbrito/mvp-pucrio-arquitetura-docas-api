"""Utilidades compartilhadas pelos blueprints: respostas de erro padronizadas."""


def erro(mensagem, status):
    """Monta uma resposta no formato de ErroSchema com o código HTTP informado."""
    return {"mensagem": mensagem}, status
