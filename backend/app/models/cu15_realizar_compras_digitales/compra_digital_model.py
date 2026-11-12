# ==============================================================================
# CU15 - REALIZAR COMPRAS DIGITALES -> CAPA MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu15_realizar_compras_digitales/compra_digital_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship, synonym
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class Carrito(Base):
    __tablename__ = "carrito"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    estado = Column(String(50), nullable=False, default="Activo")
    fechacreacion = Column(DateTime, default=get_bolivia_now, nullable=False)
    fechaactualizacion = Column(DateTime, default=get_bolivia_now, onupdate=get_bolivia_now)
    clienteid = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    usuarioid = synonym("clienteid")
    sucursalid = Column(Integer, ForeignKey("sucursal.id"), nullable=True)

    items = relationship("CarritoItem", back_populates="carrito", cascade="all, delete-orphan")
    cliente = relationship("Usuario", foreign_keys=[clienteid])
    sucursal = relationship("Sucursal")


class CarritoItem(Base):
    __tablename__ = "carrito_item"

    carritoid = Column(Integer, ForeignKey("carrito.id"), primary_key=True)
    varianteid = Column(Integer, ForeignKey("variante_producto.id"), primary_key=True)
    cantidad = Column(Integer, nullable=False, default=1)
    preciounitario = Column(Numeric(12, 2), nullable=False)
    fechaagregado = Column(DateTime, default=get_bolivia_now)

    carrito = relationship("Carrito", back_populates="items")
    variante = relationship("VarianteProducto")


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
CarritoModel = Carrito
CarritoItemModel = CarritoItem

carrito = Carrito
carrito_item = CarritoItem
