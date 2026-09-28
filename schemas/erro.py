"""Schema de erro padrão das respostas da API."""
from pydantic import BaseModel, Field


class ErroSchema(BaseModel):
    """Corpo devolvido em qualquer erro (400, 404, 409, 502), com mensagem em português."""

    mensagem: str = Field(..., description="Descrição do erro", examples=["Pedido não encontrado"])
