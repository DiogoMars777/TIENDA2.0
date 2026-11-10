# ==============================================================================
# CU25 - GESTIONAR CAMBIOS Y DEVOLUCIONES DE PRENDAS -> CONTROLADOR (MVC)
# Ubicación: backend/app/controllers/cu25_gestionar_cambios_devoluciones/devolucion_controller.py
# ==============================================================================

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.models.models import (
    Venta, DetalleVenta, Inventario,
    MovimientoInventario, Usuario, Tenant, Bitacora
)

from app.services.cu25_gestionar_cambios_devoluciones.devolucion_service import DevolucionService


class DevolucionController:
    """
    Controlador MVC para la gestión de cambios de talla/modelo y devoluciones comerciales.
    """

    @staticmethod
    def validar_venta(
        db: Session,
        tenant_id: int,
        venta_id: Any,
        plazo_dias: int = 15
    ) -> Dict[str, Any]:
        return DevolucionService.validar_venta_para_cambio(
            db=db,
            tenant_id=tenant_id,
            venta_id=venta_id,
            plazo_dias=plazo_dias
        )

    @staticmethod
    def procesar_devolucion(
        db: Session,
        tenant_id: int,
        venta_id: int,
        cliente_id: Optional[int],
        usuario_id: Optional[int],
        sucursal_id: int,
        tipo_devolucion: str,
        motivo: str,
        monto_reembolso: float,
        items: List[Dict[str, Any]]
    ) -> Any:
        return DevolucionService.solicitar_devolucion(
            db=db,
            tenant_id=tenant_id,
            venta_id=venta_id,
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            sucursal_id=sucursal_id,
            tipo_devolucion=tipo_devolucion,
            motivo=motivo,
            monto_reembolso=monto_reembolso,
            items=items
        )

    @staticmethod
    def listar_devoluciones(
        db: Session,
        tenant_id: int,
        sucursal_id: Optional[int] = None,
        tipo: Optional[str] = None
    ) -> List[Any]:
        return DevolucionService.listar_devoluciones(
            db=db,
            tenant_id=tenant_id,
            sucursal_id=sucursal_id,
            tipo=tipo
        )

    @staticmethod
    def obtener_kpis(
        db: Session,
        tenant_id: int,
        plazo_dias: int = 15
    ) -> Dict[str, Any]:
        return DevolucionService.obtener_kpis(
            db=db,
            tenant_id=tenant_id,
            plazo_dias=plazo_dias
        )
