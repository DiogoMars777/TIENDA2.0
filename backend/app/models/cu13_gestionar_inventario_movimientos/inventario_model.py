# ==============================================================================
# CU13 - GESTIONAR INVENTARIO Y MOVIMIENTOS -> CAPA MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu13_gestionar_inventario_movimientos/inventario_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, synonym
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class Inventario(Base):
    __tablename__ = "inventario"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    stockfisico = Column(Integer, default=0, nullable=False)
    stockreservado = Column(Integer, default=0, nullable=False)
    stockminimo = Column(Integer, default=5, nullable=False)
    fechaactualizacion = Column(DateTime, default=get_bolivia_now, onupdate=get_bolivia_now)
    sucursalid = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    varianteid = Column(Integer, ForeignKey("variante_producto.id"), nullable=False)

    # Alias de compatibilidad: CU08-CU11 usan .cantidad para referirse al stock físico
    cantidad = synonym("stockfisico")

    sucursal = relationship("Sucursal")
    variante = relationship("VarianteProducto")
    movimientos = relationship("MovimientoInventario", back_populates="inventario", cascade="all, delete-orphan")


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    tipomovimiento = Column(String(50), nullable=False)
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String(200), nullable=True)
    referencia = Column(String(100), nullable=True)
    fecha = Column(DateTime, default=get_bolivia_now)
    inventarioid = Column(Integer, ForeignKey("inventario.id"), nullable=False)
    usuarioid = Column(Integer, ForeignKey("usuario.id"), nullable=False)

    inventario = relationship("Inventario", back_populates="movimientos")
    usuario = relationship("Usuario")


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
InventarioModel = Inventario
MovimientoInventarioModel = MovimientoInventario
InventarioSucursalModel = Inventario

inventario = Inventario
movimiento_inventario = MovimientoInventario
inventario_sucursal = Inventario
