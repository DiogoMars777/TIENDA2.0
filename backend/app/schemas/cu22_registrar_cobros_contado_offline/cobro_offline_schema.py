# ==============================================================================
# CU22 - REGISTRAR COBROS DE CONTADO SIN CONEXIÓN -> ESQUEMAS PYDANTIC (MVC)
# Ubicación: backend/app/schemas/cu22_registrar_cobros_contado_offline/cobro_offline_schema.py
# ==============================================================================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class ItemCobroOffline(BaseModel):
    variante_id: Optional[int] = Field(None, description="ID de la variante de polera vendida")
    producto_nombre: str = Field(..., description="Nombre del modelo de prenda")
    talla: Optional[str] = Field("M", description="Talla de la prenda (S, M, L, XL)")
    color: Optional[str] = Field("Negro", description="Color de la prenda")
    cantidad: int = Field(1, ge=1, description="Cantidad de unidades")
    precio_unitario: Decimal = Field(..., ge=0, description="Precio unitario en Bs.")
    subtotal: Decimal = Field(..., ge=0, description="Subtotal del item en Bs.")


class CobroOfflineCreate(BaseModel):
    sucursal_id: int = Field(..., description="ID de la sucursal física donde se cobra")
    monto: Decimal = Field(..., ge=0, description="Monto total cobrado en efectivo")
    moneda: str = Field("BOB", description="Moneda (BOB)")
    nro_recibo_provisional: str = Field(..., description="Número de folio provisional generado offline (ej. REC-OFF-20261031-001)")
    uuid_operacion: Optional[str] = Field(None, description="UUID único de idempotencia generado por el terminal")
    cliente_nombre: Optional[str] = Field("Cliente Mostrador", description="Nombre o razón social del comprador")
    cliente_nit: Optional[str] = Field("0", description="NIT o CI del cliente")
    efectivo_recibido: Optional[Decimal] = Field(None, ge=0, description="Efectivo entregado por el cliente")
    cambio: Optional[Decimal] = Field(None, ge=0, description="Cambio devuelto")
    observaciones: Optional[str] = Field(None, description="Detalles o notas adicionales")
    fecha_cobro: Optional[datetime] = Field(None, description="Fecha y hora de emisión del cobro en el terminal")
    items: Optional[List[ItemCobroOffline]] = Field(default_factory=list, description="Desglose de prendas vendidas")


class CobroOfflineResponse(BaseModel):
    id: int
    tenant_id: int
    cajero_id: Optional[int] = None
    cajero_nombre: Optional[str] = None
    sucursal_id: int
    sucursal_nombre: Optional[str] = None
    monto: Decimal
    moneda: str
    nro_recibo_provisional: str
    uuid_operacion: str
    cliente_nombre: Optional[str] = None
    cliente_nit: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_cobro: datetime
    sincronizado: bool
    fecha_sincronizacion: Optional[datetime] = None
    venta_id: Optional[int] = None
    items: Optional[List[ItemCobroOffline]] = None
    efectivo_recibido: Optional[Decimal] = None
    cambio: Optional[Decimal] = None

    class Config:
        from_attributes = True


class BatchCobrosOfflineRequest(BaseModel):
    cobros: List[CobroOfflineCreate] = Field(..., description="Lote de cobros generados offline para registrar masivamente")


class CobroOfflineKpis(BaseModel):
    total_cobros: int
    monto_total_offline: float
    pendientes_sync: int
    monto_pendiente: float
    sincronizados: int
    monto_sincronizado: float
    sucursal_activa_id: Optional[int] = None
