# ==============================================================================
# CU26 - GESTIONAR BITACORA Y AUDITORIA -> CAPA VISTA / RUTAS API (MVC - VIEW)
# Ubicación: backend/app/views/cu26_gestionar_bitacora/bitacora_views.py
# ==============================================================================

from fastapi import APIRouter, Depends, Query, Request, Response, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_tenant_user
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
from app.schemas.cu26_gestionar_bitacora.bitacora_schema import (
    BitacoraCreate, BitacoraResponse, BitacoraListResponse, BitacoraStatsResponse
)

router = APIRouter(prefix="/bitacora", tags=["CU26 - Bitácora y Auditoría del Sistema (Web)"])


def _require_superadmin(current_user: UsuarioModel, db: Session):
    """Restringe la consulta de la Bitácora exclusivamente al SUPERADMIN del sistema."""
    rol_nombre = ""
    if current_user.rol and current_user.rol.nombre:
        rol_nombre = current_user.rol.nombre.strip().upper()
    elif current_user.rolid:
        from app.models.models import RolModel
        r = db.query(RolModel).filter(RolModel.id == current_user.rolid).first()
        if r and r.nombre:
            rol_nombre = r.nombre.strip().upper()
    if rol_nombre != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: La Bitácora del Sistema es exclusiva del Administrador General (SUPERADMIN)."
        )


@router.get("", response_model=BitacoraListResponse, summary="Listar registros de auditoría (Solo SUPERADMIN)")
def listar_bitacora(
    fecha_inicio: Optional[datetime] = Query(None, description="Fecha de inicio (ISO 8601)"),
    fecha_fin: Optional[datetime] = Query(None, description="Fecha de fin (ISO 8601)"),
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Filtrar por acción"),
    usuario_id: Optional[int] = Query(None, description="Filtrar por ID de usuario"),
    search: Optional[str] = Query(None, description="Búsqueda por texto (detalle, IP, usuario)"),
    limit: int = Query(50, ge=1, le=200, description="Cantidad de registros por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento / paginación"),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_tenant_user)
):
    """Retorna el historial paginado global de bitácora (Exclusivo SUPERADMIN)."""
    _require_superadmin(current_user, db)
    return BitacoraController.listar(
        db=db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        modulo=modulo,
        accion=accion,
        usuario_id=usuario_id,
        search=search,
        limit=limit,
        offset=offset,
        tenant_id=None
    )


@router.get("/estadisticas", response_model=BitacoraStatsResponse, summary="Obtener KPIs y métricas de auditoría (Solo SUPERADMIN)")
def obtener_estadisticas_bitacora(
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_tenant_user)
):
    """Retorna indicadores clave globales de bitácora (Exclusivo SUPERADMIN)."""
    _require_superadmin(current_user, db)
    return BitacoraController.obtener_estadisticas(db=db, tenant_id=None)


@router.get("/exportar", summary="Exportar registros filtrados a archivo CSV (Solo SUPERADMIN)")
def exportar_bitacora_csv(
    fecha_inicio: Optional[datetime] = Query(None),
    fecha_fin: Optional[datetime] = Query(None),
    modulo: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    usuario_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_tenant_user)
):
    """Genera y descarga un archivo CSV con los registros de auditoría (Exclusivo SUPERADMIN)."""
    _require_superadmin(current_user, db)
    csv_data = BitacoraController.exportar_csv(
        db=db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        modulo=modulo,
        accion=accion,
        usuario_id=usuario_id,
        search=search,
        tenant_id=None
    )

    filename = f"bitacora_auditoria_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Registrar evento manual en bitácora")
def crear_evento_bitacora(
    evento: BitacoraCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_tenant_user)
):
    """Permite registrar un evento de auditoría."""
    tenant_id = getattr(current_user, 'tenant_id', 1) or 1
    ip_cliente = evento.ip or (request.client.host if request.client else None)
    usuario_efectivo = evento.usuarioid if evento.usuarioid is not None else current_user.id

    nuevo = BitacoraController.registrar_evento(
        db=db,
        accion=evento.accion,
        modulo=evento.modulo,
        usuario_id=usuario_efectivo,
        detalle=evento.detalle,
        ip=ip_cliente,
        datos_previos=evento.datosprevios,
        datos_nuevos=evento.datosnuevos,
        tenant_id=tenant_id
    )

    if not nuevo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar el evento en la bitácora"
        )

    return {"mensaje": "Evento registrado con éxito", "id": nuevo.id}
