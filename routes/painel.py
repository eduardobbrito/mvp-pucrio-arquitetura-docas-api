"""Rota do painel: métricas consolidadas da operação."""
from datetime import date

from flask_openapi3 import APIBlueprint, Tag

from database import Session
from model import Pedido
from schemas import PainelSchema
from schemas.pedido import STATUS_ENCERRADOS
from services.fluxo import TRANSICOES

tag_painel = Tag(name="Painel", description="Indicadores da operação de expedição")

bp_painel = APIBlueprint("painel", __name__, abp_tags=[tag_painel])

# Mapeamento UF → região do IBGE, usado no frete médio por região
REGIOES = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
REGIAO_POR_UF = {uf: regiao for regiao, ufs in REGIOES.items() for uf in ufs}


def _media(valores):
    """Média aritmética arredondada a 2 casas; None se a lista estiver vazia."""
    return round(sum(valores) / len(valores), 2) if valores else None


@bp_painel.get("/painel", summary="Indicadores do painel", responses={200: PainelSchema})
def painel():
    """
    Consolida contagem por status, frete médio (geral e por região), pedidos
    atrasados e prazo médio das cotações contratadas.

    "Frete" aqui é sempre o valor da cotação contratada; pedidos cancelados
    ficam fora das médias.
    """
    with Session() as sessao:
        pedidos = sessao.query(Pedido).all()

        # Começa com todos os status zerados para a interface sempre receber as chaves
        contagem = {status: 0 for status in TRANSICOES}
        for pedido in pedidos:
            contagem[pedido.status] = contagem.get(pedido.status, 0) + 1

        contratados = [p for p in pedidos if p.cotacao_contratada and p.status != "cancelado"]

        fretes_por_regiao = {regiao: [] for regiao in REGIOES}
        for pedido in contratados:
            regiao = REGIAO_POR_UF.get(pedido.uf)
            if regiao:
                fretes_por_regiao[regiao].append(pedido.cotacao_contratada.valor)

        hoje = date.today()
        atrasados = sum(
            1 for p in pedidos if p.data_prometida and p.data_prometida < hoje and p.status not in STATUS_ENCERRADOS
        )

        return {
            "total_pedidos": len(pedidos),
            "contagem_por_status": contagem,
            "frete_medio_geral": _media([p.cotacao_contratada.valor for p in contratados]),
            "frete_medio_por_regiao": [
                {"regiao": regiao, "frete_medio": _media(valores) or 0, "quantidade": len(valores)}
                for regiao, valores in fretes_por_regiao.items()
            ],
            "atrasados": atrasados,
            "prazo_medio_contratado": _media([p.cotacao_contratada.prazo_dias_uteis for p in contratados]),
        }, 200
