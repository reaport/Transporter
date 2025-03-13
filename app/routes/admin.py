# app/routes/admin.py

import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from services.tasks import (
    vehicle_node_mapping,
    vehicle_node_mapping_place,
    vehicle_capacity,
    lock_object
)

router = APIRouter()

@router.get("/admin/vehicles")
async def list_vehicles():
    """
    Возвращает JSON со списком машин,
    их текущим положением и т.д.
    """
    with lock_object:
        data = []
        for v_id, node in vehicle_node_mapping.items():
            data.append({
                "vehicle_id": v_id,
                "current_node": node,
                "service_spots": vehicle_node_mapping_place.get(v_id, {})
            })
        return {
            "count": len(data),
            "vehicles": data,
            "capacity": vehicle_capacity
        }


@router.get("/admin/audit")
async def get_audit():
    """
    Возвращает содержимое audit.log в виде JSON-массива строк.
    Если файл не найден или пуст, возвращаем ["(Нет записей)"].
    """
    logfile_path = "app/audit.log"  # Путь к вашему лог-файлу
    if os.path.exists(logfile_path):
        with open(logfile_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Удаляем переносы строк
        lines = [line.rstrip("\n\r") for line in lines]
        if lines:
            return {"lines": lines}
    return {"lines": ["(Нет записей или файл не найден)"]}


@router.get("/admin/ui", response_class=HTMLResponse)
async def admin_ui():
    """
    Возвращает содержимое admin_ui.html.
    """
    # Определяем путь к файлу admin_ui.html
    html_path = os.path.join(os.path.dirname(__file__), "admin_ui.html")
    if not os.path.exists(html_path):
        return HTMLResponse("<h1>admin_ui.html not found</h1>", status_code=404)

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(html_content)
