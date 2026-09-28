"""Rotas de tarifas (CRUD da tabela de frete) e listagem de modalidades."""
from flask_openapi3 import APIBlueprint, Tag

from database import Session
from model import Modalidade, Tarifa
from routes.comum import erro
from schemas import (
    ErroSchema,
    ListaModalidadesSchema,
    ListaTarifasSchema,
    TarifaEntradaSchema,
    TarifaPath,
    TarifaRemovidaSchema,
    TarifaSchema,
    apresentar_modalidade,
    apresentar_tarifa,
)

tag_tarifas = Tag(name="Tarifas", description="Tabela de tarifas (ilustrativa e configurável) e modalidades")

bp_tarifas = APIBlueprint("tarifas", __name__, abp_tags=[tag_tarifas])


def _faixa_duplicada(sessao, dados, ignorar_id=None):
    """True se já existe outra tarifa com a mesma faixa de peso e distância."""
    consulta = sessao.query(Tarifa).filter(
        Tarifa.peso_max_kg == dados.peso_max_kg, Tarifa.distancia_max_km == dados.distancia_max_km
    )
    if ignorar_id:
        consulta = consulta.filter(Tarifa.id != ignorar_id)
    return consulta.first() is not None


@bp_tarifas.get("/tarifas", summary="Lista a tabela de tarifas", responses={200: ListaTarifasSchema})
def listar_tarifas():
    """Devolve todas as tarifas ordenadas por faixa de peso e de distância."""
    with Session() as sessao:
        tarifas = sessao.query(Tarifa).order_by(Tarifa.peso_max_kg, Tarifa.distancia_max_km).all()
        return {"tarifas": [apresentar_tarifa(t) for t in tarifas]}, 200


@bp_tarifas.get(
    "/tarifas/<int:tarifa_id>", summary="Detalha uma tarifa", responses={200: TarifaSchema, 404: ErroSchema}
)
def detalhar_tarifa(path: TarifaPath):
    """Devolve uma tarifa pelo id."""
    with Session() as sessao:
        tarifa = sessao.get(Tarifa, path.tarifa_id)
        if not tarifa:
            return erro("Tarifa não encontrada", 404)
        return apresentar_tarifa(tarifa), 200


@bp_tarifas.post(
    "/tarifas",
    summary="Cria uma tarifa",
    responses={201: TarifaSchema, 400: ErroSchema, 409: ErroSchema},
)
def criar_tarifa(body: TarifaEntradaSchema):
    """Cria uma nova célula na tabela; a combinação peso × distância deve ser única."""
    with Session() as sessao:
        if _faixa_duplicada(sessao, body):
            return erro("Já existe uma tarifa para essa faixa de peso e distância", 409)
        tarifa = Tarifa(**body.model_dump())
        sessao.add(tarifa)
        sessao.commit()
        return apresentar_tarifa(tarifa), 201


@bp_tarifas.put(
    "/tarifas/<int:tarifa_id>",
    summary="Edita uma tarifa",
    responses={200: TarifaSchema, 400: ErroSchema, 404: ErroSchema, 409: ErroSchema},
)
def editar_tarifa(path: TarifaPath, body: TarifaEntradaSchema):
    """Atualiza valor, prazo ou faixas de uma tarifa. Não altera cotações já geradas."""
    with Session() as sessao:
        tarifa = sessao.get(Tarifa, path.tarifa_id)
        if not tarifa:
            return erro("Tarifa não encontrada", 404)
        if _faixa_duplicada(sessao, body, ignorar_id=tarifa.id):
            return erro("Já existe uma tarifa para essa faixa de peso e distância", 409)
        for campo, valor in body.model_dump().items():
            setattr(tarifa, campo, valor)
        sessao.commit()
        return apresentar_tarifa(tarifa), 200


@bp_tarifas.delete(
    "/tarifas/<int:tarifa_id>",
    summary="Remove uma tarifa",
    responses={200: TarifaRemovidaSchema, 404: ErroSchema},
)
def remover_tarifa(path: TarifaPath):
    """Remove uma tarifa. Cotações já geradas guardam seus valores e não são afetadas."""
    with Session() as sessao:
        tarifa = sessao.get(Tarifa, path.tarifa_id)
        if not tarifa:
            return erro("Tarifa não encontrada", 404)
        sessao.delete(tarifa)
        sessao.commit()
        return {"id": path.tarifa_id, "mensagem": "Tarifa removida"}, 200


@bp_tarifas.get("/modalidades", summary="Lista as modalidades de frete", responses={200: ListaModalidadesSchema})
def listar_modalidades():
    """Devolve as modalidades (econômico, padrão, expresso) e seus ajustes."""
    with Session() as sessao:
        modalidades = sessao.query(Modalidade).order_by(Modalidade.id).all()
        return {"modalidades": [apresentar_modalidade(m) for m in modalidades]}, 200
