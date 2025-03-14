import math
import asyncio
import logging
from fastapi import APIRouter, HTTPException

# Импортируем наши схемы из app.schemas
from schemas import (
    LoadRequest,
    UploadRequest,
    TransporterResponse,
    VehicleCapacity
)

# Импортируем переменные и функцию "процесса" из tasks.py
# (где хранится логика поездок и глобальные переменные)
from services.tasks import (
    lock_object,
    vehicle_node_mapping,
    vehicle_node_mapping_place,
    vehicle_capacity,
    process_transporter_task
)

# Создаём роутер
router = APIRouter()

# Логгер для обычных сообщений
logger = logging.getLogger(__name__)
# Логгер для аудита (будет записывать события в отдельный файл или канал)
audit_logger = logging.getLogger("audit")


@router.post("/load", response_model=TransporterResponse)
async def load_passengers(request: LoadRequest):
    """
    Запрос на посадку пассажиров.
    """
    # Логируем входной запрос в аудит
    audit_logger.info("Запрос /load: %s", request.dict())

    if request.passenger_count <= 0:
        logger.warning("Попытка загрузить 0 или отрицательное число пассажиров")
        raise HTTPException(status_code=400, detail="Неверный запрос: passenger_count <= 0")
    if not request.aircraft_id or not request.aircraft_coordinates:
        logger.warning("Некорректные поля в запросе load_passengers")
        raise HTTPException(status_code=400, detail="Неверный запрос (пустые поля)")

    # Считаем нужное число машин
    needed_cars = math.ceil(request.passenger_count / vehicle_capacity)

    waiting = False
    # Проверяем, есть ли хотя бы одна свободная машина
    with lock_object:
        found_vehicle = next((k for k, v in vehicle_node_mapping.items() if v != "в пути"), None)
        if not found_vehicle:
            waiting = True
            logger.info("Нет свободных машин -> waiting = True")

    # Запускаем асинхронные "поездки"
    tasks = []
    for _ in range(needed_cars):
        tasks.append(asyncio.create_task(process_transporter_task(
            aircraft_id=request.aircraft_id,
            aircraft_coordinates=request.aircraft_coordinates,
            passenger_count=request.passenger_count,
            is_boarding=True
        )))

    # Не дожидаемся завершения тасков в рамках запроса, чтобы не блокировать
    if tasks:
        asyncio.gather(*tasks)
        logger.info("Запустили %d задач на перевозку (load)", needed_cars)

    # Логируем ответ
    audit_logger.info("Ответ /load: waiting=%s, needed_cars=%d", waiting, needed_cars)

    return TransporterResponse(waiting=waiting)


@router.post("/upload", response_model=TransporterResponse)
async def unload_passengers(request: UploadRequest):
    """
    Запрос на высадку пассажиров.
    """
    audit_logger.info("Запрос /upload: %s", request.dict())

    if request.passenger_count <= 0:
        logger.warning("Попытка выгрузить 0 или отрицательное число пассажиров")
        raise HTTPException(status_code=400, detail="Неверный запрос: passenger_count <= 0")
    if not request.aircraft_id or not request.aircraft_coordinates:
        logger.warning("Некорректные поля в запросе unload_passengers")
        raise HTTPException(status_code=400, detail="Неверный запрос (пустые поля)")

    needed_cars = math.ceil(request.passenger_count / vehicle_capacity)

    waiting = False
    with lock_object:
        found_vehicle = next((k for k, v in vehicle_node_mapping.items() if v != "в пути"), None)
        if not found_vehicle:
            waiting = True
            logger.info("Нет свободных машин -> waiting = True")

    tasks = []
    for _ in range(needed_cars):
        tasks.append(asyncio.create_task(process_transporter_task(
            aircraft_id=request.aircraft_id,
            aircraft_coordinates=request.aircraft_coordinates,
            passenger_count=request.passenger_count,
            is_boarding=False
        )))

    if tasks:
        asyncio.gather(*tasks)
        logger.info("Запустили %d задач на перевозку (upload)", needed_cars)

    audit_logger.info("Ответ /upload: waiting=%s, needed_cars=%d", waiting, needed_cars)

    return TransporterResponse(waiting=waiting)


@router.get("/getCapacity")
async def get_vehicle_capacity():
    """
    Получить текущую вместимость транспортного средства.
    """
    logger.info("[get_vehicle_capacity] Текущая вместимость: %d", vehicle_capacity)
    audit_logger.info("Запрос /getCapacity -> %d", vehicle_capacity)
    return {"capacity": vehicle_capacity}


@router.post("/updateCapacity")
async def set_vehicle_capacity(new_cap: VehicleCapacity):
    """
    Обновить вместимость транспортного средства.
    """
    global vehicle_capacity
    audit_logger.info("Запрос /updateCapacity: %s", new_cap.dict())
    if new_cap.capacity < 0:
        logger.error("Некорректное значение вместимости: %d", new_cap.capacity)
        raise HTTPException(status_code=400, detail="Некорректное значение вместимости")

    vehicle_capacity = new_cap.capacity
    logger.info("[set_vehicle_capacity] Установлена вместимость: %d", vehicle_capacity)
    audit_logger.info("Обновленная вместимость: %d", vehicle_capacity)

    return {"capacity": vehicle_capacity}
