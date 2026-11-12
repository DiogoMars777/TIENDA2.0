# ==============================================================================
# MODELOS SAAS MULTI-TENANT (MVC - MODEL)
# Ubicación: backend/app/models/saas_tenant/tenant_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.timezone import get_bolivia_now


class PlanSuscripcion(Base):
    __tablename__ = "plan_suscripcion"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    precio_mensual = Column(Numeric(10, 2), nullable=False)
    limite_sucursales = Column(Integer, nullable=False, default=1)
    limite_usuarios = Column(Integer, nullable=False, default=3)
    limite_productos = Column(Integer, nullable=False, default=100)
    habilitar_reportes_ia = Column(Boolean, default=False)
    habilitar_vestidor_ia = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    fechacreacion = Column(DateTime, default=get_bolivia_now)

    tenants = relationship("Tenant", back_populates="plan")
    suscripciones = relationship("TenantSuscripcion", back_populates="plan")


class Tenant(Base):
    __tablename__ = "tenant"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    slug = Column(String(60), unique=True, nullable=False, index=True)
    dominio_personalizado = Column(String(150), unique=True, nullable=True)
    nit_ruc = Column(String(30), nullable=True)
    email_contacto = Column(String(120), nullable=False)
    telefono_contacto = Column(String(30), nullable=True)
    direccion_fiscal = Column(Text, nullable=True)
    logo_url = Column(Text, nullable=True)
    plan_id = Column(Integer, ForeignKey("plan_suscripcion.id"), nullable=True)
    activo = Column(Boolean, default=True)
    fechacreacion = Column(DateTime, default=get_bolivia_now)

    plan = relationship("PlanSuscripcion", back_populates="tenants")
    configuracion = relationship("TenantConfiguracion", back_populates="tenant", uselist=False)
    suscripciones = relationship("TenantSuscripcion", back_populates="tenant")


class TenantConfiguracion(Base):
    __tablename__ = "tenant_configuracion"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), unique=True, nullable=False)
    moneda_simbolo = Column(String(10), default="Bs.")
    moneda_iso = Column(String(5), default="BOB")
    zona_horaria = Column(String(50), default="America/La_Paz")
    tiempo_expiracion_reserva_horas = Column(Integer, default=48)
    color_primario_hex = Column(String(10), default="#0d1b2a")
    color_secundario_hex = Column(String(10), default="#d4af37")
    paypal_client_id = Column(Text, nullable=True)
    paypal_client_secret = Column(Text, nullable=True)
    qr_banco_cuenta = Column(String(60), nullable=True)
    whatsapp_notificaciones = Column(String(30), nullable=True)

    tenant = relationship("Tenant", back_populates="configuracion")


class TenantSuscripcion(Base):
    __tablename__ = "tenant_suscripcion"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plan_suscripcion.id"), nullable=False)
    fecha_inicio = Column(DateTime, default=get_bolivia_now, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)
    estado = Column(String(20), default="ACTIVA")
    monto_pagado = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(String(50), nullable=True)

    tenant = relationship("Tenant", back_populates="suscripciones")
    plan = relationship("PlanSuscripcion", back_populates="suscripciones")


class DireccionCliente(Base):
    __tablename__ = "direccioncliente"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    cliente_id = Column(Integer, ForeignKey("cliente.id", ondelete="CASCADE"), nullable=True)
    nombre = Column(String(100), nullable=True)
    direccion = Column(String(255), nullable=False)
    referencia = Column(String(255), nullable=True)
    ciudad = Column(String(80), nullable=True)
    departamento = Column(String(80), nullable=True)
    telefono = Column(String(30), nullable=True)
    esprincipal = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)


class EventoCliente(Base):
    __tablename__ = "evento_cliente"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    cliente_id = Column(Integer, ForeignKey("cliente.id", ondelete="CASCADE"), nullable=True)
    tipoevento = Column(String(80), nullable=False)
    fecha = Column(DateTime, default=get_bolivia_now)
    datos_metadata = Column("metadata", Text, nullable=True)


class PruebaVirtual(Base):
    __tablename__ = "prueba_virtual"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    cliente_id = Column(Integer, ForeignKey("cliente.id", ondelete="SET NULL"), nullable=True)
    variante_id = Column(Integer, ForeignKey("variante_producto.id", ondelete="SET NULL"), nullable=True)
    imagenresultadourl = Column(Text, nullable=False)
    dispositivo = Column(String(50), nullable=True)
    fecha = Column(DateTime, default=get_bolivia_now)


class ProductoColeccion(Base):
    __tablename__ = "producto_coleccion"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("producto.id", ondelete="CASCADE"), nullable=False)
    coleccion_id = Column(Integer, ForeignKey("coleccion.id", ondelete="CASCADE"), nullable=False)
    cantidad = Column(Integer, default=1)


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
PlanSuscripcionModel = PlanSuscripcion
TenantModel = Tenant
TenantConfiguracionModel = TenantConfiguracion
TenantSuscripcionModel = TenantSuscripcion
DireccionClienteModel = DireccionCliente
EventoClienteModel = EventoCliente
PruebaVirtualModel = PruebaVirtual
ProductoColeccionModel = ProductoColeccion

plan_suscripcion = PlanSuscripcion
tenant = Tenant
tenant_configuracion = TenantConfiguracion
tenant_suscripcion = TenantSuscripcion
direccioncliente = DireccionCliente
evento_cliente = EventoCliente
prueba_virtual = PruebaVirtual
producto_coleccion = ProductoColeccion
