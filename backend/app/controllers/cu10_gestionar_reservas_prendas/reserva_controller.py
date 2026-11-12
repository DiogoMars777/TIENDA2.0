# ==============================================================================
# CU10 - GESTIONAR RESERVAS DE PRENDAS -> CAPA CONTROLADOR (MVC - CONTROLLER)
# Arquitectura: Multi-Tenant SaaS con Vencimiento 48h y Bloqueo de Stock
# Ubicación: backend/app/controllers/cu10_gestionar_reservas_prendas/reserva_controller.py
# ==============================================================================

from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.models import (
    Reserva, ReservaDetalle, Carrito, CarritoItem,
    Inventario, Sucursal, VarianteProducto, Producto,
    Usuario, Tenant
)
from app.services.cu10_gestionar_reservas_prendas.reserva_service import (
    ReservaService, formatear_reserva, generar_codigo_reserva
)
from app.schemas.reserva_schema import ReservaCreate, ReservaResponse


class ReservaController:
    """
    Controlador MVC para la administración de Reservas de prendas físicas.
    Orquesta la lógica de negocio, validaciones multitenant y trazabilidad de estados.
    """

    @staticmethod
    def crear_reserva(
        db: Session,
        usuario_id: int,
        datos: ReservaCreate,
        tenant_id: int = 1
    ) -> ReservaResponse:
        """Crea una reserva física con vencimiento de 48h y bloqueo temporal de stock"""
        return ReservaService.crear_reserva(
            db=db,
            usuario_id=usuario_id,
            datos=datos,
            tenant_id=tenant_id
        )

    @staticmethod
    def listar_reservas_usuario(
        db: Session,
        usuario_id: int,
        tenant_id: int = 1,
        codigos_dispositivo: Optional[List[str]] = None
    ) -> List[ReservaResponse]:
        """Obtiene las reservas del usuario en el tenant ordenadas cronológicamente"""
        return ReservaService.listar_reservas_usuario(
            db=db,
            usuario_id=usuario_id,
            tenant_id=tenant_id,
            codigos_dispositivo=codigos_dispositivo
        )

    @staticmethod
    def obtener_reserva_por_id_o_codigo(
        db: Session,
        id_o_codigo: str,
        usuario_id: Optional[int] = None,
        tenant_id: int = 1
    ) -> ReservaResponse:
        """Consulta el detalle de una reserva por su ID o código único"""
        return ReservaService.obtener_reserva_por_id_o_codigo(
            db=db,
            id_o_codigo=id_o_codigo,
            usuario_id=usuario_id,
            tenant_id=tenant_id
        )

    @staticmethod
    def cancelar_reserva(
        db: Session,
        reserva_id: int,
        usuario_id: int,
        motivo: Optional[str] = None,
        tenant_id: int = 1
    ) -> ReservaResponse:
        """Cancela una reserva pendiente y libera el stockreservado"""
        return ReservaService.cancelar_reserva(
            db=db,
            reserva_id=reserva_id,
            usuario_id=usuario_id,
            motivo=motivo,
            tenant_id=tenant_id
        )

    @staticmethod
    def pagar_reserva(
        db: Session,
        reserva_id: int,
        metodo_pago: str,
        referencia: Optional[str] = None,
        origen: str = "MOVIL",
        tenant_id: int = 1
    ) -> ReservaResponse:
        """Registra el pago de una reserva (móvil o en caja física)"""
        return ReservaService.pagar_reserva(
            db=db,
            reserva_id=reserva_id,
            metodo_pago=metodo_pago,
            referencia=referencia,
            origen=origen,
            tenant_id=tenant_id
        )

    # Aliases de compatibilidad hacia atrás
    crear_reserva_desde_carrito = crear_reserva
    cancelar_reserva_cliente = cancelar_reserva
