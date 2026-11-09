# ==============================================================================
# CU15 - REALIZAR COMPRAS DIGITALES -> CAPA CONTROLADOR (MVC - CONTROLLER)
# Ubicación: backend/app/controllers/cu15_realizar_compras_digitales/compra_digital_controller.py
# ==============================================================================

from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from app.models.models import (
    Venta, DetalleVenta, Pago, MetodoPago,
    Carrito, CarritoItem, Usuario, Cliente,
    Sucursal, Inventario, VarianteProducto,
    Tenant, Bitacora
)

# Alias de tipo ORM
UsuarioModel = Usuario
from app.schemas.orden_schema import OrdenCreate, ActualizarEstadoOrdenRequest
from app.services.cu15_realizar_compras_digitales.compra_digital_service import CompraDigitalService


class CompraDigitalController:

    @staticmethod
    def procesar_orden_digital(
        db: Session,
        current_user: UsuarioModel,
        data: OrdenCreate,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        CU15: Delegación al servicio de compras digitales para validar stock,
        crear orden digital, asentar kardex y generar comprobante.
        """
        return CompraDigitalService.procesar_orden_digital(
            db=db,
            current_user=current_user,
            data=data,
            tenant_id=tenant_id
        )

    @staticmethod
    def listar_mis_ordenes(
        db: Session,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        CU15: Consulta del historial de órdenes del cliente autenticado.
        """
        return CompraDigitalService.listar_mis_ordenes(
            db=db,
            current_user=current_user,
            tenant_id=tenant_id
        )

    @staticmethod
    def consultar_tracking(
        db: Session,
        orden_id: int,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        CU15: Consulta del timeline y etapas de despacho de la orden.
        """
        return CompraDigitalService.consultar_tracking(
            db=db,
            orden_id=orden_id,
            current_user=current_user,
            tenant_id=tenant_id
        )

    @staticmethod
    def actualizar_estado_orden(
        db: Session,
        orden_id: int,
        req: ActualizarEstadoOrdenRequest,
        usuario_actual: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        CU15: Actualización del estado logístico de la orden digital.
        """
        return CompraDigitalService.actualizar_estado_orden(
            db=db,
            orden_id=orden_id,
            req=req,
            usuario_actual=usuario_actual,
            tenant_id=tenant_id
        )
