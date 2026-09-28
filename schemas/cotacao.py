"""Schemas de cotação de frete."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class CotacaoPath(BaseModel):
    """Parâmetro de caminho com o id da cotação."""

    cotacao_id: int = Field(..., description="Id da cotação")


class CotacaoSchema(BaseModel):
    """Uma cotação: valor e prazo de frete em uma modalidade."""

    id: int
    pedido_id: int
    modalidade_codigo: str = Field(..., examples=["padrao"])
    modalidade_nome: str = Field(..., examples=["Padrão"])
    valor: float = Field(..., description="Valor do frete em reais", examples=[42.0])
    prazo_dias_uteis: int = Field(..., examples=[5])
    data_prometida: date
    criado_em: datetime
    contratada: bool = Field(..., description="True se esta é a cotação contratada do pedido")


class ListaCotacoesSchema(BaseModel):
    """Cotações geradas para um pedido (uma por modalidade ativa)."""

    cotacoes: list[CotacaoSchema]


def apresentar_cotacao(cotacao, id_contratada=None):
    """Converte um modelo Cotacao em dicionário no formato de CotacaoSchema."""
    return {
        "id": cotacao.id,
        "pedido_id": cotacao.pedido_id,
        "modalidade_codigo": cotacao.modalidade.codigo,
        "modalidade_nome": cotacao.modalidade.nome,
        "valor": cotacao.valor,
        "prazo_dias_uteis": cotacao.prazo_dias_uteis,
        "data_prometida": cotacao.data_prometida,
        "criado_em": cotacao.criado_em,
        "contratada": cotacao.id == id_contratada,
    }
