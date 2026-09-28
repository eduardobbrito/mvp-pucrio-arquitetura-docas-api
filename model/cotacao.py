"""Modelo Cotacao: preço e prazo de frete de um pedido em uma modalidade."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Cotacao(Base):
    """
    Cotação gerada para um pedido em uma modalidade.

    Um pedido cotado tem uma cotação por modalidade ativa; ao contratar, o
    pedido passa a apontar para uma delas (cotacao_contratada_id).
    """

    __tablename__ = "cotacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), nullable=False)
    modalidade_id: Mapped[int] = mapped_column(ForeignKey("modalidades.id"), nullable=False)
    valor: Mapped[float] = mapped_column(Float)
    prazo_dias_uteis: Mapped[int] = mapped_column(Integer)
    data_prometida: Mapped[date] = mapped_column(Date)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # foreign_keys explícito: há duas ligações entre pedidos e cotacoes
    pedido: Mapped["Pedido"] = relationship(back_populates="cotacoes", foreign_keys=[pedido_id])  # noqa: F821
    modalidade: Mapped["Modalidade"] = relationship()  # noqa: F821

    def __repr__(self):
        """Representação curta para logs e depuração."""
        return f"<Cotacao id={self.id} pedido={self.pedido_id} R${self.valor} {self.prazo_dias_uteis}d>"
