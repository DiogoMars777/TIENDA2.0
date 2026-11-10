# ==============================================================================
# CU10 - GESTIONAR RESERVAS DE PRENDAS -> CAPA VISTA / RUTAS API (MVC - VIEW)
# Ubicación: backend/app/views/cu10_gestionar_reservas_prendas/reserva_views.py
# ==============================================================================

from fastapi import APIRouter, Depends, status, Header, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import verify_token
from app.models.models import UsuarioModel
from app.models.saas_tenant.tenant_model import Tenant
from app.schemas.reserva_schema import (
    ReservaResponse,
    ReservaCreate,
    CancelarReservaRequest,
    PagarReservaRequest,
)
from app.controllers.cu10_gestionar_reservas_prendas.reserva_controller import (
    ReservaController,
)

router = APIRouter(prefix="/reservas", tags=["CU10 - Reservas de Prendas"])


def get_current_user_id(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
) -> int:
    """Extrae el ID del usuario del token JWT respetando el tenant; si es invitado, usa o crea el usuario del tenant"""
    tenant_id = x_tenant_id or 1

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant con ID {tenant_id} no existe en la plataforma SaaS"
        )

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        email = verify_token(token)
        if email:
            user = db.query(UsuarioModel).filter(
                UsuarioModel.email == email,
                UsuarioModel.tenant_id == tenant_id
            ).first()
            if not user:
                user = db.query(UsuarioModel).filter(
                    UsuarioModel.email == email
                ).first()
            if user:
                return user.id

    user_tenant = db.query(UsuarioModel).filter(
        UsuarioModel.tenant_id == tenant_id,
        UsuarioModel.activo == True
    ).first()

    if user_tenant:
        return user_tenant.id

    from app.core.security import get_password_hash
    nuevo_user = UsuarioModel(
        nombre=f"Cliente Tenant {tenant_id}",
        apellido="Invitado",
        email=f"cliente_tenant{tenant_id}@tienda.bo",
        passwordhash=get_password_hash("guest123"),
        telefono="70000000",
        tenant_id=tenant_id,
        rolid=3,
        activo=True
    )
    db.add(nuevo_user)
    db.commit()
    db.refresh(nuevo_user)
    return nuevo_user.id


@router.post("", response_model=ReservaResponse, status_code=status.HTTP_201_CREATED, summary="Crear reserva de prendas")
def crear_reserva(
    datos: ReservaCreate,
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    usuario_id: int = Depends(get_current_user_id),
):
    """
    CU10: Convierte los ítems seleccionados o del carrito en una Reserva física en sucursal.
    Genera un código único alfanumérico (ej: RES-XXXXXX), bloquea stock por 48 horas y valida cuotas de reservas activas.
    """
    tenant_id = x_tenant_id or 1
    return ReservaController.crear_reserva(
        db=db,
        usuario_id=usuario_id,
        datos=datos,
        tenant_id=tenant_id
    )


@router.get("/mis-reservas", response_model=List[ReservaResponse], summary="Listar reservas del cliente autenticado")
def listar_mis_reservas(
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    usuario_id: int = Depends(get_current_user_id),
):
    """
    CU10: Retorna el historial y estado de todas las reservas efectuadas por el cliente en el tenant, con cálculo de expiración.
    """
    tenant_id = x_tenant_id or 1
    return ReservaController.listar_reservas_usuario(
        db=db,
        usuario_id=usuario_id,
        tenant_id=tenant_id
    )


@router.get("/{id_o_codigo}", response_model=ReservaResponse, summary="Obtener detalle de reserva por ID o código")
def obtener_reserva(
    id_o_codigo: str,
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    usuario_id: int = Depends(get_current_user_id),
):
    """
    CU10: Consulta la información completa de una reserva usando su ID o su código alfanumérico.
    """
    tenant_id = x_tenant_id or 1
    return ReservaController.obtener_reserva_por_id_o_codigo(
        db=db,
        id_o_codigo=id_o_codigo,
        usuario_id=usuario_id,
        tenant_id=tenant_id
    )


@router.patch("/{reserva_id}/cancelar", response_model=ReservaResponse, summary="Cancelar reserva pendiente por el cliente")
def cancelar_reserva(
    reserva_id: int,
    datos: Optional[CancelarReservaRequest] = None,
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    usuario_id: int = Depends(get_current_user_id),
):
    """
    CU10: Cancela una reserva que se encuentre en estado PENDIENTE y libera inmediatamente el stock reservado en la tienda física.
    """
    tenant_id = x_tenant_id or 1
    motivo = datos.motivo if datos else None
    return ReservaController.cancelar_reserva(
        db=db,
        reserva_id=reserva_id,
        usuario_id=usuario_id,
        motivo=motivo,
        tenant_id=tenant_id
    )


@router.post("/{reserva_id}/pagar", response_model=ReservaResponse, summary="Pagar reserva (Móvil o Tienda)")
def pagar_reserva(
    reserva_id: int,
    datos: PagarReservaRequest,
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    usuario_id: int = Depends(get_current_user_id),
):
    """
    Registra el pago de una reserva realizada desde la app móvil o mostrador, actualizando su estado a 'PAGADA'.
    """
    tenant_id = x_tenant_id or 1
    return ReservaController.pagar_reserva(
        db=db,
        reserva_id=reserva_id,
        metodo_pago=datos.metodo_pago,
        referencia=datos.referencia,
        origen=datos.origen or "MOVIL",
        tenant_id=tenant_id
    )
