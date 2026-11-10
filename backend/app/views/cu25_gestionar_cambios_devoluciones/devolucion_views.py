# ==============================================================================
# CU25 - GESTIONAR CAMBIOS Y DEVOLUCIONES DE PRENDAS -> VISTAS (MVC - VIEW / ROUTER)
# Ubicación: backend/app/views/cu25_gestionar_cambios_devoluciones/devolucion_views.py
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.controllers.cu25_gestionar_cambios_devoluciones.devolucion_controller import DevolucionController
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.schemas.cu25_gestionar_cambios_devoluciones.devolucion_schema import (
    SolicitudDevolucionRequest,
    ValidarVentaDevolucionResponse,
    DevolucionResponse,
    DevolucionKpisResponse
)

router = APIRouter(prefix="/devoluciones", tags=["CU25 - Cambios y Devoluciones"])


@router.post(
    "/solicitar",
    response_model=DevolucionResponse,
    summary="Registrar y ejecutar cambio de prenda, talla o devolución con reintegro a stock"
)
def solicitar_devolucion(
    req: SolicitudDevolucionRequest,
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_user)
):
    """
    Registra la operación de cambio o devolución.
    Reincorpora prendas en perfecto estado al stock comercial en Inventario, genera movimientos
    en Kardex, emite el código de comprobante oficial, notifica al cliente y audita en Bitácora (CU26).
    """
    tenant_id = getattr(current_user, "tenant_id", 1) or 1
    items_dict = [it.dict() for it in req.items]
    try:
        devolucion = DevolucionController.procesar_devolucion(
            db=db,
            tenant_id=tenant_id,
            venta_id=req.venta_id,
            cliente_id=req.cliente_id,
            usuario_id=current_user.id,
            sucursal_id=req.sucursal_id,
            tipo_devolucion=req.tipo_devolucion,
            motivo=req.motivo,
            monto_reembolso=req.monto_reembolso,
            items=items_dict
        )
        return devolucion
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la devolución: {str(e)}"
        )


@router.get(
    "/validar-venta/{venta_id}",
    response_model=ValidarVentaDevolucionResponse,
    summary="Validar si una venta califica para cambio/devolución dentro del plazo (por ID o Código de Venta)"
)
def validar_venta(
    venta_id: str,
    plazo_dias: int = Query(15, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_user)
):
    """
    Verifica si una venta previa está dentro del plazo de garantía (15 días por defecto)
    y retorna la lista de prendas compradas para seleccionarlas en el formulario de cambio.
    """
    tenant_id = getattr(current_user, "tenant_id", 1) or 1
    return DevolucionController.validar_venta(
        db=db,
        tenant_id=tenant_id,
        venta_id=venta_id,
        plazo_dias=plazo_dias
    )


@router.get(
    "/kpis",
    response_model=DevolucionKpisResponse,
    summary="Obtener métricas ejecutivas de cambios, mermas y devoluciones"
)
def obtener_kpis_devoluciones(
    plazo_dias: int = Query(15, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_user)
):
    """
    Retorna métricas gerenciales: total operaciones, prendas aptas vs dadas de baja por defecto,
    monto total reembolsado o acreditado.
    """
    tenant_id = getattr(current_user, "tenant_id", 1) or 1
    return DevolucionController.obtener_kpis(
        db=db,
        tenant_id=tenant_id,
        plazo_dias=plazo_dias
    )


@router.get(
    "/",
    response_model=List[DevolucionResponse],
    summary="Listar historial de cambios y devoluciones de prendas"
)
def listar_devoluciones(
    sucursal_id: Optional[int] = Query(None, description="Filtrar por sucursal"),
    tipo: Optional[str] = Query(None, description="Filtrar por CAMBIO_TALLA, CAMBIO_PRENDA, REEMBOLSO_TOTAL, NOTA_CREDITO"),
    db: Session = Depends(get_db),
    current_user: UsuarioModel = Depends(get_current_user)
):
    """
    Recupera el histórico completo de cambios y devoluciones con prendas devueltas y entregadas.
    """
    tenant_id = getattr(current_user, "tenant_id", 1) or 1
    return DevolucionController.listar_devoluciones(
        db=db,
        tenant_id=tenant_id,
        sucursal_id=sucursal_id,
        tipo=tipo
    )
