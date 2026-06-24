FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md constraints.txt ./
COPY src ./src

RUN python -m pip install --no-cache-dir -c constraints.txt .

CMD ["python", "-m", "railway_lakehouse.bronze.run", "schedule"]
