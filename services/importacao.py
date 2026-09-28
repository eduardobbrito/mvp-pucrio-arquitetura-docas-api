"""
Importação de pedidos da DummyJSON.

Orquestra os clientes externos: lê os carts, completa itens (produtos) e
cliente (usuário), sorteia um endereço brasileiro real do seed, confirma o CEP
na BrasilAPI, calcula pesos e distância e grava pedido, itens e a movimentação
inicial. É idempotente: carts já importados (mesmo id_externo) são ignorados.
"""
import config
from database import Session
from logger import logger
from model import ItemPedido, Movimentacao, Pedido
from services import brasilapi, dummyjson
from services.frete import calcular_distancia_km, calcular_pesos
from services.seeds import sortear_endereco


def importar_pedidos(quantidade):
    """
    Importa até `quantidade` carts ainda não existentes no banco.

    Decisão fora do CLAUDE.md: a DummyJSON tem cerca de 200 carts, e importar
    todos de uma vez levaria minutos (várias chamadas externas por pedido). Por
    isso cada chamada traz um lote; chamar de novo traz os próximos.

    Devolve (importados, ignorados), em que ignorados é o número de carts que
    já estavam no banco.
    """
    carts = dummyjson.listar_carts()
    with Session() as sessao:
        existentes = {id_ext for (id_ext,) in sessao.query(Pedido.id_externo).all()}

    novos = [cart for cart in carts if cart["id"] not in existentes][:quantidade]
    ignorados = sum(1 for cart in carts if cart["id"] in existentes)
    cache_produtos = {}  # evita buscar o mesmo produto duas vezes no mesmo lote

    importados = 0
    for cart in novos:
        _importar_cart(cart, cache_produtos)
        importados += 1

    logger.info("Importação concluída: %s novos, %s já existentes", importados, ignorados)
    return importados, ignorados


def _importar_cart(cart, cache_produtos):
    """Transforma um cart da DummyJSON em Pedido com itens e grava no banco."""
    usuario = dummyjson.buscar_usuario(cart["userId"])

    itens = []
    for produto_cart in cart["products"]:
        produto_id = produto_cart["id"]
        if produto_id not in cache_produtos:
            cache_produtos[produto_id] = dummyjson.buscar_produto(produto_id)
        produto = cache_produtos[produto_id]
        dimensoes = produto.get("dimensions") or {}
        # Unidades assumidas: weight em kg e dimensions em cm (documentado no README)
        itens.append(
            {
                "produto_id_externo": produto_id,
                "sku": produto.get("sku"),
                "titulo": produto_cart["title"],
                "quantidade": produto_cart["quantity"],
                "preco_unitario": produto_cart["price"],
                "peso": float(produto.get("weight") or 0),
                "largura": float(dimensoes.get("width") or 0),
                "altura": float(dimensoes.get("height") or 0),
                "profundidade": float(dimensoes.get("depth") or 0),
            }
        )

    endereco, verificado = _definir_endereco()
    peso_real, peso_cubado, peso_cobrado = calcular_pesos(itens)
    distancia = calcular_distancia_km(
        config.ARMAZEM["latitude"], config.ARMAZEM["longitude"], endereco["latitude"], endereco["longitude"]
    )

    pedido = Pedido(
        id_externo=cart["id"],
        cliente_nome=f"{usuario.get('firstName', '')} {usuario.get('lastName', '')}".strip(),
        cliente_email=usuario.get("email", ""),
        cep=endereco["cep"],
        logradouro=endereco["logradouro"],
        numero=endereco["numero"],
        bairro=endereco["bairro"],
        cidade=endereco["cidade"],
        uf=endereco["uf"],
        latitude=endereco["latitude"],
        longitude=endereco["longitude"],
        endereco_verificado=verificado,
        valor_mercadoria=round(cart.get("discountedTotal") or cart.get("total") or 0, 2),
        peso_real=peso_real,
        peso_cubado=peso_cubado,
        peso_cobrado=peso_cobrado,
        distancia_km=distancia,
        status="recebido",
        itens=[ItemPedido(**item) for item in itens],
        movimentacoes=[
            Movimentacao(de_status=None, para_status="recebido", observacao=f"Importado da DummyJSON (cart {cart['id']})")
        ],
    )
    # Grava pedido a pedido: uma falha externa no meio do lote preserva o que já entrou
    with Session() as sessao:
        sessao.add(pedido)
        sessao.commit()


def _definir_endereco():
    """
    Sorteia um endereço do seed e tenta confirmá-lo na BrasilAPI.

    Devolve (endereco, verificado). Se a BrasilAPI falhar, usa o endereço do
    seed como está e marca verificado = False, sem interromper a importação.
    """
    endereco = sortear_endereco()
    confirmado = brasilapi.consultar_cep(endereco["cep"])
    if not confirmado:
        return endereco, False

    # Dados oficiais da BrasilAPI prevalecem; o número vem do seed (CEP não tem número)
    for campo in ("logradouro", "bairro", "cidade", "uf"):
        if confirmado[campo]:
            endereco[campo] = confirmado[campo]
    # Coordenadas: usa as da BrasilAPI quando existirem; senão mantém as do seed
    if confirmado["latitude"] is not None and confirmado["longitude"] is not None:
        endereco["latitude"] = confirmado["latitude"]
        endereco["longitude"] = confirmado["longitude"]
    return endereco, True
