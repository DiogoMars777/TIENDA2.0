from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ReservaDetalleResponse(BaseModel):
    variante_id: int
    producto_nombre: str
    talla: Optional[str] = None
    color: Optional[str] = None
    codigo_hex: Optional[str] = None
    imagen_url: Optional[str] = None
    precio_unitario: float
    cantidad: int
    subtotal: float

    class Config:
        from_attributes = True


class ReservaSucursalResponse(BaseModel):
    id: int
    nombre: str
    ciudad: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None

    class Config:
        from_attributes = True


class ReservaResponse(BaseModel):
    id: int
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_expiracion: Optional[datetime] = None
    horas_restantes: Optional[int] = None
    estado: str
    observaciones: Optional[str] = None
    cliente_id: Optional[int] = None
    cliente_nombre: Optional[str] = None
    cliente_email: Optional[str] = None
    cliente_telefono: Optional[str] = None
    sucursal: Optional[ReservaSucursalResponse] = None
    detalles: List[ReservaDetalleResponse] = []
    total_items: int = 0
    total_estimado: float = 0.0
    mensaje: Optional[str] = None
    cancelada_sin_stock: Optional[bool] = False

    class Config:
        from_attributes = True


class ReservaItemCreate(BaseModel):
    producto_id: Optional[int] = None
    variante_id: Optional[int] = None
    cantidad: int = 1


class ReservaCreate(BaseModel):
    sucursal_id: Optional[int] = None
    observaciones: Optional[str] = None
    items: Optional[List[ReservaItemCreate]] = None
    codigo_reserva: Optional[str] = None
    es_offline: Optional[bool] = False
    fecha_reserva: Optional[datetime] = None


class CancelarReservaRequest(BaseModel):
    motivo: Optional[str] = None


class AtenderReservaRequest(BaseModel):
    accion: str  # 'ENTREGAR' o 'CANCELAR'
    observaciones: Optional[str] = None


class PagarReservaRequest(BaseModel):
    metodo_pago: str = "QR"  # 'PayPal', 'Tarjeta', 'QR', 'Efectivo'
    referencia: Optional[str] = None
    origen: Optional[str] = "MOVIL"  # 'MOVIL' o 'TIENDA'


