# ==============================================================================
# CU15 - REALIZAR COMPRAS DIGITALES -> CAPA VISTA / RUTAS API (MVC - VIEW)
# Ubicación: backend/app/views/cu15_realizar_compras_digitales/compra_digital_views.py
# ==============================================================================

from fastapi import APIRouter, Depends, status, Query, Header
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import verify_token
from app.core.dependencies import get_current_tenant_user
from app.models.models import UsuarioModel
from app.schemas.orden_schema import (
    OrdenCreate,
    OrdenResponse,
    OrdenTrackingResponse,
    ActualizarEstadoOrdenRequest
)
from app.controllers.cu15_realizar_compras_digitales.compra_digital_controller import CompraDigitalController

router = APIRouter(tags=["CU15 - Realizar Compras Digitales (Web y Móvil)"])


def _resolver_usuario_orden(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
) -> UsuarioModel:
    tenant_id = x_tenant_id or 1
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        email = verify_token(token)
        if email:
            user = db.query(UsuarioModel).filter(UsuarioModel.email == email).first()
            if user:
                return user

    user_tenant = db.query(UsuarioModel).filter(
        UsuarioModel.tenant_id == tenant_id,
        UsuarioModel.activo == True
    ).first()
    if user_tenant:
        return user_tenant

    return db.query(UsuarioModel).filter(UsuarioModel.activo == True).first()


@router.post("/ordenes", response_model=OrdenResponse, status_code=status.HTTP_201_CREATED, summary="Procesar compra digital (App Móvil / Web)")
@router.post("/ordenes/", response_model=OrdenResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/compras/procesar", response_model=OrdenResponse, status_code=status.HTTP_201_CREATED, summary="Alias para procesar compra digital")
def crear_orden_digital(
    data: OrdenCreate,
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(_resolver_usuario_orden)
):
    """
    CU15: Procesa la compra online, valida stock disponible, genera la venta digital,
    emite recibo fiscal, registra el pago, vacía el carrito y asienta en Kardex y Bitácora.
    """
    tenant_id = x_tenant_id or getattr(current_user, 'tenant_id', 1) or 1
    return CompraDigitalController.procesar_orden_digital(
        db=db,
        current_user=current_user,
        data=data,
        tenant_id=tenant_id
    )


@router.get("/ordenes/me", response_model=List[OrdenResponse], summary="Historial de compras y pedidos del cliente autenticado")
def consultar_mis_ordenes(
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(_resolver_usuario_orden)
):
    """
    CU15: Permite al cliente autenticado ver sus compras digitales pasadas y el estado de entrega.
    """
    tenant_id = x_tenant_id or getattr(current_user, 'tenant_id', 1) or 1
    return CompraDigitalController.listar_mis_ordenes(
        db=db,
        current_user=current_user,
        tenant_id=tenant_id
    )


@router.get("/ordenes/{orden_id}/tracking", response_model=OrdenTrackingResponse, summary="Consultar tracking y timeline de entrega de una orden")
def consultar_tracking(
    orden_id: int,
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_tenant_user)
):
    """
    CU15: Consulta las etapas de despacho de la orden (Confirmado -> Preparación -> En Camino -> Entregado).
    """
    tenant_id = getattr(current_user, 'tenant_id', 1) or 1
    return CompraDigitalController.consultar_tracking(
        db=db,
        orden_id=orden_id,
        current_user=current_user,
        tenant_id=tenant_id
    )


@router.put("/ordenes/{orden_id}/estado", summary="Actualizar estado logístico de la orden (Admin/Personal)")
def actualizar_estado_orden(
    orden_id: int,
    req: ActualizarEstadoOrdenRequest,
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_tenant_user)
):
    """
    CU15: Permite al encargado/administrador avanzar el estado logístico de un pedido online.
    """
    tenant_id = getattr(current_user, 'tenant_id', 1) or 1
    return CompraDigitalController.actualizar_estado_orden(
        db=db,
        orden_id=orden_id,
        req=req,
        usuario_actual=current_user,
        tenant_id=tenant_id
    )
