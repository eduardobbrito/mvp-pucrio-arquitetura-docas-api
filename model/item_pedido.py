"""Modelo ItemPedido: cada produto (com quantidade) dentro de um pedido."""
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ItemPedido(Base):
    """
    Item de um pedido, com os dados físicos do produto vindos da DummyJSON.

    Peso em kg e dimensões em cm (unidades assumidas, ver README). São esses
    valores que alimentam o cálculo de peso real e peso cubado do pedido.
    """

    __tablename__ = "itens_pedido"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), nullable=False)
    produto_id_externo: Mapped[int] = mapped_column(Integer)
    sku: Mapped[str | None] = mapped_column(String(50), nullable=True)
    titulo: Mapped[str] = mapped_column(String(200))
    quantidade: Mapped[int] = mapped_column(Integer, default=1)
    preco_unitario: Mapped[float] = mapped_column(Float, default=0)
    peso: Mapped[float] = mapped_column(Float, default=0)
    largura: Mapped[float] = mapped_column(Float, default=0)
    altura: Mapped[float] = mapped_column(Float, default=0)
    profundidade: Mapped[float] = mapped_column(Float, default=0)

    pedido: Mapped["Pedido"] = relationship(back_populates="itens")  # noqa: F821

    def __repr__(self):
        """Representação curta para logs e depuração."""
        return f"<ItemPedido id={self.id} pedido={self.pedido_id} sku={self.sku} qtd={self.quantidade}>"
