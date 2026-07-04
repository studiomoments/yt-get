import random
import re
from fastapi import FastAPI, HTTPException, Query
import requests
import yt_dlp

app = FastAPI()

# Ссылки на ваши бесплатные списки прокси
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
]

def get_fresh_proxies():
    """Скачивает и объединяет прокси из всех трех источников с указанием протокола"""
    proxies = []
    
    for url in PROXY_SOURCES:
        try:
            # Определяем протокол по имени файла
            protocol = "socks5" if "socks5" in url else "socks4" if "socks4" in url else "http"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                lines = response.text.splitlines()
                # Форматируем в вид: protocol://ip:port
                proxies.extend([f"{protocol}://{line.strip()}" for line in lines if line.strip()])
        except Exception:
            continue # Если один из списков недоступен, пропускаем его
            
    # Перемешиваем, чтобы не брать всегда одни и те же
    random.shuffle(proxies)
    return proxies

@app.get("/get-stream")
def get_stream_url(url: str = Query(..., description="Ссылка на YouTube видео")):
    # Получаем свежий пул прокси при каждом запросе к нашему эндпоинту
    proxy_pool = get_fresh_proxies()
    
    # Пытаемся сначала сделать запрос без прокси (напрямую с сервера)
    attempts = 0
    max_attempts = 10 # Максимум 10 попыток сменить прокси
    current_proxy = None

    while attempts < max_attempts:
        # Настройки для yt-dlp
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
        }
        
        # Если это не первая попытка, добавляем прокси в настройки yt-dlp
        if current_proxy:
            ydl_opts['proxy'] = current_proxy

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Извлекаем информацию без скачивания самого файла
                info = ydl.extract_info(url, download=False)
                # Возвращаем прямую ссылку на поток
                return {
                    "status": "success", 
                    "proxy_used": current_proxy or "Direct Server IP", 
                    "stream_url": info.get('url')
                }
                
        except yt_dlp.utils.DownloadError as e:
            error_message = str(e)
            
            # Проверяем, вызвана ли ошибка блокировкой (робот / капча / sign in)
            is_bot_detected = any(keyword in error_message.lower() for keyword in [
                "bot", "captcha", "sign in to confirm", "confirm you`re not a bot", "429"
            ])
            
            if is_bot_detected or "ExtractorError" in error_message:
                attempts += 1
                if not proxy_pool:
                    raise HTTPException(status_code=500, detail="Пул бесплатных прокси пуст или недоступен.")
                
                # Берем следующий случайный прокси из списка
                current_proxy = proxy_pool.pop(0)
                print(f"[Попытка {attempts}] Блокировка! Пробуем новый прокси: {current_proxy}")
            else:
                # Если ошибка другая (например, видео удалено или неверная ссылка), сразу отдаем ошибку клиенту
                raise HTTPException(status_code=400, detail=f"Ошибка yt-dlp: {error_message}")

    raise HTTPException(status_code=503, detail="Не удалось обойти блокировку. Все прокси забанены.")

if __name__ == "__main__":
    import uvicorn
    import os
    # Локально запустится на 8000 порту, если переменная PORT не задана
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
