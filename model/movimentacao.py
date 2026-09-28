"""Modelo Movimentacao: histórico de mudanças de status de um pedido."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Movimentacao(Base):
    """
    Registro de uma transição de status.

    Toda mudança de status grava uma linha aqui, formando a linha do tempo do
    pedido exibida na interface. `de_status` é nulo na entrada (importação).
    """

    __tablename__ = "movimentacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), nullable=False)
    de_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    para_status: Mapped[str] = mapped_column(String(20))
    observacao: Mapped[str | None] = mapped_column(String(300), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    pedido: Mapped["Pedido"] = relationship(back_populates="movimentacoes")  # noqa: F821

    def __repr__(self):
        """Representação curta para logs e depuração."""
        return f"<Movimentacao pedido={self.pedido_id} {self.de_status} → {self.para_status}>"
