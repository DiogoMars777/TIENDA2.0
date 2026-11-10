# ==============================================================================
# CU19 - GESTIONAR NOTIFICACIONES -> CAPA VISTA / RUTAS API (MVC - VIEW)
# Ubicación: backend/app/views/cu19_gestionar_notificaciones/notificacion_views.py
# ==============================================================================

from fastapi import APIRouter, Depends, status, Header
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.core.security import verify_token
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.controllers.cu19_gestionar_notificaciones.notificacion_controller import NotificacionController

router = APIRouter(prefix="/notificaciones", tags=["CU19 - Gestionar Notificaciones (Web y Móvil)"])


def _resolver_usuario_notif(
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


@router.get("", summary="Listar notificaciones del usuario (con detección de vencimientos y stock)")
def listar_notificaciones(
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(_resolver_usuario_notif)
):
    """CU19: Retorna lista de notificaciones activas para el usuario conectado."""
    tenant_id = x_tenant_id or getattr(current_user, 'tenant_id', 1) or 1
    return NotificacionController.listar_notificaciones(db=db, current_user=current_user, tenant_id=tenant_id)


@router.get("/contador", summary="Contar notificaciones no leídas para insignia/badge")
def contar_no_leidas(
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(_resolver_usuario_notif)
):
    """CU19: Retorna la cantidad de alertas no leídas."""
    tenant_id = x_tenant_id or getattr(current_user, 'tenant_id', 1) or 1
    conteo = NotificacionController.contar_no_leidas(db=db, current_user=current_user, tenant_id=tenant_id)
    return {"no_leidas": conteo}


@router.patch("/{notificacion_id}/leer", summary="Marcar una notificación como leída")
def marcar_leida(
    notificacion_id: int,
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(_resolver_usuario_notif)
):
    """CU19: Actualiza el estado a leído = True."""
    tenant_id = x_tenant_id or getattr(current_user, 'tenant_id', 1) or 1
    ok = NotificacionController.marcar_como_leida(db=db, current_user=current_user, notificacion_id=notificacion_id, tenant_id=tenant_id)
    return {"exito": ok}


@router.post("/marcar-todas-leidas", summary="Marcar todas las notificaciones como leídas")
def marcar_todas(
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(_resolver_usuario_notif)
):
    """CU19: Marca todas las notificaciones pendientes como leídas."""
    tenant_id = x_tenant_id or getattr(current_user, 'tenant_id', 1) or 1
    ok = NotificacionController.marcar_todas_leidas(db=db, current_user=current_user, tenant_id=tenant_id)
    return {"exito": ok}

