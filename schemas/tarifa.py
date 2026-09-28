"""Schemas de tarifas e modalidades de frete."""
from pydantic import BaseModel, Field


class TarifaPath(BaseModel):
    """Parâmetro de caminho com o id da tarifa."""

    tarifa_id: int = Field(..., description="Id da tarifa")


class TarifaEntradaSchema(BaseModel):
    """Dados para criar ou editar uma tarifa (célula peso × distância da tabela)."""

    peso_max_kg: float = Field(..., gt=0, description="Limite superior da faixa de peso, em kg", examples=[3])
    distancia_max_km: int = Field(..., gt=0, description="Limite superior da faixa de distância, em km", examples=[500])
    valor: float = Field(..., gt=0, description="Valor base do frete em reais", examples=[30.0])
    prazo_dias_uteis: int = Field(..., ge=0, description="Prazo base em dias úteis", examples=[3])


class TarifaSchema(TarifaEntradaSchema):
    """Tarifa gravada, com id."""

    id: int


class ListaTarifasSchema(BaseModel):
    """Tabela completa de tarifas, ordenada por peso e distância."""

    tarifas: list[TarifaSchema]


class TarifaRemovidaSchema(BaseModel):
    """Confirmação de remoção de tarifa."""

    id: int
    mensagem: str


class ModalidadeSchema(BaseModel):
    """Modalidade de frete e seus ajustes sobre a tarifa base."""

    id: int
    codigo: str
    nome: str
    multiplicador_valor: float
    ajuste_prazo_dias: int
    prazo_minimo_dias: int
    prazo_maximo_dias: int | None
    ativa: bool


class ListaModalidadesSchema(BaseModel):
    """Modalidades cadastradas."""

    modalidades: list[ModalidadeSchema]


def apresentar_tarifa(tarifa):
    """Converte um modelo Tarifa no formato de TarifaSchema."""
    return {
        "id": tarifa.id,
        "peso_max_kg": tarifa.peso_max_kg,
        "distancia_max_km": tarifa.distancia_max_km,
        "valor": tarifa.valor,
        "prazo_dias_uteis": tarifa.prazo_dias_uteis,
    }


def apresentar_modalidade(modalidade):
    """Converte um modelo Modalidade no formato de ModalidadeSchema."""
    return {
        "id": modalidade.id,
        "codigo": modalidade.codigo,
        "nome": modalidade.nome,
        "multiplicador_valor": modalidade.multiplicador_valor,
        "ajuste_prazo_dias": modalidade.ajuste_prazo_dias,
        "prazo_minimo_dias": modalidade.prazo_minimo_dias,
        "prazo_maximo_dias": modalidade.prazo_maximo_dias,
        "ativa": modalidade.ativa,
    }
