"""
Regras de frete: pesos, distância, busca de tarifa, prazos e cotações.

Todas as funções são puras ou recebem a sessão do banco explicitamente, o que
facilita testá-las isoladamente.
"""
import math
from datetime import date, timedelta

import config
from services.erros import SemTarifa


def calcular_pesos(itens):
    """
    Calcula peso real, peso cubado e peso cobrado de uma lista de itens.

    Cada item é um dicionário com peso (kg), largura, altura, profundidade (cm)
    e quantidade. Devolve (peso_real, peso_cubado, peso_cobrado) em kg.
    """
    # Peso real: soma do peso de cada unidade
    peso_real = sum(item["peso"] * item["quantidade"] for item in itens)
    # Peso cubado: volume total em cm³ dividido pelo fator de cubagem (6000).
    # Representa o "espaço" que a carga ocupa no veículo, convertido em kg.
    volume = sum(item["largura"] * item["altura"] * item["profundidade"] * item["quantidade"] for item in itens)
    peso_cubado = volume / config.FATOR_CUBAGEM
    # A transportadora cobra pelo maior dos dois: carga leve e volumosa paga pelo volume
    peso_cobrado = max(peso_real, peso_cubado)
    return round(peso_real, 2), round(peso_cubado, 2), round(peso_cobrado, 2)


def calcular_distancia_km(lat_origem, lon_origem, lat_destino, lon_destino):
    """
    Distância em linha reta entre dois pontos pela fórmula de haversine, em km inteiros.

    A haversine considera a curvatura da Terra (raio médio de 6371 km), o que é
    suficiente para faixas de distância de frete.
    """
    raio_terra_km = 6371
    # Converte graus para radianos, exigência das funções trigonométricas
    phi1, phi2 = math.radians(lat_origem), math.radians(lat_destino)
    delta_phi = math.radians(lat_destino - lat_origem)
    delta_lambda = math.radians(lon_destino - lon_origem)
    # a = sen²(Δφ/2) + cos φ1 · cos φ2 · sen²(Δλ/2)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    # c é o ângulo central entre os pontos; distância = raio × ângulo
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(raio_terra_km * c)


def buscar_tarifa(sessao, peso_cobrado, distancia_km):
    """
    Encontra a tarifa base para o peso e a distância do pedido.

    Regra: menor peso_max_kg >= peso cobrado e, dentro dessa faixa de peso, menor
    distancia_max_km >= distância. Devolve (tarifa, fator_excedente).

    Decisão fora do CLAUDE.md: muitos carts da DummyJSON passam de 30 kg, a
    maior faixa da tabela. Nesse caso usamos a maior faixa de peso e cobramos
    proporcionalmente ao peso (fator = peso cobrado / peso máximo da faixa),
    em vez de recusar a cotação.
    """
    from model import Tarifa  # import local evita ciclo model ↔ services nos testes

    faixas_peso = sorted({t.peso_max_kg for t in sessao.query(Tarifa).all()})
    if not faixas_peso:
        raise SemTarifa("A tabela de tarifas está vazia")

    # Primeira faixa de peso que comporta o pedido; se nenhuma, a maior (com excedente)
    faixa_peso = next((p for p in faixas_peso if p >= peso_cobrado), faixas_peso[-1])
    fator_excedente = max(1.0, peso_cobrado / faixa_peso)

    tarifa = (
        sessao.query(Tarifa)
        .filter(Tarifa.peso_max_kg == faixa_peso, Tarifa.distancia_max_km >= distancia_km)
        .order_by(Tarifa.distancia_max_km)
        .first()
    )
    if not tarifa:
        raise SemTarifa(f"Nenhuma tarifa cobre {distancia_km} km na faixa de até {faixa_peso:g} kg")
    return tarifa, fator_excedente


def somar_dias_uteis(inicio, dias):
    """
    Soma `dias` dias úteis a uma data, pulando sábados e domingos.

    Feriados estão fora do escopo do MVP. Com 0 dias, devolve a própria data.
    """
    data = inicio
    restantes = dias
    while restantes > 0:
        data += timedelta(days=1)
        # weekday(): segunda = 0 ... sábado = 5, domingo = 6
        if data.weekday() < 5:
            restantes -= 1
    return data


def calcular_prazo(prazo_base, modalidade):
    """
    Aplica os ajustes da modalidade ao prazo base da tarifa.

    prazo = max(prazo_base + ajuste, prazo_minimo), limitado ao prazo máximo
    quando a modalidade define um (expresso: no máximo 3 dias úteis).
    """
    prazo = max(prazo_base + modalidade.ajuste_prazo_dias, modalidade.prazo_minimo_dias)
    if modalidade.prazo_maximo_dias is not None:
        prazo = min(prazo, modalidade.prazo_maximo_dias)
    return prazo


def calcular_cotacoes(sessao, pedido, hoje=None):
    """
    Calcula (sem gravar) uma cotação por modalidade ativa.

    Devolve lista de dicionários com modalidade, valor, prazo_dias_uteis e
    data_prometida. Valor = tarifa × fator de excedente × multiplicador.
    """
    from model import Modalidade

    hoje = hoje or date.today()
    tarifa, fator_excedente = buscar_tarifa(sessao, pedido.peso_cobrado, pedido.distancia_km)
    resultado = []
    for modalidade in sessao.query(Modalidade).filter(Modalidade.ativa.is_(True)).order_by(Modalidade.id):
        valor = round(tarifa.valor * fator_excedente * modalidade.multiplicador_valor, 2)
        prazo = calcular_prazo(tarifa.prazo_dias_uteis, modalidade)
        resultado.append(
            {
                "modalidade": modalidade,
                "valor": valor,
                "prazo_dias_uteis": prazo,
                "data_prometida": somar_dias_uteis(hoje, prazo),
            }
        )
    return resultado


def gerar_cotacoes(sessao, pedido):
    """
    Calcula e grava as cotações do pedido, apagando as anteriores não contratadas.

    Não faz commit: quem chama decide (junto com a transição de status).
    """
    from model import Cotacao

    for antiga in list(pedido.cotacoes):
        if antiga.id != pedido.cotacao_contratada_id:
            pedido.cotacoes.remove(antiga)  # delete-orphan apaga do banco

    novas = []
    for dados in calcular_cotacoes(sessao, pedido):
        cotacao = Cotacao(
            modalidade=dados["modalidade"],
            valor=dados["valor"],
            prazo_dias_uteis=dados["prazo_dias_uteis"],
            data_prometida=dados["data_prometida"],
        )
        pedido.cotacoes.append(cotacao)
        novas.append(cotacao)
    sessao.flush()  # gera os ids das cotações para a resposta
    return novas
