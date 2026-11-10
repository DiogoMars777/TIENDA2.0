# ==============================================================================
# CU14 - REGISTRAR VENTAS PRESENCIALES -> CAPA MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu14_registrar_ventas_presenciales/venta_presencial_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Venta(Base):
    __tablename__ = "venta"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    codigoventa = Column(String(100), nullable=False, unique=True)
    tipoventa = Column(String(50), nullable=False, default="Presencial")
    estado = Column(String(50), nullable=False, default="Completada")
    subtotal = Column(Numeric(12, 2), nullable=False)
    descuento = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    sucursalid = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    clienteid = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    usuarioid = Column(Integer, ForeignKey("usuario.id"), nullable=False)

    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    pagos = relationship("Pago", back_populates="venta", cascade="all, delete-orphan")
    sucursal = relationship("Sucursal")
    cliente = relationship("Cliente")
    usuario = relationship("Usuario")


class DetalleVenta(Base):
    __tablename__ = "detalle_venta"

    ventaid = Column(Integer, ForeignKey("venta.id"), primary_key=True)
    varianteid = Column(Integer, ForeignKey("variante_producto.id"), primary_key=True)
    cantidad = Column(Integer, nullable=False)
    preciounitario = Column(Numeric(12, 2), nullable=False)
    descuento = Column(Numeric(12, 2), default=0)
    subtotal = Column(Numeric(12, 2), nullable=False)

    venta = relationship("Venta", back_populates="detalles")
    variante = relationship("VarianteProducto")


class MetodoPago(Base):
    __tablename__ = "metodo_pago"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    estado = Column(Boolean, default=True)


class Recibo(Base):
    __tablename__ = "recibo"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    estado = Column(String(50), nullable=False, default="Emitido")
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)


class Pago(Base):
    __tablename__ = "pago"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    monto = Column(Numeric(12, 2), nullable=False)
    estado = Column(String(50), nullable=False, default="Aprobado")
    referencia = Column(String(150), nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    ventaid = Column(Integer, ForeignKey("venta.id"), nullable=False)
    reciboid = Column(Integer, ForeignKey("recibo.id"), nullable=True)
    metodoid = Column(Integer, ForeignKey("metodo_pago.id"), nullable=False)

    venta = relationship("Venta", back_populates="pagos")
    metodo = relationship("MetodoPago")


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
VentaModel = Venta
DetalleVentaModel = DetalleVenta
MetodoPagoModel = MetodoPago
ReciboModel = Recibo
ComprobantePago = Recibo
ComprobantePagoModel = Recibo
PagoModel = Pago

venta = Venta
detalle_venta = DetalleVenta
metodo_pago = MetodoPago
recibo = Recibo
pago = Pago
