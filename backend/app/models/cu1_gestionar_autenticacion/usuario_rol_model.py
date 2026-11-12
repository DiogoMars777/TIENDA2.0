# ==============================================================================
# CU1 - GESTIONAR AUTENTICACION -> CAPA MODELO
# Ubicacion: backend/app/models/cu1_gestionar_autenticacion/usuario_rol_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class Rol(Base):
    __tablename__ = "rol"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)

    usuarios = relationship("Usuario", back_populates="rol")


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=True)
    email = Column(String(150), index=True, nullable=False)
    passwordhash = Column(String(255), nullable=False)
    telefono = Column(String(20), nullable=True)
    rolid = Column(Integer, ForeignKey("rol.id"), nullable=True)
    sucursalid = Column(Integer, ForeignKey("sucursal.id"), nullable=True)
    activo = Column(Boolean, default=True)
    verificado = Column(Boolean, default=False)
    codigoverificacion = Column(String(255), nullable=True)
    codigoexpiracion = Column(DateTime, nullable=True)
    fechacreacion = Column(DateTime, default=get_bolivia_now)

    rol = relationship("Rol", back_populates="usuarios")
    sucursal = relationship("Sucursal", back_populates="usuarios")
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    @property
    def created_at(self):
        return self.fechacreacion

    @property
    def rol_id(self):
        return self.rolid


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
RolModel = Rol
UsuarioModel = Usuario
rol = Rol
usuario = Usuario
