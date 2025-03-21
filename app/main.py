# app/main.py

import uvicorn
import logging
from fastapi import FastAPI

from routes import transporter, admin

def create_app() -> FastAPI:
    app = FastAPI(
        title="Transporter API",
        description="API для управления посадкой и высадкой пассажиров",
        version="1.0.0"
    )
    app.include_router(transporter.router, tags=["Transporter"])
    app.include_router(admin.router, tags=["Admin"])
    return app


app = create_app()

if __name__ == "__main__":
    # Пример элементарной настройки
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Создадим отдельный логгер для аудита, который пишет в файл
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)

    # Хендлер в файл audit.log
    audit_file_handler = logging.FileHandler("audit.log", encoding="utf-8")
    audit_file_handler.setFormatter(logging.Formatter(
        fmt='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    audit_logger.addHandler(audit_file_handler)

    # Запуск uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
