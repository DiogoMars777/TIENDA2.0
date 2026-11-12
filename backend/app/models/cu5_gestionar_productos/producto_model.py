# ==============================================================================
# CU5 - GESTIONAR PRODUCTOS -> CAPA MODELO
# Producto, Color, Talla y sus Variantes (combinacion color+talla)
# Ubicacion: backend/app/models/cu5_gestionar_productos/producto_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class Producto(Base):
    __tablename__ = "producto"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    marca = Column(String(100), nullable=True)
    genero = Column(String(50), nullable=True)
    grupoedad = Column(String(50), nullable=True)
    preciobase = Column(Numeric(10, 2), nullable=False, default=0.00)
    imagenprincipal = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)
    fechacreacion = Column(DateTime, default=get_bolivia_now)
    fechaactualizacion = Column(DateTime, default=get_bolivia_now, onupdate=get_bolivia_now)
    categoriaid = Column(Integer, ForeignKey("categoria.id"), nullable=True)

    categoria = relationship("Categoria", back_populates="productos")
    variantes = relationship("VarianteProducto", back_populates="producto")

    @property
    def precio(self):
        return self.preciobase

    @property
    def imagen_url(self):
        return self.imagenprincipal

    @property
    def categoria_id(self):
        return self.categoriaid

    @property
    def stock(self):
        return 20


class Color(Base):
    __tablename__ = "color"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    codigohex = Column(String(10), nullable=True)
    activo = Column(Boolean, default=True)


class Talla(Base):
    __tablename__ = "talla"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(20), nullable=False)
    grupoedad = Column(String(50), nullable=True)
    orden = Column(Integer, default=0)
    activo = Column(Boolean, default=True)


class VarianteProducto(Base):
    __tablename__ = "variante_producto"

    id = Column(Integer, primary_key=True, index=True)
    productoid = Column(Integer, ForeignKey("producto.id"), nullable=False)
    colorid = Column(Integer, ForeignKey("color.id"), nullable=True)
    tallaid = Column(Integer, ForeignKey("talla.id"), nullable=True)
    sku = Column(String(50), nullable=True)
    codigobarra = Column(String(100), nullable=True)
    imagenurl = Column(Text, nullable=True)
    precioventa = Column(Numeric(10, 2), nullable=True)
    activo = Column(Boolean, default=True)
    fechacreacion = Column(DateTime, default=get_bolivia_now)

    producto = relationship("Producto", back_populates="variantes")
    color = relationship("Color")
    talla = relationship("Talla")


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
ProductoModel = Producto
ColorModel = Color
TallaModel = Talla
VarianteProductoModel = VarianteProducto

producto = Producto
color = Color
talla = Talla
variante_producto = VarianteProducto
