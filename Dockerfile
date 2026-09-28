# Imagem da API Docas: Python 3.12 enxuto + gunicorn
FROM python:3.12-slim

# Evita arquivos .pyc e força logs sem buffer (aparecem na hora no "docker logs")
# TZ: "hoje", datas prometidas, atrasos e horários no fuso de Brasília (o padrão do container é UTC)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

# Instala as dependências primeiro para aproveitar o cache de camadas do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação (ver .dockerignore)
COPY . .

EXPOSE 5000

# Um único worker (padrão do gunicorn) evita concorrência na carga inicial do SQLite;
# threads atendem requisições simultâneas e o timeout maior cobre a importação,
# que faz várias chamadas externas.
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--threads", "4", "--timeout", "120", "app:app"]
