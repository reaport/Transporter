# app/services/ground_control.py

import httpx
import math
import asyncio
import logging

from app.schemas import RegisterVehicleResponse, MoveResponse

# Пример: адреса, куда будем стучаться (меняются при необходимости)
REGISTER_VEHICLE_URL = "https://ground-control.reaport.ru/register-vehicle"
ROUTE_URL = "https://ground-control.reaport.ru/route"
MOVE_URL = "https://ground-control.reaport.ru/move"
ARRIVED_URL = "https://ground-control.reaport.ru/arrived"


async def register_vehicle_async(vehicle_type: str):
    """
    POST /register-vehicle/{vehicle_type}
    """
    url = f"{REGISTER_VEHICLE_URL}/{vehicle_type}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url)
            if resp.status_code == 200:
                return RegisterVehicleResponse(**resp.json())
            elif resp.status_code == 400:
                logging.warning(f"[register_vehicle_async] 400: Неверные данные. {resp.text}")
            elif resp.status_code == 403:
                logging.warning("[register_vehicle_async] 403: Нет свободного узла.")
            else:
                logging.warning(f"[register_vehicle_async] Ошибка {resp.status_code}: {resp.text}")
        except Exception as e:
            logging.error(f"[register_vehicle_async] Exception: {e}")
    return None


async def get_route_async(_from: str, _to: str):
    """
    POST /route
    """
    async with httpx.AsyncClient() as client:
        json_data = {
            "from": _from,
            "to": _to,
            "type": "bus" 
        }
        try:
            resp = await client.post(ROUTE_URL, json=json_data)
            if resp.status_code == 200:
                return resp.json()  # ожидаем list[str]
            elif resp.status_code == 404:
                logging.warning("[get_route_async] Маршрут не найден.")
            else:
                logging.warning(f"[get_route_async] Ошибка {resp.status_code}: {resp.text}")
        except Exception as e:
            logging.error(f"[get_route_async] Exception: {e}")
    return None


async def get_permission_async(vehicle_id: str, vehicle_type: str, _from: str, _to: str):
    """
    POST /move
    Возвращает дистанцию (float), которую нужно проехать.
    """
    async with httpx.AsyncClient() as client:
        json_data = {
            "vehicleId": vehicle_id,
            "vehicleType": vehicle_type,
            "from": _from,
            "to": _to
        }
        try:
            resp = await client.post(MOVE_URL, json=json_data)
            if resp.status_code == 200:
                move_resp = MoveResponse(**resp.json())
                return move_resp.distance
            elif resp.status_code == 400:
                logging.warning(f"[get_permission_async] 400: Неверный запрос. {resp.text}")
            elif resp.status_code == 403:
                logging.warning("[get_permission_async] 403: Перемещение запрещено.")
            elif resp.status_code == 404:
                logging.warning("[get_permission_async] 404: Один из узлов не найден.")
            elif resp.status_code == 409:
                logging.warning(f"[get_permission_async] 409: Узел {_to} занят. Повторим позже.")
                # Ждём секунду и пробуем снова
                await asyncio.sleep(1)
                return await get_permission_async(vehicle_id, vehicle_type, _from, _to)
            else:
                logging.warning(f"[get_permission_async] Ошибка {resp.status_code}: {resp.text}")
        except Exception as e:
            logging.error(f"[get_permission_async] Exception: {e}")
    return None


async def inform_about_arrival_async(vehicle_id: str, vehicle_type: str, node_id: str):
    """
    POST /arrived
    """
    async with httpx.AsyncClient() as client:
        json_data = {
            "vehicleId": vehicle_id,
            "vehicleType": vehicle_type,
            "nodeId": node_id
        }
        try:
            resp = await client.post(ARRIVED_URL, json=json_data)
            if resp.status_code == 200:
                logging.info(f"[inform_about_arrival_async] Машина {vehicle_id} прибыла в узел {node_id}")
            elif resp.status_code == 400:
                logging.warning("[inform_about_arrival_async] 400: Неверный запрос о прибытии.")
            else:
                logging.warning(f"[inform_about_arrival_async] Ошибка {resp.status_code}: {resp.text}")
        except Exception as e:
            logging.error(f"[inform_about_arrival_async] Exception: {e}")
