"""Modelo Tarifa: uma célula da tabela de frete (faixa de peso × faixa de distância)."""
from sqlalchemy import Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Tarifa(Base):
    """
    Tarifa base de frete.

    Cada linha vale para pedidos com peso cobrado até `peso_max_kg` e distância
    até `distancia_max_km`. A busca escolhe a menor faixa que comporta o pedido.
    Os valores são ilustrativos e editáveis pelas rotas /tarifas.
    """

    __tablename__ = "tarifas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    peso_max_kg: Mapped[float] = mapped_column(Float)
    distancia_max_km: Mapped[int] = mapped_column(Integer)
    valor: Mapped[float] = mapped_column(Float)
    prazo_dias_uteis: Mapped[int] = mapped_column(Integer)

    def __repr__(self):
        """Representação curta para logs e depuração."""
        return f"<Tarifa até {self.peso_max_kg}kg/{self.distancia_max_km}km R${self.valor}>"
