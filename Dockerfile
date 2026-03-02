FROM python:3.12.6-slim-bullseye AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12.6-slim-bullseye

WORKDIR /app

COPY --from=builder /install /usr/local

COPY . .

EXPOSE 5000

# Updated entrypoint for new folder structure
ENTRYPOINT ["gunicorn", "-w", "4", "api.index:app", "--bind", "0.0.0.0:5000"]
