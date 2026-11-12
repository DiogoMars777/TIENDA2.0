# ==============================================================================
# CU25 - GESTIONAR CAMBIOS Y DEVOLUCIONES DE PRENDAS -> MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu25_gestionar_cambios_devoluciones/devolucion_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class Devolucion(Base):
    """
    Entidad para registrar solicitudes y ejecuciones de cambios de talla/prenda
    o devoluciones monetarias/notas de crédito con retorno al inventario.
    """
    __tablename__ = "devolucion"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1, index=True)
    venta_id = Column(Integer, ForeignKey("venta.id", ondelete="CASCADE"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id", ondelete="SET NULL"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)  # Operador que atiende
    sucursal_id = Column(Integer, ForeignKey("sucursal.id", ondelete="CASCADE"), nullable=False)
    codigo_devolucion = Column(String(50), nullable=False, unique=True, index=True)
    tipo_devolucion = Column(String(50), nullable=False)  # CAMBIO_TALLA, CAMBIO_PRENDA, REEMBOLSO_TOTAL, NOTA_CREDITO
    motivo = Column(Text, nullable=False)
    estado = Column(String(30), default="APROBADA", index=True)  # PENDIENTE, APROBADA, RECHAZADA, COMPLETADA
    monto_reembolso = Column(Numeric(12, 2), default=0.0)
    reingreso_inventario = Column(Boolean, default=True)
    fecha_solicitud = Column(DateTime, default=get_bolivia_now)
    fecha_resolucion = Column(DateTime, default=get_bolivia_now)

    detalles = relationship("DetalleDevolucion", back_populates="devolucion", cascade="all, delete-orphan")


class DetalleDevolucion(Base):
    __tablename__ = "detalle_devolucion"

    id = Column(Integer, primary_key=True, index=True)
    devolucion_id = Column(Integer, ForeignKey("devolucion.id", ondelete="CASCADE"), nullable=False)
    variante_devuelta_id = Column(Integer, ForeignKey("variante_producto.id"), nullable=False)
    variante_nueva_id = Column(Integer, ForeignKey("variante_producto.id"), nullable=True)  # Si aplica cambio
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    estado_prenda = Column(String(50), default="PERFECTO_ESTADO")  # PERFECTO_ESTADO, DEFECTUOSO, DAÑADO

    devolucion = relationship("Devolucion", back_populates="detalles")


DevolucionModel = Devolucion
DetalleDevolucionModel = DetalleDevolucion
devolucion = Devolucion
detalle_devolucion = DetalleDevolucion
