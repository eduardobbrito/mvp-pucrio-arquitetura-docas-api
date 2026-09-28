"""Testes das regras de frete: pesos, distância, dias úteis, tarifas e cotações."""
from datetime import date

import pytest

from model import Modalidade
from services.erros import SemTarifa
from services.frete import (
    buscar_tarifa,
    calcular_cotacoes,
    calcular_distancia_km,
    calcular_pesos,
    calcular_prazo,
    gerar_cotacoes,
    somar_dias_uteis,
)


def item(peso, largura, altura, profundidade, quantidade=1):
    """Monta um item no formato esperado por calcular_pesos."""
    return {"peso": peso, "largura": largura, "altura": altura, "profundidade": profundidade, "quantidade": quantidade}


def test_peso_cobrado_usa_peso_real_quando_carga_e_densa():
    """Carga pesada e pequena: o peso real vence o cubado."""
    # volume = 10×10×10×2 = 2000 cm³ → cubado = 2000/6000 = 0,33 kg
    real, cubado, cobrado = calcular_pesos([item(5, 10, 10, 10, quantidade=2)])
    assert real == 10
    assert cubado == 0.33
    assert cobrado == 10


def test_peso_cobrado_usa_peso_cubado_quando_carga_e_volumosa():
    """Carga leve e grande: o peso cubado vence o real."""
    # volume = 60×40×50 = 120000 cm³ → cubado = 20 kg
    real, cubado, cobrado = calcular_pesos([item(1, 60, 40, 50)])
    assert (real, cubado, cobrado) == (1, 20, 20)


def test_distancia_rio_sao_paulo_por_haversine():
    """Centro do Rio até a Avenida Paulista fica perto de 360 km em linha reta."""
    distancia = calcular_distancia_km(-22.90642, -43.18223, -23.5617698, -46.6553299)
    assert 350 <= distancia <= 370


def test_distancia_mesmo_ponto_e_zero():
    """Origem e destino iguais resultam em 0 km."""
    assert calcular_distancia_km(-22.9, -43.1, -22.9, -43.1) == 0


def test_dias_uteis_pula_fim_de_semana():
    """Sexta + 1 dia útil = segunda; sexta + 5 dias úteis = sexta seguinte."""
    sexta = date(2026, 10, 2)
    assert somar_dias_uteis(sexta, 1) == date(2026, 10, 5)
    assert somar_dias_uteis(sexta, 5) == date(2026, 10, 9)
    assert somar_dias_uteis(sexta, 0) == sexta


def test_busca_menor_faixa_que_comporta_o_pedido(sessao):
    """2 kg a 690 km cai na faixa 'até 3 kg' × 'até 1500 km' (R$ 42, 5 dias)."""
    tarifa, fator = buscar_tarifa(sessao, 2, 690)
    assert (tarifa.peso_max_kg, tarifa.distancia_max_km) == (3, 1500)
    assert (tarifa.valor, tarifa.prazo_dias_uteis) == (42, 5)
    assert fator == 1


def test_peso_no_limite_da_faixa_fica_na_faixa(sessao):
    """Exatamente 3 kg e 500 km ainda cabem nas faixas 'até 3 kg' e 'até 500 km'."""
    tarifa, _ = buscar_tarifa(sessao, 3, 500)
    assert (tarifa.peso_max_kg, tarifa.distancia_max_km) == (3, 500)


def test_peso_acima_da_maior_faixa_cobra_excedente(sessao):
    """75 kg usa a faixa de 30 kg com fator 75/30 = 2,5."""
    tarifa, fator = buscar_tarifa(sessao, 75, 128)
    assert tarifa.peso_max_kg == 30
    assert fator == 2.5


def test_tabela_vazia_lanca_sem_tarifa(sessao):
    """Sem nenhuma tarifa cadastrada, a cotação é recusada."""
    from model import Tarifa

    sessao.query(Tarifa).delete()
    with pytest.raises(SemTarifa):
        buscar_tarifa(sessao, 1, 10)


def test_prazo_das_modalidades(sessao):
    """Econômico soma 4 dias; expresso tira 2, com mínimo 1 e máximo 3."""
    modalidades = {m.codigo: m for m in sessao.query(Modalidade)}
    assert calcular_prazo(5, modalidades["economico"]) == 9
    assert calcular_prazo(5, modalidades["padrao"]) == 5
    assert calcular_prazo(10, modalidades["expresso"]) == 3  # 10 − 2 = 8, limitado a 3
    assert calcular_prazo(1, modalidades["expresso"]) == 1  # 1 − 2 = −1, elevado ao mínimo 1


def test_cotacoes_do_exemplo_do_readme(sessao, novo_pedido):
    """Reproduz o exemplo numérico do README: 2 kg a 690 km."""
    pedido = novo_pedido(peso_cobrado=2, distancia_km=690)
    segunda = date(2026, 9, 28)
    cotacoes = {c["modalidade"].codigo: c for c in calcular_cotacoes(sessao, pedido, hoje=segunda)}
    assert (cotacoes["economico"]["valor"], cotacoes["economico"]["prazo_dias_uteis"]) == (29.4, 9)
    assert (cotacoes["padrao"]["valor"], cotacoes["padrao"]["prazo_dias_uteis"]) == (42, 5)
    assert (cotacoes["expresso"]["valor"], cotacoes["expresso"]["prazo_dias_uteis"]) == (79.8, 3)
    assert cotacoes["padrao"]["data_prometida"] == date(2026, 10, 5)


def test_modalidade_inativa_nao_gera_cotacao(sessao, novo_pedido):
    """Desativar uma modalidade tira ela das cotações."""
    sessao.query(Modalidade).filter_by(codigo="expresso").update({"ativa": False})
    pedido = novo_pedido()
    codigos = [c["modalidade"].codigo for c in calcular_cotacoes(sessao, pedido)]
    assert codigos == ["economico", "padrao"]


def test_cotar_de_novo_substitui_as_cotacoes(sessao, novo_pedido):
    """Gerar cotações duas vezes mantém só as da última geração."""
    pedido = novo_pedido()
    gerar_cotacoes(sessao, pedido)
    sessao.commit()
    gerar_cotacoes(sessao, pedido)
    sessao.commit()
    assert len(pedido.cotacoes) == 3
