# ==============================================================================
# CU22 - REGISTRAR COBROS DE CONTADO SIN CONEXIÓN -> MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu22_registrar_cobros_contado_offline/cobro_offline_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class CobroOffline(Base):
    """
    Entidad para registrar cobros en efectivo realizados sin conexión a internet en mostrador/caja.
    Mantiene folio provisional y clave de idempotencia UUID para sincronización diferida.
    """
    __tablename__ = "cobro_offline"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1, index=True)
    cajero_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id", ondelete="CASCADE"), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    moneda = Column(String(5), default="BOB")
    nro_recibo_provisional = Column(String(50), nullable=False, unique=True, index=True)
    uuid_operacion = Column(String(64), nullable=False, unique=True, index=True)
    cliente_nombre = Column(String(120), nullable=True)
    cliente_nit = Column(String(30), nullable=True)
    observaciones = Column(Text, nullable=True)
    fecha_cobro = Column(DateTime, default=get_bolivia_now, index=True)
    sincronizado = Column(Boolean, default=False, index=True)
    fecha_sincronizacion = Column(DateTime, nullable=True)
    venta_id = Column(Integer, ForeignKey("venta.id", ondelete="SET NULL"), nullable=True)


CobroOfflineModel = CobroOffline
cobro_offline = CobroOffline
