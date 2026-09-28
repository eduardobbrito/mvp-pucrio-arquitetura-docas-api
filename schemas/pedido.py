"""Schemas de pedido: filtros, resumo para a fila, detalhe, importação e status."""
from datetime import date, datetime

from pydantic import BaseModel, Field

import config
from schemas.cotacao import CotacaoSchema, apresentar_cotacao

# Status em que o pedido já saiu do fluxo e não pode mais "atrasar"
STATUS_ENCERRADOS = ("entregue", "cancelado")


class PedidoPath(BaseModel):
    """Parâmetro de caminho com o id do pedido."""

    pedido_id: int = Field(..., description="Id do pedido na Docas")


class FiltroPedidosQuery(BaseModel):
    """Filtros e paginação da listagem de pedidos (todos opcionais)."""

    status: str | None = Field(None, description="recebido, cotado, contratado, em_transito, entregue ou cancelado")
    uf: str | None = Field(None, description="Sigla do estado de destino, ex.: SP", max_length=2)
    q: str | None = Field(None, description="Busca por nome do cliente, cidade ou id externo")
    pagina: int = Field(1, ge=1, description="Número da página, a partir de 1")
    por_pagina: int = Field(config.POR_PAGINA_PADRAO, ge=1, le=config.POR_PAGINA_MAXIMO, description="Itens por página")


class ItemPedidoSchema(BaseModel):
    """Produto de um pedido com dados físicos (peso em kg, dimensões em cm)."""

    id: int
    produto_id_externo: int
    sku: str | None
    titulo: str
    quantidade: int
    preco_unitario: float
    peso: float
    largura: float
    altura: float
    profundidade: float


class MovimentacaoSchema(BaseModel):
    """Uma mudança de status na linha do tempo do pedido."""

    id: int
    de_status: str | None
    para_status: str
    observacao: str | None
    criado_em: datetime


class PedidoResumoSchema(BaseModel):
    """Dados essenciais de um pedido, usados na fila."""

    id: int
    id_externo: int
    cliente_nome: str
    cidade: str
    uf: str
    quantidade_itens: int = Field(..., description="Soma das quantidades dos itens")
    peso_cobrado: float
    distancia_km: int
    status: str
    data_prometida: date | None
    atrasado: bool = Field(..., description="data_prometida já passou e o pedido não foi entregue nem cancelado")
    valor_frete: float | None = Field(None, description="Valor da cotação contratada, se houver")
    importado_em: datetime


class ListaPedidosSchema(BaseModel):
    """Página de pedidos com metadados de paginação."""

    pedidos: list[PedidoResumoSchema]
    pagina: int
    por_pagina: int
    total: int
    total_paginas: int


class PedidoDetalheSchema(PedidoResumoSchema):
    """Pedido completo: cliente, endereço, pesos, itens, cotações e movimentações."""

    cliente_email: str
    cep: str
    logradouro: str
    numero: str
    bairro: str
    latitude: float | None
    longitude: float | None
    endereco_verificado: bool
    valor_mercadoria: float
    peso_real: float
    peso_cubado: float
    cotacao_contratada_id: int | None
    atualizado_em: datetime
    itens: list[ItemPedidoSchema]
    cotacoes: list[CotacaoSchema]
    movimentacoes: list[MovimentacaoSchema]


class ImportacaoSchema(BaseModel):
    """Resultado da importação de pedidos da DummyJSON."""

    importados: int = Field(..., description="Pedidos novos gravados")
    ignorados: int = Field(..., description="Pedidos que já existiam (importação idempotente)")
    mensagem: str


class AtualizarStatusSchema(BaseModel):
    """Corpo da atualização de status; a máquina de estados valida a transição."""

    status: str = Field(..., description="Novo status: em_transito ou entregue", examples=["em_transito"])
    observacao: str | None = Field(None, max_length=300, description="Observação opcional para o histórico")


def esta_atrasado(pedido):
    """True se a data prometida já passou e o pedido ainda está em andamento."""
    return (
        pedido.data_prometida is not None
        and pedido.data_prometida < date.today()
        and pedido.status not in STATUS_ENCERRADOS
    )


def apresentar_resumo(pedido):
    """Converte um modelo Pedido em dicionário no formato de PedidoResumoSchema."""
    return {
        "id": pedido.id,
        "id_externo": pedido.id_externo,
        "cliente_nome": pedido.cliente_nome,
        "cidade": pedido.cidade,
        "uf": pedido.uf,
        "quantidade_itens": sum(item.quantidade for item in pedido.itens),
        "peso_cobrado": pedido.peso_cobrado,
        "distancia_km": pedido.distancia_km,
        "status": pedido.status,
        "data_prometida": pedido.data_prometida,
        "atrasado": esta_atrasado(pedido),
        "valor_frete": pedido.cotacao_contratada.valor if pedido.cotacao_contratada else None,
        "importado_em": pedido.importado_em,
    }


def apresentar_detalhe(pedido):
    """Converte um modelo Pedido (com relacionamentos) no formato de PedidoDetalheSchema."""
    dados = apresentar_resumo(pedido)
    dados.update(
        {
            "cliente_email": pedido.cliente_email,
            "cep": pedido.cep,
            "logradouro": pedido.logradouro,
            "numero": pedido.numero,
            "bairro": pedido.bairro,
            "latitude": pedido.latitude,
            "longitude": pedido.longitude,
            "endereco_verificado": pedido.endereco_verificado,
            "valor_mercadoria": pedido.valor_mercadoria,
            "peso_real": pedido.peso_real,
            "peso_cubado": pedido.peso_cubado,
            "cotacao_contratada_id": pedido.cotacao_contratada_id,
            "atualizado_em": pedido.atualizado_em,
            "itens": [
                {
                    "id": item.id,
                    "produto_id_externo": item.produto_id_externo,
                    "sku": item.sku,
                    "titulo": item.titulo,
                    "quantidade": item.quantidade,
                    "preco_unitario": item.preco_unitario,
                    "peso": item.peso,
                    "largura": item.largura,
                    "altura": item.altura,
                    "profundidade": item.profundidade,
                }
                for item in pedido.itens
            ],
            "cotacoes": [apresentar_cotacao(c, pedido.cotacao_contratada_id) for c in pedido.cotacoes],
            "movimentacoes": [
                {
                    "id": mov.id,
                    "de_status": mov.de_status,
                    "para_status": mov.para_status,
                    "observacao": mov.observacao,
                    "criado_em": mov.criado_em,
                }
                for mov in pedido.movimentacoes
            ],
        }
    )
    return dados
