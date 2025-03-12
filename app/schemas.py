# app/schemas.py
from pydantic import BaseModel
from typing import Dict

# Вместимость транспортного средства
class VehicleCapacity(BaseModel):
    capacity: int

# Запрос на посадку пассажиров
class LoadRequest(BaseModel):
    aircraft_id: str
    passenger_count: int
    aircraft_coordinates: str

# Запрос на высадку пассажиров
class UploadRequest(BaseModel):
    aircraft_id: str
    passenger_count: int
    aircraft_coordinates: str

# Ответ на запрос посадки/высадки
class TransporterResponse(BaseModel):
    waiting: bool

# Ответ при возникновении ошибки
class ErrorResponse(BaseModel):
    error: str

# --------------------------------------
# Ниже – структуры для общения с ground-control
# --------------------------------------

# Ответ от /register-vehicle
class RegisterVehicleResponse(BaseModel):
    garrageNodeId: str
    VehicleId: str
    serviceSpots: Dict[str, str]

# Ответ от /move
class MoveResponse(BaseModel):
    distance: float
