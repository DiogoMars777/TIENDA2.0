# ==============================================================================
# CU21 - ADMINISTRAR PLANES DE SUSCRIPCIÓN Y TENANTS -> CONTROLADOR (MVC)
# Ubicación: backend/app/controllers/cu21_administrar_planes_suscripcion_tenants/suscripcion_tenant_controller.py
# ==============================================================================

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.models.models import (
    PlanSuscripcion, Tenant, Usuario, Bitacora
)

from app.services.cu21_administrar_planes_suscripcion_tenants.suscripcion_tenant_service import SuscripcionTenantService
from app.schemas.cu21_administrar_planes_suscripcion_tenants.suscripcion_tenant_schema import (
    PlanSuscripcionCreate, PlanSuscripcionUpdate, TenantCreate, TenantUpdate
)


class SuscripcionTenantController:
    """
    Controlador de negocio para la gestión Multi-Tenant SaaS (CU21).
    Coordina la interacción entre la API REST (Vistas) y la capa de Servicios.
    """

    # --- PLANES ---
    @staticmethod
    def listar_planes(db: Session, solo_activos: bool = False) -> List[Any]:
        return SuscripcionTenantService.listar_planes(db, solo_activos=solo_activos)

    @staticmethod
    def obtener_plan(db: Session, plan_id: int) -> Optional[Any]:
        return SuscripcionTenantService.obtener_plan_por_id(db, plan_id)

    @staticmethod
    def crear_plan(db: Session, data: PlanSuscripcionCreate, usuario_id: Optional[int] = None) -> Any:
        return SuscripcionTenantService.crear_plan(db, data, usuario_id=usuario_id)

    @staticmethod
    def actualizar_plan(db: Session, plan_id: int, data: PlanSuscripcionUpdate, usuario_id: Optional[int] = None) -> Any:
        return SuscripcionTenantService.actualizar_plan(db, plan_id, data, usuario_id=usuario_id)

    # --- TENANTS ---
    @staticmethod
    def listar_tenants(db: Session) -> List[Dict[str, Any]]:
        return SuscripcionTenantService.listar_tenants_enriquecidos(db)

    @staticmethod
    def obtener_tenant(db: Session, tenant_id: int) -> Optional[Dict[str, Any]]:
        return SuscripcionTenantService.obtener_tenant_detalle(db, tenant_id)

    @staticmethod
    def registrar_tenant(db: Session, data: TenantCreate, usuario_id: Optional[int] = None) -> Any:
        return SuscripcionTenantService.crear_tenant_completo(db, data, usuario_id=usuario_id)

    @staticmethod
    def cambiar_plan_tenant(
        db: Session,
        tenant_id: int,
        nuevo_plan_id: int,
        motivo: Optional[str] = None,
        usuario_id: Optional[int] = None
    ) -> Any:
        return SuscripcionTenantService.cambiar_plan_tenant(
            db, tenant_id=tenant_id, nuevo_plan_id=nuevo_plan_id, motivo=motivo, usuario_id=usuario_id
        )

    @staticmethod
    def toggle_tenant_estado(
        db: Session,
        tenant_id: int,
        activo: bool,
        motivo: Optional[str] = None,
        usuario_id: Optional[int] = None
    ) -> Any:
        return SuscripcionTenantService.toggle_tenant_estado(
            db, tenant_id=tenant_id, activo=activo, motivo=motivo, usuario_id=usuario_id
        )

    @staticmethod
    def renovar_suscripcion(
        db: Session,
        tenant_id: int,
        meses: int,
        metodo_pago: str = "TRANSFERENCIA_BANCARIA",
        usuario_id: Optional[int] = None
    ) -> Any:
        return SuscripcionTenantService.renovar_suscripcion(
            db, tenant_id=tenant_id, meses=meses, metodo_pago=metodo_pago, usuario_id=usuario_id
        )

    @staticmethod
    def obtener_kpis(db: Session) -> Dict[str, Any]:
        return SuscripcionTenantService.obtener_kpis_saas(db)

    @staticmethod
    def asignar_administrador_tenant(
        db: Session,
        tenant_id: int,
        nombre: str,
        apellido: Optional[str],
        email: str,
        password: str,
        usuario_id: Optional[int] = None
    ) -> Dict[str, Any]:
        return SuscripcionTenantService.asignar_administrador_tenant(
            db=db,
            tenant_id=tenant_id,
            nombre=nombre,
            apellido=apellido,
            email=email,
            password=password,
            usuario_id=usuario_id
        )
