# Docas API

**Docas** é um serviço de expedição e cotação de frete para lojas online. Esta API importa pedidos de uma loja (simulada pela DummyJSON), enriquece cada pedido com um endereço brasileiro real confirmado na BrasilAPI, calcula cotações de frete a partir de uma tabela de tarifas própria e acompanha o pedido pelo fluxo:

`recebido → cotado → contratado → em_transito → entregue` (com `cancelado` como saída antes de `em_transito`).

Este repositório é a **segunda componente** (API REST em Python) do MVP da disciplina de Arquitetura de Software da pós-graduação em Engenharia de Software da PUC-Rio. A componente principal é a interface web: [mvp-pucrio-arquitetura-docas-front](https://github.com/eduardobbrito/mvp-pucrio-arquitetura-docas-front).

## Como rodar a API e a interface

Clone os dois repositórios lado a lado na mesma pasta:

```bash
git clone https://github.com/eduardobbrito/mvp-pucrio-arquitetura-docas-api.git
git clone https://github.com/eduardobbrito/mvp-pucrio-arquitetura-docas-front.git
```

### Opção 1 — docker-compose (as duas componentes de uma vez)

```bash
cd mvp-pucrio-arquitetura-docas-api
docker compose up --build
```

### Opção 2 — Docker, um container por componente

Terminal 1 (API):

```bash
cd mvp-pucrio-arquitetura-docas-api
docker build -t docas-api .
docker run -p 5000:5000 docas-api
```

Terminal 2 (interface):

```bash
cd mvp-pucrio-arquitetura-docas-front
docker build --build-arg VITE_API_URL=http://localhost:5000 -t docas-front .
docker run -p 3000:80 docas-front
```

### Opção 3 — local, sem Docker (Python 3.12 e Node 20.19+)

Terminal 1 (API):

```bash
cd mvp-pucrio-arquitetura-docas-api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Terminal 2 (interface):

```bash
cd mvp-pucrio-arquitetura-docas-front
npm install
cp .env.example .env
npm run dev
```

| | Docker (opções 1 e 2) | Local (opção 3) |
|---|---|---|
| Interface | http://localhost:3000 | http://localhost:5173 |
| API / Swagger | http://localhost:5000/openapi | http://localhost:5000/openapi |

## Arquitetura

![Fluxograma da arquitetura](docs/arquitetura.png)

- A **interface** (React) roda no navegador e conversa apenas com a **API Docas**, por REST/JSON.
- A **API Docas** (Flask + flask-openapi3) concentra as regras de negócio, persiste os dados em **SQLite** via SQLAlchemy e é a única que consome as **APIs externas**.
- A fonte do diagrama está em [`docs/arquitetura.mmd`](docs/arquitetura.mmd) (Mermaid).

Stack: Python 3.12, Flask, flask-openapi3 (Swagger, ReDoc e RapiDoc gerados dos schemas Pydantic), Pydantic 2, SQLAlchemy 2, SQLite, requests, flask-cors e gunicorn.

## APIs externas

| API | URL | Licença | Cadastro/chave | Rotas usadas |
|---|---|---|---|---|
| DummyJSON | https://dummyjson.com | Gratuita, de uso público (projeto open source) | Não exige | `GET /carts?limit=0`, `GET /products/{id}`, `GET /users/{id}` |
| BrasilAPI | https://brasilapi.com.br | MIT | Não exige | `GET /api/cep/v2/{cep}` |

**DummyJSON** simula a loja: cada *cart* vira um pedido. De `/products/{id}` usamos `weight`, `dimensions {width, height, depth}` e `sku`; de `/users/{id}`, nome e e-mail do cliente. **Unidades assumidas:** `weight` em **kg** e `dimensions` em **cm** (a DummyJSON não documenta as unidades). Usamos apenas rotas de leitura, porque as de escrita da DummyJSON não persistem.

**BrasilAPI** confirma o endereço (logradouro, bairro, cidade, UF) e fornece as coordenadas usadas no cálculo da distância. Como os usuários da DummyJSON não têm endereço brasileiro, cada pedido recebe um endereço real sorteado de [`seeds/enderecos.json`](seeds/enderecos.json) (30 CEPs de todas as regiões), que então é confirmado na BrasilAPI. Os CEPs e logradouros são reais; os números são ilustrativos.

Toda chamada externa tem `timeout`, `User-Agent` identificando o projeto e tratamento de erro:
- Se a **DummyJSON** falhar, a importação responde **502** com a mensagem do erro.
- Se a **BrasilAPI** falhar, a importação continua: usa o endereço do seed e marca `endereco_verificado = false`.
- No startup, a API tenta obter as coordenadas do armazém (Praia de Botafogo, 300, Rio de Janeiro/RJ, CEP 22250-040) na BrasilAPI. Se a consulta falhar, mantém o padrão definido em `config.py`.

## Rotas

Documentação interativa: **http://localhost:5000/openapi** (escolha Swagger, ReDoc ou RapiDoc).

| Método | Rota | Descrição |
|---|---|---|
| POST | `/pedidos/importar?quantidade=10` | Importa um lote de pedidos novos da DummyJSON (idempotente) |
| GET | `/pedidos?status=&uf=&q=&pagina=&por_pagina=` | Lista com filtros e paginação |
| GET | `/pedidos/{id}` | Detalhe com itens, cotações e movimentações |
| POST | `/pedidos/{id}/cotacoes` | Gera cotações (recebido → cotado) |
| PUT | `/cotacoes/{id}/contratar` | Contrata a cotação (cotado → contratado) |
| PUT | `/pedidos/{id}/status` | Avança o status: `{"status": "em_transito"}` ou `{"status": "entregue"}` |
| DELETE | `/pedidos/{id}` | Cancela o pedido (exclusão lógica, mantém o histórico) |
| GET / POST | `/tarifas` | Lista e cria tarifas |
| GET / PUT / DELETE | `/tarifas/{id}` | Detalha, edita e remove uma tarifa |
| GET | `/modalidades` | Lista as modalidades de frete |
| GET | `/painel` | Contagem por status, frete médio (geral e por região), atrasados, prazo médio |
| GET | `/` | Redireciona para `/openapi` |

Os erros seguem o formato `{"mensagem": "..."}`: **400** para dados inválidos, **404** para recurso não encontrado, **409** para transição de status inválida e **502** para falha em API externa.

**Transições permitidas** (qualquer outra retorna 409): `recebido → cotado`, `cotado → contratado`, `contratado → em_transito`, `em_transito → entregue`, e `recebido | cotado | contratado → cancelado`. Toda transição grava uma linha em `movimentacoes`.

## Regras de cotação

1. **Peso cobrado.** `peso_real = Σ peso × quantidade` e `peso_cubado = Σ (largura × altura × profundidade × quantidade) / 6000`. O peso cobrado é o maior dos dois.
2. **Distância.** Fórmula de haversine entre o armazém e as coordenadas do destino, em km inteiros.
3. **Tarifa base.** Menor faixa de peso que comporta o peso cobrado e, dentro dela, a menor faixa de distância que comporta a distância. Acima de 30 kg (a maior faixa), usa-se a faixa de 30 kg com valor proporcional ao peso (`valor × peso_cobrado / 30`).
4. **Modalidades**, uma cotação para cada modalidade ativa:

| Modalidade | Valor | Prazo |
|---|---|---|
| Econômico | tarifa × 0,7 | prazo base + 4 dias úteis |
| Padrão | tarifa × 1,0 | prazo base |
| Expresso | tarifa × 1,9 | prazo base − 2, no mínimo 1 e no máximo 3 dias úteis |

5. **Data prometida** = hoje + prazo em dias úteis (pula sábados e domingos; feriados ficam fora do escopo).

Cotar de novo um pedido já cotado substitui as cotações anteriores.

**Exemplo numérico.** Pedido com peso real de 2 kg e peso cubado de 1,4 kg, a 690 km do armazém:
- peso cobrado = max(2; 1,4) = **2 kg** → faixa "até 3 kg"; 690 km → faixa "até 1500 km"
- tarifa base: **R$ 42,00** e **5 dias úteis**
- Econômico: 42 × 0,7 = **R$ 29,40**, 5 + 4 = **9 dias úteis**
- Padrão: **R$ 42,00**, **5 dias úteis**
- Expresso: 42 × 1,9 = **R$ 79,80**, 5 − 2 = **3 dias úteis**

> ⚠️ **A tabela de tarifas é ilustrativa e configurável.** Os valores iniciais (4 faixas de peso × 5 faixas de distância, em [`seeds/tarifas.json`](seeds/tarifas.json)) não correspondem a nenhuma transportadora real. Eles podem ser editados pelas rotas `/tarifas`. A carga inicial só acontece quando a tabela está vazia, então as edições não são sobrescritas.

## Execução local

Requer Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # opcional: FRONT_URL (CORS) e PORTA
python app.py
```

A API sobe em http://localhost:5000 e o Swagger fica em **http://localhost:5000/openapi**. O banco `database/docas.sqlite3` é criado no primeiro startup, já com modalidades e tarifas.

Variáveis de ambiente (ver `.env.example`):
- `FRONT_URL`: origens autorizadas no CORS, separadas por vírgula (padrão: `http://localhost:3000,http://localhost:5173`).
- `PORTA`: porta do `python app.py` (padrão: `5000`).
- `URL_BANCO`: URL do banco SQLite (padrão: `database/docas.sqlite3`). É usada pelo docker-compose para gravar o banco em um volume.

## Execução com Docker

```bash
docker build -t docas-api .
docker run -p 5000:5000 docas-api
```

Para manter o banco entre execuções, aponte o SQLite para uma pasta fora do código e monte um volume nela:

```bash
docker run -p 5000:5000 -e URL_BANCO=sqlite:////app/dados/docas.sqlite3 -v docas-dados:/app/dados docas-api
```

## Execução com docker-compose

O `docker-compose.yml` deste repositório sobe a API e a interface juntas. Os dois repositórios precisam estar clonados lado a lado na mesma pasta:

```
pasta/
├── mvp-pucrio-arquitetura-docas-api/
└── mvp-pucrio-arquitetura-docas-front/
```

Dentro de `mvp-pucrio-arquitetura-docas-api`:

```bash
docker compose up --build
```

- Interface: **http://localhost:3000**
- API e Swagger: **http://localhost:5000/openapi**

O banco fica no volume `docas-dados` e sobrevive a reinícios e rebuilds. Para apagar os dados e recomeçar do zero, use `docker compose down -v`.

## Testes

Os testes cobrem as regras de frete (pesos, haversine, dias úteis, faixas, excedente, modalidades) e a máquina de estados. Eles usam um banco SQLite em memória e não acessam a rede.

```bash
pytest
```

## Estrutura

```
app.py            aplicação flask-openapi3, CORS e registro dos blueprints
config.py         URLs externas, armazém, paginação, variáveis do .env
database/         engine, Session e criação das tabelas
model/            modelos SQLAlchemy (pedido, item, cotação, modalidade, tarifa, movimentação)
schemas/          schemas Pydantic (entrada, saída e erros; geram o Swagger)
routes/           blueprints: pedidos, cotações, tarifas/modalidades, painel
services/         clientes DummyJSON e BrasilAPI, importação, frete, máquina de estados, seeds
seeds/            endereços, tarifas e modalidades iniciais
tests/            testes de frete e de transições de status (pytest)
docs/             fluxograma da arquitetura (PNG + fonte Mermaid)
```
