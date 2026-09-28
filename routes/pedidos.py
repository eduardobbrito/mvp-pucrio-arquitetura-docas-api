"""
Rotas de pedidos: importação, listagem, detalhe, cotação, status e cancelamento.
"""
import math

from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field
from sqlalchemy import or_

from database import Session
from logger import logger
from model import Pedido
from routes.comum import erro
from schemas import (
    AtualizarStatusSchema,
    ErroSchema,
    FiltroPedidosQuery,
    ImportacaoSchema,
    ListaCotacoesSchema,
    ListaPedidosSchema,
    PedidoDetalheSchema,
    PedidoPath,
    apresentar_cotacao,
    apresentar_detalhe,
    apresentar_resumo,
)
from services.erros import ErroApiExterna, SemTarifa, TransicaoInvalida
from services.fluxo import transitar
from services.frete import gerar_cotacoes
from services.importacao import importar_pedidos

tag_pedidos = Tag(name="Pedidos", description="Importação, consulta e fluxo de status dos pedidos")

bp_pedidos = APIBlueprint("pedidos", __name__, abp_tags=[tag_pedidos])


class ImportarQuery(BaseModel):
    """Tamanho do lote de importação."""

    quantidade: int = Field(10, ge=1, le=50, description="Máximo de pedidos novos a importar nesta chamada")


@bp_pedidos.post(
    "/pedidos/importar",
    summary="Importa pedidos da DummyJSON",
    responses={200: ImportacaoSchema, 502: ErroSchema},
)
def importar(query: ImportarQuery):
    """
    Importa um lote de carts da DummyJSON como pedidos.

    Pedidos já existentes são ignorados (idempotência por id_externo). Cada
    pedido novo recebe um endereço real confirmado na BrasilAPI.
    """
    try:
        importados, ignorados = importar_pedidos(query.quantidade)
    except ErroApiExterna as falha:
        return erro(str(falha), 502)
    logger.info("POST /pedidos/importar: %s importados", importados)
    if importados == 0:
        mensagem = "Nenhum pedido novo na loja"
    else:
        mensagem = f"{importados} pedido(s) importado(s)"
    return {"importados": importados, "ignorados": ignorados, "mensagem": mensagem}, 200


@bp_pedidos.get(
    "/pedidos",
    summary="Lista pedidos com filtros e paginação",
    responses={200: ListaPedidosSchema, 400: ErroSchema},
)
def listar(query: FiltroPedidosQuery):
    """
    Lista pedidos do mais recente para o mais antigo.

    Filtros opcionais: status, uf e busca livre `q` (nome do cliente, cidade ou
    id externo). A paginação devolve também o total e o número de páginas.
    """
    with Session() as sessao:
        consulta = sessao.query(Pedido)
        if query.status:
            consulta = consulta.filter(Pedido.status == query.status)
        if query.uf:
            consulta = consulta.filter(Pedido.uf == query.uf.upper())
        if query.q:
            termo = f"%{query.q.strip()}%"
            condicoes = [Pedido.cliente_nome.ilike(termo), Pedido.cidade.ilike(termo)]
            # Se a busca for numérica, também procura pelo id do cart
            if query.q.strip().isdigit():
                condicoes.append(Pedido.id_externo == int(query.q.strip()))
            consulta = consulta.filter(or_(*condicoes))

        total = consulta.count()
        pedidos = (
            consulta.order_by(Pedido.id.desc())
            .offset((query.pagina - 1) * query.por_pagina)
            .limit(query.por_pagina)
            .all()
        )
        # math.ceil: 21 pedidos com 10 por página = 3 páginas
        total_paginas = max(1, math.ceil(total / query.por_pagina))
        return {
            "pedidos": [apresentar_resumo(p) for p in pedidos],
            "pagina": query.pagina,
            "por_pagina": query.por_pagina,
            "total": total,
            "total_paginas": total_paginas,
        }, 200


@bp_pedidos.get(
    "/pedidos/<int:pedido_id>",
    summary="Detalha um pedido",
    responses={200: PedidoDetalheSchema, 404: ErroSchema},
)
def detalhar(path: PedidoPath):
    """Devolve o pedido com itens, cotações e movimentações (linha do tempo)."""
    with Session() as sessao:
        pedido = sessao.get(Pedido, path.pedido_id)
        if not pedido:
            return erro("Pedido não encontrado", 404)
        return apresentar_detalhe(pedido), 200


@bp_pedidos.post(
    "/pedidos/<int:pedido_id>/cotacoes",
    summary="Gera cotações de frete para o pedido",
    responses={201: ListaCotacoesSchema, 404: ErroSchema, 409: ErroSchema},
)
def cotar(path: PedidoPath):
    """
    Calcula uma cotação por modalidade ativa e move o pedido de recebido para cotado.

    Um pedido já cotado pode ser cotado de novo (por exemplo, após editar a
    tabela de tarifas): as cotações anteriores não contratadas são substituídas.
    """
    with Session() as sessao:
        pedido = sessao.get(Pedido, path.pedido_id)
        if not pedido:
            return erro("Pedido não encontrado", 404)
        if pedido.status not in ("recebido", "cotado"):
            return erro(f"Não é possível cotar um pedido com status '{pedido.status}'", 409)
        try:
            cotacoes = gerar_cotacoes(sessao, pedido)
            if pedido.status == "recebido":
                transitar(sessao, pedido, "cotado", f"{len(cotacoes)} cotação(ões) gerada(s)")
        except (SemTarifa, TransicaoInvalida) as falha:
            sessao.rollback()
            return erro(str(falha), 409)
        sessao.commit()
        return {"cotacoes": [apresentar_cotacao(c) for c in cotacoes]}, 201


@bp_pedidos.put(
    "/pedidos/<int:pedido_id>/status",
    summary="Avança o status do pedido",
    responses={200: PedidoDetalheSchema, 400: ErroSchema, 404: ErroSchema, 409: ErroSchema},
)
def atualizar_status(path: PedidoPath, body: AtualizarStatusSchema):
    """
    Muda o status conforme a máquina de estados (ex.: contratado → em_transito).

    Transições fora das regras retornam 409. Para cotar, contratar ou cancelar
    use as rotas específicas, que também gravam cotações e datas.
    """
    with Session() as sessao:
        pedido = sessao.get(Pedido, path.pedido_id)
        if not pedido:
            return erro("Pedido não encontrado", 404)
        # Estes status têm rota própria porque exigem dados além da troca de status
        if body.status in ("cotado", "contratado", "cancelado"):
            rota = {
                "cotado": "POST /pedidos/{id}/cotacoes",
                "contratado": "PUT /cotacoes/{id}/contratar",
                "cancelado": "DELETE /pedidos/{id}",
            }[body.status]
            return erro(f"Para mudar para '{body.status}' use {rota}", 409)
        try:
            transitar(sessao, pedido, body.status, body.observacao)
        except TransicaoInvalida as falha:
            return erro(str(falha), 409)
        sessao.commit()
        return apresentar_detalhe(pedido), 200


@bp_pedidos.delete(
    "/pedidos/<int:pedido_id>",
    summary="Cancela o pedido",
    responses={200: PedidoDetalheSchema, 404: ErroSchema, 409: ErroSchema},
)
def cancelar(path: PedidoPath):
    """
    Cancela o pedido (exclusão lógica: o registro e o histórico são mantidos).

    Só é permitido antes de em_transito; depois disso retorna 409.
    """
    with Session() as sessao:
        pedido = sessao.get(Pedido, path.pedido_id)
        if not pedido:
            return erro("Pedido não encontrado", 404)
        try:
            transitar(sessao, pedido, "cancelado", "Pedido cancelado pelo operador")
        except TransicaoInvalida as falha:
            return erro(str(falha), 409)
        sessao.commit()
        return apresentar_detalhe(pedido), 200
