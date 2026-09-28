"""Modelo Modalidade: variações de serviço de frete (econômico, padrão, expresso)."""
from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Modalidade(Base):
    """
    Modalidade de frete aplicada sobre a tarifa base.

    - multiplicador_valor: multiplica o valor da tarifa (ex.: 0,7 no econômico);
    - ajuste_prazo_dias: soma ao prazo base (ex.: +4 no econômico, −2 no expresso);
    - prazo_minimo_dias: piso do prazo final (ex.: 1 no expresso);
    - prazo_maximo_dias: teto opcional do prazo final (ex.: 3 no expresso).
      Campo acrescentado ao modelo do CLAUDE.md para representar a regra
      "expresso com prazo máximo de 3 dias"; nulo significa sem teto.
    """

    __tablename__ = "modalidades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(50))
    multiplicador_valor: Mapped[float] = mapped_column(Float, default=1.0)
    ajuste_prazo_dias: Mapped[int] = mapped_column(Integer, default=0)
    prazo_minimo_dias: Mapped[int] = mapped_column(Integer, default=1)
    prazo_maximo_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self):
        """Representação curta para logs e depuração."""
        return f"<Modalidade {self.codigo} x{self.multiplicador_valor}>"
