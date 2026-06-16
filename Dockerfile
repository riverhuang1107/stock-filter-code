FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/stock-filter-matplotlib

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY stock_filter_tool ./stock_filter_tool
COPY README.md pyproject.toml ./

CMD ["python", "-m", "stock_filter_tool", "run", "--top", "10", "--days", "3", "--chart-days", "5", "--send-email"]
