# ==============================================================================
# CU10 - GESTIONAR RESERVAS DE PRENDAS -> CAPA MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu10_gestionar_reservas_prendas/reserva_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class Reserva(Base):
    __tablename__ = "reserva"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    codigoreserva = Column(String(100), unique=True, nullable=False, index=True)
    fechareserva = Column(DateTime, default=get_bolivia_now, nullable=False)
    estado = Column(String(50), default="PENDIENTE", nullable=False)  # PENDIENTE, CONFIRMADA, PAGADA, ENTREGADA, CANCELADA, EXPIRADA
    observaciones = Column(Text, nullable=True)
    sucursalid = Column(Integer, ForeignKey("sucursal.id", ondelete="RESTRICT"), nullable=False, index=True)
    clienteid = Column(Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False, index=True)

    sucursal = relationship("Sucursal", backref="reservas")
    cliente = relationship("Usuario", foreign_keys=[clienteid], backref="reservas")
    detalles = relationship("ReservaDetalle", back_populates="reserva", cascade="all, delete-orphan")

    @property
    def fecha_expiracion(self) -> datetime:
        """Vencimiento de 48 horas oficiales para retiro físico en tienda"""
        return (self.fechareserva or get_bolivia_now()) + timedelta(hours=48)

    @property
    def es_expirada(self) -> bool:
        """Indica si han transcurrido más de 48 horas desde la creación de la reserva"""
        return get_bolivia_now() > self.fecha_expiracion


class ReservaDetalle(Base):
    __tablename__ = "reserva_detalle"

    varianteid = Column(Integer, ForeignKey("variante_producto.id", ondelete="RESTRICT"), primary_key=True)
    reservaid = Column(Integer, ForeignKey("reserva.id", ondelete="CASCADE"), primary_key=True)
    cantidad = Column(Integer, nullable=False)

    reserva = relationship("Reserva", back_populates="detalles")
    variante = relationship("VarianteProducto")


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
ReservaModel = Reserva
ReservaDetalleModel = ReservaDetalle

reserva = Reserva
reserva_detalle = ReservaDetalle

__all__ = [
    "Reserva", "ReservaDetalle",
    "ReservaModel", "ReservaDetalleModel",
    "reserva", "reserva_detalle"
]
