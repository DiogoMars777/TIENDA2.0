# ==============================================================================
# CU21 - ADMINISTRAR PLANES DE SUSCRIPCIÓN Y TENANTS -> ESQUEMAS PYDANTIC (MVC)
# Ubicación: backend/app/schemas/cu21_administrar_planes_suscripcion_tenants/suscripcion_tenant_schema.py
# ==============================================================================

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# --- ESQUEMAS DE PLANES DE SUSCRIPCIÓN ---

class PlanSuscripcionBase(BaseModel):
    nombre: str = Field(..., max_length=50, description="Nombre descriptivo del plan (ej. Básico, Profesional, Enterprise)")
    descripcion: Optional[str] = Field(None, description="Detalles del alcance del plan")
    precio_mensual: Decimal = Field(..., ge=0, description="Precio mensual en Bolivianos (Bs.)")
    limite_sucursales: int = Field(1, ge=1, description="Máximo de sucursales físicas permitidas")
    limite_usuarios: int = Field(3, ge=1, description="Máximo de colaboradores/usuarios permitidos")
    limite_productos: int = Field(100, ge=1, description="Límite del catálogo de productos")
    habilitar_reportes_ia: bool = Field(False, description="Acceso a Reportes Generativos con IA (CU20)")
    habilitar_vestidor_ia: bool = Field(False, description="Acceso a módulo de Vestidor Virtual con IA")
    activo: bool = Field(True, description="Indica si el plan está disponible comercialmente")


class PlanSuscripcionCreate(PlanSuscripcionBase):
    pass


class PlanSuscripcionUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_mensual: Optional[Decimal] = None
    limite_sucursales: Optional[int] = None
    limite_usuarios: Optional[int] = None
    limite_productos: Optional[int] = None
    habilitar_reportes_ia: Optional[bool] = None
    habilitar_vestidor_ia: Optional[bool] = None
    activo: Optional[bool] = None


class PlanSuscripcionResponse(PlanSuscripcionBase):
    id: int
    fechacreacion: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- ESQUEMAS DE TENANTS (EMPRESAS INQUILINAS) ---

class TenantBase(BaseModel):
    nombre: str = Field(..., max_length=150, description="Razón social o nombre comercial de la boutique")
    slug: str = Field(..., max_length=60, description="Identificador único de URL/subdominio")
    nit_ruc: Optional[str] = Field(None, max_length=30, description="Identificación fiscal NIT o RUC")
    email_contacto: str = Field(..., max_length=120, description="Correo electrónico del administrador")
    telefono_contacto: Optional[str] = Field(None, max_length=30)
    direccion_fiscal: Optional[str] = None
    logo_url: Optional[str] = None


class TenantCreate(TenantBase):
    plan_id: int = Field(..., description="ID del plan de suscripción seleccionado")
    meses_suscripcion: int = Field(12, ge=1, le=36, description="Meses contratados inicialmente (default 1 año)")
    admin_nombre: Optional[str] = Field(None, description="Nombre del administrador de la empresa (Tenant)")
    admin_apellido: Optional[str] = Field(None, description="Apellido del administrador de la empresa (Tenant)")
    admin_email: Optional[str] = Field(None, description="Correo electrónico de acceso del administrador del Tenant")
    admin_password: Optional[str] = Field("Admin123.", description="Contraseña de acceso para el administrador del Tenant")


class AsignarAdminTenantRequest(BaseModel):
    nombre: str = Field(..., description="Nombre del administrador del tenant")
    apellido: Optional[str] = Field("", description="Apellido del administrador del tenant")
    email: str = Field(..., description="Correo de inicio de sesión del administrador del tenant")
    password: str = Field("Admin123.", description="Contraseña del administrador del tenant")


class TenantUpdate(BaseModel):
    nombre: Optional[str] = None
    nit_ruc: Optional[str] = None
    email_contacto: Optional[str] = None
    telefono_contacto: Optional[str] = None
    direccion_fiscal: Optional[str] = None
    logo_url: Optional[str] = None


class TenantCambiarPlanRequest(BaseModel):
    nuevo_plan_id: int = Field(..., description="Nuevo ID del plan a asignar")
    motivo: Optional[str] = Field("Upgrade/Downgrade solicitado por cliente", description="Justificación del cambio")


class TenantToggleEstadoRequest(BaseModel):
    activo: bool = Field(..., description="True para activar, False para suspender acceso")
    motivo: Optional[str] = Field(None, description="Motivo de suspensión o reactivación")


class RenovarSuscripcionRequest(BaseModel):
    meses: int = Field(12, ge=1, le=36, description="Meses a extender la vigencia")
    metodo_pago: Optional[str] = Field("TRANSFERENCIA_BANCARIA", description="Método de pago de renovación")


# --- METRICAS DE CONSUMO Y DETALLE ---

class MetricasUsoTenant(BaseModel):
    sucursales_usadas: int = 0
    sucursales_limite: int = 1
    usuarios_usados: int = 0
    usuarios_limite: int = 3
    productos_usados: int = 0
    productos_limite: int = 100
    porcentaje_sucursales: float = 0.0
    porcentaje_usuarios: float = 0.0


class TenantSuscripcionResponse(BaseModel):
    id: int
    plan_id: int
    plan_nombre: Optional[str] = None
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: str
    monto_pagado: Decimal
    metodo_pago: Optional[str] = None

    class Config:
        from_attributes = True


class TenantResponse(BaseModel):
    id: int
    uuid: str
    nombre: str
    slug: str
    dominio_personalizado: Optional[str] = None
    nit_ruc: Optional[str] = None
    email_contacto: str
    telefono_contacto: Optional[str] = None
    direccion_fiscal: Optional[str] = None
    logo_url: Optional[str] = None
    plan_id: Optional[int] = None
    plan: Optional[PlanSuscripcionResponse] = None
    activo: bool
    fechacreacion: Optional[datetime] = None
    suscripcion_actual: Optional[TenantSuscripcionResponse] = None
    metricas_uso: Optional[MetricasUsoTenant] = None

    class Config:
        from_attributes = True


class KpiSaaSResponse(BaseModel):
    total_tenants: int
    tenants_activos: int
    tenants_suspendidos: int
    mrr_estimado: float
    total_planes: int
    distribucion_planes: Dict[str, int]
