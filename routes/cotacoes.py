"""Rotas de cotações: contratação de uma cotação gerada."""
from flask_openapi3 import APIBlueprint, Tag

from database import Session
from model import Cotacao
from routes.comum import erro
from schemas import CotacaoPath, ErroSchema, PedidoDetalheSchema, apresentar_detalhe
from services.erros import TransicaoInvalida
from services.fluxo import transitar

tag_cotacoes = Tag(name="Cotações", description="Contratação de cotações de frete")

bp_cotacoes = APIBlueprint("cotacoes", __name__, abp_tags=[tag_cotacoes])


@bp_cotacoes.put(
    "/cotacoes/<int:cotacao_id>/contratar",
    summary="Contrata uma cotação",
    responses={200: PedidoDetalheSchema, 404: ErroSchema, 409: ErroSchema},
)
def contratar(path: CotacaoPath):
    """
    Contrata a cotação escolhida: o pedido passa de cotado para contratado.

    Grava no pedido a cotação contratada e a data prometida ao cliente, que
    depois serve para identificar atrasos.
    """
    with Session() as sessao:
        cotacao = sessao.get(Cotacao, path.cotacao_id)
        if not cotacao:
            return erro("Cotação não encontrada", 404)
        pedido = cotacao.pedido
        try:
            transitar(
                sessao,
                pedido,
                "contratado",
                f"{cotacao.modalidade.nome}: R$ {cotacao.valor:.2f}, {cotacao.prazo_dias_uteis} dia(s) útil(eis)",
            )
        except TransicaoInvalida as falha:
            return erro(str(falha), 409)
        pedido.cotacao_contratada_id = cotacao.id
        pedido.data_prometida = cotacao.data_prometida
        sessao.commit()
        return apresentar_detalhe(pedido), 200
