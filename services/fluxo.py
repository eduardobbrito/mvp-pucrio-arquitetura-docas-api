"""
Máquina de estados do pedido.

Define quais mudanças de status são permitidas e registra cada transição em
movimentacoes, formando a linha do tempo do pedido.

    recebido → cotado → contratado → em_transito → entregue
        └──────────┴──────────┴──→ cancelado  (só antes de em_transito)
"""
from datetime import datetime

from model import Movimentacao
from services.erros import TransicaoInvalida

# Para cada status, os status seguintes permitidos. Qualquer outro destino é 409.
TRANSICOES = {
    "recebido": ["cotado", "cancelado"],
    "cotado": ["contratado", "cancelado"],
    "contratado": ["em_transito", "cancelado"],
    "em_transito": ["entregue"],  # depois de sair do armazém não se cancela
    "entregue": [],  # estado final
    "cancelado": [],  # estado final
}

# Nomes legíveis para as mensagens de erro
ROTULOS = {
    "recebido": "recebido",
    "cotado": "cotado",
    "contratado": "contratado",
    "em_transito": "em trânsito",
    "entregue": "entregue",
    "cancelado": "cancelado",
}


def pode_transitar(status_atual, novo_status):
    """True se a transição status_atual → novo_status é permitida."""
    return novo_status in TRANSICOES.get(status_atual, [])


def transitar(sessao, pedido, novo_status, observacao=None):
    """
    Muda o status do pedido e grava a movimentação correspondente.

    Lança TransicaoInvalida (HTTP 409) se a mudança não estiver em TRANSICOES.
    Não faz commit: a rota decide quando confirmar, junto com outras alterações.
    """
    if novo_status not in TRANSICOES:
        raise TransicaoInvalida(f"Status desconhecido: '{novo_status}'")
    if not pode_transitar(pedido.status, novo_status):
        raise TransicaoInvalida(
            f"Transição inválida: um pedido {ROTULOS[pedido.status]} não pode passar para {ROTULOS[novo_status]}"
        )
    anterior = pedido.status
    pedido.status = novo_status
    pedido.atualizado_em = datetime.now()
    sessao.add(Movimentacao(pedido=pedido, de_status=anterior, para_status=novo_status, observacao=observacao))
