"""Testes da máquina de estados do pedido (services/fluxo.py)."""
import pytest

from services.erros import TransicaoInvalida
from services.fluxo import pode_transitar, transitar


def test_fluxo_completo_grava_movimentacoes(sessao, novo_pedido):
    """recebido → cotado → contratado → em_transito → entregue, com histórico."""
    pedido = novo_pedido()
    for status in ["cotado", "contratado", "em_transito", "entregue"]:
        transitar(sessao, pedido, status)
    sessao.commit()

    assert pedido.status == "entregue"
    historico = [(m.de_status, m.para_status) for m in pedido.movimentacoes]
    assert historico == [
        ("recebido", "cotado"),
        ("cotado", "contratado"),
        ("contratado", "em_transito"),
        ("em_transito", "entregue"),
    ]


@pytest.mark.parametrize("status_atual", ["recebido", "cotado", "contratado"])
def test_cancelamento_permitido_antes_de_em_transito(sessao, novo_pedido, status_atual):
    """Cancelar é possível enquanto o pedido não saiu do armazém."""
    pedido = novo_pedido(status=status_atual)
    transitar(sessao, pedido, "cancelado", "teste")
    assert pedido.status == "cancelado"
    assert pedido.movimentacoes[-1].observacao == "teste"


@pytest.mark.parametrize(
    "status_atual, novo_status",
    [
        ("em_transito", "cancelado"),  # já saiu do armazém
        ("recebido", "contratado"),  # não pode pular a cotação
        ("contratado", "entregue"),  # não pode pular o trânsito
        ("entregue", "em_transito"),  # não volta atrás
        ("cancelado", "cotado"),  # estado final
    ],
)
def test_transicoes_invalidas_sao_recusadas(sessao, novo_pedido, status_atual, novo_status):
    """Transições fora das regras lançam TransicaoInvalida e não alteram o pedido."""
    pedido = novo_pedido(status=status_atual)
    with pytest.raises(TransicaoInvalida):
        transitar(sessao, pedido, novo_status)
    assert pedido.status == status_atual
    assert pedido.movimentacoes == []


def test_status_desconhecido_e_recusado(sessao, novo_pedido):
    """Um status que não existe na máquina de estados é recusado."""
    pedido = novo_pedido()
    with pytest.raises(TransicaoInvalida, match="desconhecido"):
        transitar(sessao, pedido, "extraviado")


def test_pode_transitar():
    """A consulta simples segue o dicionário de transições."""
    assert pode_transitar("recebido", "cotado")
    assert not pode_transitar("em_transito", "cancelado")
