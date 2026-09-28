"""Exceções de negócio compartilhadas pelos serviços da API Docas."""


class ErroApiExterna(Exception):
    """Falha ao consultar uma API externa (timeout, rede ou resposta inválida). Vira HTTP 502."""


class TransicaoInvalida(Exception):
    """Mudança de status não permitida pela máquina de estados. Vira HTTP 409."""


class SemTarifa(Exception):
    """Nenhuma tarifa cadastrada comporta o pedido. Vira HTTP 409."""
