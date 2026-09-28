"""Schemas do painel de métricas."""
from pydantic import BaseModel, Field


class FreteRegiaoSchema(BaseModel):
    """Frete médio contratado em uma região do Brasil."""

    regiao: str = Field(..., examples=["Sudeste"])
    frete_medio: float
    quantidade: int = Field(..., description="Pedidos com frete contratado na região")


class PainelSchema(BaseModel):
    """Métricas consolidadas da operação."""

    total_pedidos: int
    contagem_por_status: dict[str, int] = Field(..., description="Quantidade de pedidos em cada status")
    frete_medio_geral: float | None = Field(None, description="Média dos fretes contratados, em reais")
    frete_medio_por_regiao: list[FreteRegiaoSchema]
    atrasados: int = Field(..., description="Pedidos com data prometida vencida e não entregues/cancelados")
    prazo_medio_contratado: float | None = Field(None, description="Média de dias úteis das cotações contratadas")
