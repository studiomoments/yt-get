# Используем легковесный образ Python
FROM python:3.11-slim

# Устанавливаем системные зависимости, необходимые для yt-dlp (ffmpeg) и компиляции некоторых библиотек
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /lib/apt/lists/*

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файлы зависимостей и устанавливаем их
# (Мы также можем установить их напрямую, чтобы не создавать лишний requirements.txt)
RUN pip install --no-cache-dir fastapi uvicorn requests yt-dlp

# Копируем код приложения в контейнер
COPY main.py .

# Render передает порт через переменную среды $PORT, используем её при запуске
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
