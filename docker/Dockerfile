# Используем официальный Python-образ в качестве базового
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости для сборки (если нужно компилировать зависимости)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей и устанавливаем их
COPY ./app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY ./app/ .

# Запуск Uvicorn сервера
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
