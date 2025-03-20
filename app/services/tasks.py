import math
import asyncio
import logging
from threading import Lock

from services.ground_control import (
    register_vehicle_async,
    get_route_async,
    get_permission_async,
    inform_about_arrival_async
)
from services.orchestrator import (
    start_boarding,
    finish_boarding,
    start_unboarding,
    finish_unboarding
)

# Храним состояние
vehicle_node_mapping = {}          # { vehicle_id: current_node }
vehicle_node_mapping_place = {}    # { vehicle_id: { coords: plane_node_id } }

# Учет состояния самолетов и машин
aircraft_vehicles = {}             # { aircraft_id: set(vehicle_ids) }
aircraft_status = {}               # { aircraft_id: {"status": "started/finished", "passenger_count": count} }

# Вместимость по умолчанию
vehicle_capacity = 400
SPEED_CAR = 25  # м/с движение

lock_object = Lock()

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")

async def process_transporter_task(
    aircraft_id: str,
    aircraft_coordinates: str,
    passenger_count: int,
    is_boarding: bool
):
    """
    Одна «поездка»:
      1) Найти/зарегистрировать машину (макс 6 штук).
      2) Ехать к самолёту.
      3) Сообщить оркестратору, что мы начали boarding/unboarding.
      4) Подождать нужное время на посадку/высадку (passenger_count / 50).
      5) Сообщить оркестратору, что мы закончили boarding/unboarding.
      6) Вернуться в гараж.
    """
    vehicle_type = "bus"
    vehicle_id = None
    garage_node = None
    plane_node = None

    # 1) Ищем свободную машину
    with lock_object:
        found = None
        for vid, node in vehicle_node_mapping.items():
            if node != "в пути":
                found = (vid, node)
                break

        if found:
            vehicle_id, garage_node = found
            plane_node = vehicle_node_mapping_place[vehicle_id].get(aircraft_coordinates)
            vehicle_node_mapping[vehicle_id] = "в пути"

    # Если не нашли, регистрируем новую, но максимум 6
    if not vehicle_id:
        with lock_object:
            if len(vehicle_node_mapping) >= 6:
                logger.warning("Лимит 6 машин уже достигнут, не регистрируем новую.")
                return  # Выходим, машину создать нельзя

        reg_resp = await register_vehicle_async(vehicle_type)
        if not reg_resp:
            logger.error("Не удалось зарегистрировать новую машину (ответ ground-control).")
            return

        vehicle_id = reg_resp.vehicleId
        garage_node = reg_resp.garrageNodeId
        plane_node = reg_resp.serviceSpots.get(aircraft_coordinates)

        with lock_object:
            vehicle_node_mapping[vehicle_id] = "в пути"
            vehicle_node_mapping_place[vehicle_id] = reg_resp.serviceSpots

        logger.info("Создана новая машина %s -> гараж %s", vehicle_id, garage_node)
        audit_logger.info("Новая машина %s зарегистрирована (всего %d)", vehicle_id, len(vehicle_node_mapping))

    # Проверка, нашли ли мы plane_node
    if not plane_node:
        logger.error("Не можем найти узел самолёта для координат %s", aircraft_coordinates)
        with lock_object:
            if vehicle_id in vehicle_node_mapping:
                vehicle_node_mapping[vehicle_id] = garage_node
        return

    # 2) Едем к самолёту
    route = await get_route_async(garage_node, plane_node)

    # +++ Добавить здесь +++
    if not route:
        logger.error("[%s] Маршрут не найден. Возвращаем машину в гараж.", vehicle_id)
        async with lock_object:  # Используем asyncio.Lock вместо threading.Lock
            vehicle_node_mapping[vehicle_id] = garage_node
        return

    if route:
        logger.info("[%s] Маршрут к самолёту: %s", vehicle_id, route)
        audit_logger.info("Машина %s -> к самолёту %s", vehicle_id, route)
        for i in range(len(route) - 1):
            dist = await get_permission_async(vehicle_id, vehicle_type, route[i], route[i + 1])
            if dist:
                logger.info("[%s] Едет %s -> %s (%.2f м)", vehicle_id, route[i], route[i+1], dist)
                travel_time = dist / SPEED_CAR
                await asyncio.sleep(math.ceil(travel_time))
                await inform_about_arrival_async(vehicle_id, vehicle_type, route[i + 1])
    else:
        logger.warning("[%s] Не смогли получить маршрут до самолёта.", vehicle_id)

    # 3) Сообщаем оркестратору, что мы начали boarding или unboarding
    # Добавляем машину в список обслуживающих этот самолет
    is_first_vehicle = False
    with lock_object:
        if aircraft_id not in aircraft_vehicles:
            aircraft_vehicles[aircraft_id] = set()
            aircraft_status[aircraft_id] = {"status": "none", "passenger_count": 0}
            is_first_vehicle = True
        
        aircraft_vehicles[aircraft_id].add(vehicle_id)
        aircraft_status[aircraft_id]["passenger_count"] += passenger_count
        
    # Только первая машина отправляет уведомление о начале
    if is_first_vehicle:
        if is_boarding:
            await start_boarding(aircraft_id)
            logger.info("Начинаем посадку пассажиров (aircraft=%s)", aircraft_id)
            with lock_object:
                aircraft_status[aircraft_id]["status"] = "boarding"
        else:
            await start_unboarding(aircraft_id)
            logger.info("Начинаем высадку пассажиров (aircraft=%s)", aircraft_id)
            with lock_object:
                aircraft_status[aircraft_id]["status"] = "unboarding"
    else:
        logger.info("[%s] Присоединяется к %s самолета %s", 
                   vehicle_id, "посадке" if is_boarding else "высадке", aircraft_id)

    # 4) Время посадки/высадки = passenger_count / 50 пассажиров/сек (без округления)
    operation_time = passenger_count / 50
    logger.info("Требуется %.2f сек на %s %d пассажиров", operation_time, 
                ("посадку" if is_boarding else "высадку"), passenger_count)
    await asyncio.sleep(operation_time)

    # 5) Сообщаем оркестратору, что закончили boarding/unboarding
    is_last_vehicle = False
    with lock_object:
        # Удаляем машину из списка обслуживающих этот самолет
        if aircraft_id in aircraft_vehicles:
            aircraft_vehicles[aircraft_id].remove(vehicle_id)
            # Если это последняя машина, отправляем уведомление о завершении
            if not aircraft_vehicles[aircraft_id]:
                is_last_vehicle = True
                total_passengers = aircraft_status[aircraft_id]["passenger_count"]
                # Очищаем данные по самолету
                del aircraft_vehicles[aircraft_id]
                del aircraft_status[aircraft_id]

    if is_last_vehicle:
        if is_boarding:
            await finish_boarding(aircraft_id, total_passengers)
            logger.info("Завершили посадку (aircraft=%s, %d пассажиров)", aircraft_id, total_passengers)
        else:
            await finish_unboarding(aircraft_id, total_passengers)
            logger.info("Завершили высадку (aircraft=%s, %d пассажиров)", aircraft_id, total_passengers)
    else:
        logger.info("[%s] Завершил свою часть %s для самолета %s", 
                   vehicle_id, "посадки" if is_boarding else "высадки", aircraft_id)

    # 6) Возвращаемся в гараж
    route_back = await get_route_async(plane_node, garage_node)

    if not route_back:
        logger.error("[%s] Обратный маршрут не найден. Возвращаем машину в гараж.", vehicle_id)
        async with lock_object:
            vehicle_node_mapping[vehicle_id] = garage_node
        return

    if route_back:
        logger.info("[%s] Маршрут обратно: %s", vehicle_id, route_back)
        for i in range(len(route_back) - 1):
            dist = await get_permission_async(vehicle_id, vehicle_type, route_back[i], route_back[i + 1])
            if dist:
                travel_time = dist / SPEED_CAR
                await asyncio.sleep(math.ceil(travel_time))
                await inform_about_arrival_async(vehicle_id, vehicle_type, route_back[i + 1])

        with lock_object:
            vehicle_node_mapping[vehicle_id] = garage_node
        logger.info("Машина %s вернулась в гараж %s", vehicle_id, garage_node)
        audit_logger.info("Машина %s свободна", vehicle_id)
    else:
        logger.warning("[%s] Не смогли получить маршрут обратно в гараж.", vehicle_id)
