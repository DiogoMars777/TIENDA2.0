# ==============================================================================
# CU4 - GESTIONAR SUCURSALES -> CAPA MODELO
# Ubicacion: backend/app/models/cu4_gestionar_sucursales/sucursal_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class Sucursal(Base):
    __tablename__ = "sucursal"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    nombre = Column(String(100), nullable=False)
    ciudad = Column(String(100), nullable=True)
    direccion = Column(String(255), nullable=True)
    telefono = Column(String(20), nullable=True)
    latitud = Column(Numeric(10, 8), nullable=True)
    longitud = Column(Numeric(11, 8), nullable=True)
    activo = Column(Boolean, default=True)
    fechacreacion = Column(DateTime, default=get_bolivia_now)

    usuarios = relationship("Usuario", back_populates="sucursal")


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
SucursalModel = Sucursal
sucursal = Sucursal
