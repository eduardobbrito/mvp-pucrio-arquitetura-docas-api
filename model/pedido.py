"""Modelo Pedido: um pedido da loja a ser expedido pelo armazém."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Pedido(Base):
    """
    Pedido importado da loja (DummyJSON) e enriquecido com endereço brasileiro.

    Guarda os dados do cliente, o endereço de entrega, os pesos usados no frete
    (real, cubado e cobrado), a distância até o armazém e o status no fluxo
    recebido → cotado → contratado → em_transito → entregue (ou cancelado).
    """

    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Id do cart na DummyJSON; único para garantir importação idempotente
    id_externo: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    cliente_nome: Mapped[str] = mapped_column(String(200))
    cliente_email: Mapped[str] = mapped_column(String(200))

    cep: Mapped[str] = mapped_column(String(8))
    logradouro: Mapped[str] = mapped_column(String(200))
    numero: Mapped[str] = mapped_column(String(20))
    bairro: Mapped[str] = mapped_column(String(100))
    cidade: Mapped[str] = mapped_column(String(100))
    uf: Mapped[str] = mapped_column(String(2), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    # False quando a BrasilAPI falhou e usamos o endereço do seed como fallback
    endereco_verificado: Mapped[bool] = mapped_column(Boolean, default=False)

    valor_mercadoria: Mapped[float] = mapped_column(Float, default=0)
    peso_real: Mapped[float] = mapped_column(Float, default=0)
    peso_cubado: Mapped[float] = mapped_column(Float, default=0)
    peso_cobrado: Mapped[float] = mapped_column(Float, default=0)
    distancia_km: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(20), default="recebido", index=True)
    # use_alter evita dependência circular na criação das tabelas pedidos ↔ cotacoes
    cotacao_contratada_id: Mapped[int | None] = mapped_column(
        ForeignKey("cotacoes.id", use_alter=True, name="fk_pedido_cotacao_contratada"), nullable=True
    )
    data_prometida: Mapped[date | None] = mapped_column(Date, nullable=True)

    importado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relacionamento 1:N com os itens; apagar o pedido apaga os itens
    itens: Mapped[list["ItemPedido"]] = relationship(  # noqa: F821
        back_populates="pedido", cascade="all, delete-orphan"
    )

    # Todas as cotações geradas (uma por modalidade); foreign_keys desfaz a ambiguidade
    cotacoes: Mapped[list["Cotacao"]] = relationship(  # noqa: F821
        back_populates="pedido", cascade="all, delete-orphan", foreign_keys="Cotacao.pedido_id"
    )
    # A cotação escolhida pelo operador (nula até a contratação)
    cotacao_contratada: Mapped["Cotacao | None"] = relationship(  # noqa: F821
        foreign_keys=[cotacao_contratada_id], post_update=True
    )
    # Histórico de status em ordem cronológica
    movimentacoes: Mapped[list["Movimentacao"]] = relationship(  # noqa: F821
        back_populates="pedido", cascade="all, delete-orphan", order_by="Movimentacao.id"
    )

    def __repr__(self):
        """Representação curta para logs e depuração."""
        return f"<Pedido id={self.id} externo={self.id_externo} status={self.status}>"
