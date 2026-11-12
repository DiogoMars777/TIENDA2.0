# ==============================================================================
# CU11 - ATENDER RESERVAS EN SUCURSAL -> CAPA SERVICIO (MVC - SERVICE)
# Arquitectura: Multi-Tenant SaaS con Auditoría (CU26) y Movimientos de Inventario (CU13)
# Ubicación: backend/app/services/cu11_atender_reservas_sucursal/atender_reserva_service.py
# ==============================================================================

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import (
    ReservaModel,
    InventarioSucursalModel,
    MovimientoInventarioModel,
    UsuarioModel,
    SucursalModel,
)
from app.models.saas_tenant.tenant_model import Tenant
from app.schemas.reserva_schema import (
    ReservaResponse,
    AtenderReservaRequest,
)
from app.services.cu10_gestionar_reservas_prendas.reserva_service import (
    ReservaService,
    formatear_reserva,
)
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import (
    BitacoraController,
)
from app.core.timezone import get_bolivia_now


class AtenderReservaService:
    """
    Servicio de Dominio para la atención, despacho, cobranza y cancelación de
    reservas en los mostradores y cajas de sucursales físicas.
    Garantiza aislamiento multitenant, trazabilidad de stock y bitácora de auditoría.
    """

    @classmethod
    def validar_tenant(cls, db: Session, tenant_id: int) -> Tenant:
        """Verifica que el tenant exista en el ecosistema SaaS"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant con ID {tenant_id} no existe en la plataforma SaaS",
            )
        return tenant

    @classmethod
    def listar_reservas_admin(
        cls,
        db: Session,
        sucursal_id: Optional[int] = None,
        estado: Optional[str] = None,
        tenant_id: int = 1,
    ) -> List[ReservaResponse]:
        """
        CU11: Listado administrativo de reservas para el personal de tienda.
        Ejecuta el barrido de expiración automática de 48 horas previo a la consulta.
        """
        cls.validar_tenant(db, tenant_id)

        # Barrido automático de reservas expiradas (+48h)
        ReservaService.verificar_y_expirar_reservas(db, tenant_id=tenant_id)

        query = db.query(ReservaModel).filter(ReservaModel.tenant_id == tenant_id)

        if sucursal_id:
            query = query.filter(ReservaModel.sucursalid == sucursal_id)

        if estado and estado.upper() != "TODAS":
            query = query.filter(ReservaModel.estado == estado.upper())

        reservas = query.order_by(ReservaModel.fechareserva.desc()).all()
        return [formatear_reserva(r) for r in reservas]

    @classmethod
    def buscar_reserva_codigo(
        cls,
        db: Session,
        codigo: str,
        tenant_id: int = 1,
    ) -> ReservaResponse:
        """
        CU11: Búsqueda ágil en mostrador mediante código de voucher (ej: RES-XXXXXX).
        """
        cls.validar_tenant(db, tenant_id)

        # Barrido automático
        ReservaService.verificar_y_expirar_reservas(db, tenant_id=tenant_id)

        limpio = codigo.strip().upper()
        reserva = (
            db.query(ReservaModel)
            .filter(
                ReservaModel.tenant_id == tenant_id,
                ReservaModel.codigoreserva == limpio,
            )
            .first()
        )

        if not reserva:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró ninguna reserva con el código '{limpio}' en esta sucursal/tenant.",
            )

        return formatear_reserva(reserva)

    @classmethod
    def atender_reserva_sucursal(
        cls,
        db: Session,
        reserva_id: int,
        datos: AtenderReservaRequest,
        usuario_staff_id: Optional[int] = None,
        tenant_id: int = 1,
    ) -> ReservaResponse:
        """
        CU11: Procesa la atención física en mostrador:
        - ENTREGAR: Libera 'stockreservado', descuenta 'stockfisico' y genera movimiento de salida.
        - CANCELAR: Libera 'stockreservado' y devuelve la prenda al stock disponible general.
        """
        cls.validar_tenant(db, tenant_id)

        # Barrido automático
        ReservaService.verificar_y_expirar_reservas(db, tenant_id=tenant_id)

        reserva = (
            db.query(ReservaModel)
            .filter(
                ReservaModel.id == reserva_id,
                ReservaModel.tenant_id == tenant_id,
            )
            .first()
        )

        if not reserva:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reserva con ID {reserva_id} no encontrada en este tenant.",
            )

        if reserva.estado in ["ENTREGADA", "CANCELADA", "EXPIRADA"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La reserva ya se encuentra en estado '{reserva.estado}' y no puede modificarse nuevamente.",
            )

        accion = datos.accion.strip().upper()
        staff_user = (
            db.query(UsuarioModel).filter(UsuarioModel.id == usuario_staff_id).first()
            if usuario_staff_id
            else None
        )
        staff_nombre = (
            f"{staff_user.nombre} {staff_user.apellido or ''}".strip()
            if staff_user
            else f"Staff #{usuario_staff_id or 1}"
        )

        sucursal = db.query(SucursalModel).filter(SucursalModel.id == reserva.sucursalid).first()
        nombre_sucursal = sucursal.nombre if sucursal else f"Sucursal #{reserva.sucursalid}"

        if accion == "ENTREGAR":
            era_pagada = reserva.estado == "PAGADA"
            reserva.estado = "ENTREGADA"

            nota = (
                "[Prendas Entregadas en Tienda - Pagada previamente]"
                if era_pagada
                else "[Entregada y Cobrada en Mostrador]"
            )
            if datos.observaciones:
                nota += f" Nota: {datos.observaciones}"
            reserva.observaciones = f"{reserva.observaciones or ''} {nota}".strip()

            # Descontar stock físico y liberar stock reservado
            for d in reserva.detalles:
                inv = (
                    db.query(InventarioSucursalModel)
                    .filter(
                        InventarioSucursalModel.varianteid == d.varianteid,
                        InventarioSucursalModel.sucursalid == reserva.sucursalid,
                        InventarioSucursalModel.tenant_id == tenant_id,
                    )
                    .first()
                )
                if inv:
                    inv.stockreservado = max(0, (inv.stockreservado or 0) - d.cantidad)
                    inv.stockfisico = max(0, (inv.stockfisico or 0) - d.cantidad)

                    # Registrar movimiento de inventario (CU13)
                    mov = MovimientoInventarioModel(
                        tenant_id=tenant_id,
                        tipomovimiento="SALIDA_ENTREGA_RESERVA",
                        cantidad=d.cantidad,
                        motivo=f"Entrega de prendas por reserva #{reserva.codigoreserva}",
                        referencia=reserva.codigoreserva,
                        inventarioid=inv.id,
                        usuarioid=usuario_staff_id or 1,
                        fecha=get_bolivia_now(),
                    )
                    db.add(mov)

            # Registrar auditoría en Bitácora (CU26)
            try:
                res_dto = formatear_reserva(reserva)
                BitacoraController.registrar_evento(
                    db=db,
                    accion="ENTREGAR",
                    modulo="CU11_ATENDER_RESERVAS",
                    usuario_id=usuario_staff_id or 1,
                    detalle=(
                        f"Reserva #{reserva.codigoreserva} entregada y cobrada con éxito en '{nombre_sucursal}' por {staff_nombre}. "
                        f"Prendas despachadas: {len(reserva.detalles)}. Total: Bs. {res_dto.total_estimado}."
                    ),
                    datos_nuevos={
                        "codigo": reserva.codigoreserva,
                        "accion": "ENTREGAR",
                        "sucursal": nombre_sucursal,
                        "staff": staff_nombre,
                        "total": float(res_dto.total_estimado),
                    },
                )
            except Exception as b_err:
                print(f"[Bitácora CU26] Error al auditar entrega: {b_err}")

        elif accion == "CANCELAR":
            reserva.estado = "CANCELADA"
            nota = "[Cancelada en mostrador por desistimiento o inasistencia]"
            if datos.observaciones:
                nota += f" Motivo: {datos.observaciones}"
            reserva.observaciones = f"{reserva.observaciones or ''} {nota}".strip()

            # Solo liberar el stock reservado (el stock físico se mantiene)
            for d in reserva.detalles:
                inv = (
                    db.query(InventarioSucursalModel)
                    .filter(
                        InventarioSucursalModel.varianteid == d.varianteid,
                        InventarioSucursalModel.sucursalid == reserva.sucursalid,
                        InventarioSucursalModel.tenant_id == tenant_id,
                    )
                    .first()
                )
                if inv:
                    inv.stockreservado = max(0, (inv.stockreservado or 0) - d.cantidad)

            # Registrar auditoría en Bitácora (CU26)
            try:
                BitacoraController.registrar_evento(
                    db=db,
                    accion="CANCELAR",
                    modulo="CU11_ATENDER_RESERVAS",
                    usuario_id=usuario_staff_id or 1,
                    detalle=(
                        f"Reserva #{reserva.codigoreserva} cancelada en '{nombre_sucursal}' por {staff_nombre}. "
                        f"Prendas liberadas de reserva hacia inventario disponible."
                    ),
                    datos_nuevos={
                        "codigo": reserva.codigoreserva,
                        "accion": "CANCELAR",
                        "motivo": datos.observaciones or "Inasistencia / Desistimiento",
                    },
                )
            except Exception as b_err:
                print(f"[Bitácora CU26] Error al auditar cancelación: {b_err}")

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Acción '{datos.accion}' no permitida. Use 'ENTREGAR' o 'CANCELAR'.",
            )

        db.commit()
        db.refresh(reserva)
        return formatear_reserva(reserva)
