# ==============================================================================
# CU23 - SINCRONIZAR OPERACIONES OFFLINE -> MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu23_sincronizar_operaciones_offline/sincronizacion_offline_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class OperacionOfflineSync(Base):
    """
    Entidad de registro para el log de transacciones y operaciones offline enviadas a sincronización.
    Previene duplicados mediante UUID y registra la estrategia de resolución de conflictos aplicada.
    """
    __tablename__ = "sincronizacion_offline"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id", ondelete="CASCADE"), nullable=False)
    tipo_operacion = Column(String(40), nullable=False, index=True)  # VENTA, RESERVA, COBRO, AJUSTE_STOCK
    uuid_operacion = Column(String(64), nullable=False, unique=True, index=True)
    payload_json = Column(Text, nullable=False)
    estado = Column(String(30), default="PENDIENTE", index=True)  # PENDIENTE, SINCRONIZADO, CONFLICTO_RESUELTO, ERROR
    estrategia_conflicto = Column(String(60), nullable=True)  # LAST_WRITE_WINS, REASIGNAR_SUCURSAL, KARDEX_AJUSTE
    reintentos = Column(Integer, default=0)
    error_detalle = Column(Text, nullable=True)
    fecha_operacion_origen = Column(DateTime, nullable=False)
    fecha_recibido = Column(DateTime, default=get_bolivia_now)
    fecha_procesado = Column(DateTime, nullable=True)


OperacionOfflineSyncModel = OperacionOfflineSync
sincronizacion_offline = OperacionOfflineSync
