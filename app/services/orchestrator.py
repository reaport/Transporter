import httpx
import logging

ORCHESTRATOR_URL = "https://orchestrator.reaport.ru"  # общий хост

logger = logging.getLogger(__name__)

async def start_unboarding(aircraft_id: str):
    """
    POST /boarding/unboarding/start
    body: { "aircraft_id": aircraft_id }
    """
    url = f"{ORCHESTRATOR_URL}/boarding/unboarding/start"
    data = {"aircraft_id": aircraft_id}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=data)
            if resp.status_code == 204:
                logger.info("[start_unboarding] Успешно отправили старт")
            else:
                logger.warning(f"[start_unboarding] Ошибка {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[start_unboarding] Exception: {e}")

async def finish_unboarding(aircraft_id: str, passengers_count: int):
    """
    POST /boarding/unboarding/finish
    body: { "aircraft_id": aircraft_id, "passengers_count": passengers_count }
    """
    url = f"{ORCHESTRATOR_URL}/boarding/unboarding/finish"
    data = {
        "aircraft_id": aircraft_id,
        "passengers_count": passengers_count
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=data)
            if resp.status_code == 204:
                logger.info("[finish_unboarding] Успешно отправили финиш")
            else:
                logger.warning(f"[finish_unboarding] Ошибка {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[finish_unboarding] Exception: {e}")

async def start_boarding(aircraft_id: str):
    """
    POST /boarding/boarding/start
    """
    url = f"{ORCHESTRATOR_URL}/boarding/boarding/start"
    data = {"aircraft_id": aircraft_id}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=data)
            if resp.status_code == 204:
                logger.info("[start_boarding] Успешно отправили старт")
            else:
                logger.warning(f"[start_boarding] Ошибка {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[start_boarding] Exception: {e}")

async def finish_boarding(aircraft_id: str, passengers_count: int):
    """
    POST /boarding/boarding/finish
    body: { "aircraft_id": aircraft_id, "passengers_count": passengers_count }
    """
    url = f"{ORCHESTRATOR_URL}/boarding/boarding/finish"
    data = {
        "aircraft_id": aircraft_id,
        "passengers_count": passengers_count
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=data)
            if resp.status_code == 204:
                logger.info("[finish_boarding] Успешно отправили финиш")
            else:
                logger.warning(f"[finish_boarding] Ошибка {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[finish_boarding] Exception: {e}")
