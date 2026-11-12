# ==============================================================================
# CU24 - GESTIONAR CANCELACIÓN Y VENCIMIENTO DE RESERVAS -> SERVICIO (MVC - SERVICE)
# Ubicación: backend/app/services/cu24_gestionar_cancelacion_vencimiento_reservas/vencimiento_reserva_service.py
# ==============================================================================

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.models.cu10_gestionar_reservas_prendas.reserva_model import ReservaModel, ReservaDetalleModel
from app.models.cu13_gestionar_inventario_movimientos.inventario_model import (
    InventarioModel, MovimientoInventarioModel
)
from app.models.cu5_gestionar_productos.producto_model import (
    VarianteProductoModel, ProductoModel
)
from app.models.cu4_gestionar_sucursales.sucursal_model import SucursalModel
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.models.cu19_gestionar_notificaciones.notificacion_model import NotificacionModel
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
from app.core.timezone import get_bolivia_now


class VencimientoReservaService:
    """
    Motor de Auditoría, Vencimiento Automático (48h) y Cancelación de Reservas (CU24).
    - Evalúa la ventana de tolerancia (por defecto 48 horas) para retiro físico en tienda.
    - Reintegra automáticamente las prendas al stock comercial disponible (disminuye stockreservado).
    - Genera movimientos de inventario tipo 'LIBERACION_RESERVA_VENCIDA' / 'CANCELACION_RESERVA_STOCK_LIBERADO'.
    - Envía alertas y notificaciones proactivas al usuario (CU19).
    - Registra auditoría completa en Bitácora (CU26).
    """

    @classmethod
    def cancelar_reservas_vencidas(
        cls,
        db: Session,
        tenant_id: int,
        horas_limite: int = 48,
        sucursal_id: Optional[int] = None,
        usuario_ejecutor_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Audita y cancela automáticamente todas las reservas pendientes que hayan superado el plazo de tolerancia.
        """
        ahora = get_bolivia_now()
        limite_tiempo = ahora - timedelta(hours=horas_limite)

        query = db.query(ReservaModel).filter(
            ReservaModel.tenant_id == tenant_id,
            ReservaModel.estado == "PENDIENTE",
            ReservaModel.fechareserva <= limite_tiempo
        )
        if sucursal_id:
            query = query.filter(ReservaModel.sucursalid == sucursal_id)

        reservas_expiradas = query.all()

        total_canceladas = 0
        prendas_liberadas = 0
        valor_total_liberado = 0.0
        detalles_resumen = []

        for res in reservas_expiradas:
            res.estado = "VENCIDA"
            if res.observaciones:
                res.observaciones += f" | Expirada por superar plazo de {horas_limite}h"
            else:
                res.observaciones = f"Expirada automáticamente por superar plazo de {horas_limite}h"

            total_canceladas += 1
            prendas_de_reserva = 0
            monto_de_reserva = 0.0

            # Consultar items de la reserva
            detalles = db.query(
                ReservaDetalleModel,
                VarianteProductoModel,
                ProductoModel
            ).join(
                VarianteProductoModel, ReservaDetalleModel.varianteid == VarianteProductoModel.id
            ).join(
                ProductoModel, VarianteProductoModel.productoid == ProductoModel.id
            ).filter(
                ReservaDetalleModel.reservaid == res.id
            ).all()

            for det, var, prod in detalles:
                cant = det.cantidad
                prendas_de_reserva += cant
                precio = float(getattr(prod, "precio", 0.0) or 0.0)
                monto_de_reserva += (cant * precio)

                # 1. Liberar stock reservado en inventario
                inv = db.query(InventarioModel).filter(
                    InventarioModel.varianteid == det.varianteid,
                    InventarioModel.sucursalid == res.sucursalid,
                    InventarioModel.tenant_id == tenant_id
                ).first()

                if inv:
                    inv.stockreservado = max(0, (inv.stockreservado or 0) - cant)
                    inv.fechaactualizacion = ahora

                    # 2. Registrar movimiento de inventario en Kardex
                    mov = MovimientoInventarioModel(
                        tenant_id=tenant_id,
                        tipomovimiento="LIBERACION_RESERVA_VENCIDA",
                        cantidad=cant,
                        motivo=f"Reintegración automática por vencimiento ({horas_limite}h) reserva #{res.codigoreserva}",
                        referencia=res.codigoreserva,
                        inventarioid=inv.id,
                        usuarioid=usuario_ejecutor_id or 1
                    )
                    db.add(mov)

            prendas_liberadas += prendas_de_reserva
            valor_total_liberado += monto_de_reserva

            # 3. Notificación al cliente (CU19)
            notif = NotificacionModel(
                tenant_id=tenant_id,
                usuario_id=res.clienteid,
                titulo=f"Reserva #{res.codigoreserva} Expirada",
                mensaje=(
                    f"Tu reserva #{res.codigoreserva} en la boutique ha expirado tras superar las {horas_limite} horas de plazo. "
                    f"Las prendas ({prendas_de_reserva} unid.) fueron devueltas a la vitrina comercial."
                ),
                tipo="RESERVA_EXPIRANDO",
                leido=False,
                enlace="/mis-reservas"
            )
            db.add(notif)

            # 4. Auditoría en Bitácora (CU26)
            BitacoraController.registrar_accion(
                db=db,
                usuario_id=usuario_ejecutor_id,
                accion="VENCER_RESERVA",
                modulo="RESERVAS",
                detalle=(
                    f"Reserva #{res.codigoreserva} vencida automáticamente (>={horas_limite}h). "
                    f"Liberadas {prendas_de_reserva} prendas (Bs. {monto_de_reserva:,.2f}) a inventario disponible."
                ),
                tenant_id=tenant_id,
                datos_nuevos={"reserva_id": res.id, "codigo": res.codigoreserva, "prendas_liberadas": prendas_de_reserva}
            )

            detalles_resumen.append({
                "reserva_id": res.id,
                "codigo": res.codigoreserva,
                "prendas_liberadas": prendas_de_reserva,
                "monto_estimado_bob": round(monto_de_reserva, 2)
            })

        db.commit()

        return {
            "reservas_vencidas_canceladas": total_canceladas,
            "prendas_liberadas_al_stock": prendas_liberadas,
            "valor_monetario_liberado_bob": round(valor_total_liberado, 2),
            "fecha_ejecucion": ahora.isoformat(),
            "detalles": detalles_resumen
        }

    @classmethod
    def cancelar_reserva_manual(
        cls,
        db: Session,
        reserva_id: int,
        tenant_id: int,
        motivo: str,
        usuario_id: Optional[int] = None
    ) -> Optional[ReservaModel]:
        """
        Permite a un cliente o encargado de tienda cancelar manualmente una reserva activa,
        liberando de inmediato el stock comprometido.
        """
        res = db.query(ReservaModel).filter(
            ReservaModel.id == reserva_id,
            ReservaModel.tenant_id == tenant_id
        ).first()

        if not res or res.estado != "PENDIENTE":
            return None

        ahora = get_bolivia_now()
        res.estado = "CANCELADA"
        res.observaciones = f"{res.observaciones or ''} | Cancelación manual: {motivo}".strip(" |")

        detalles = db.query(ReservaDetalleModel).filter(ReservaDetalleModel.reservaid == res.id).all()
        prendas_liberadas = 0

        for det in detalles:
            cant = det.cantidad
            prendas_liberadas += cant
            inv = db.query(InventarioModel).filter(
                InventarioModel.varianteid == det.varianteid,
                InventarioModel.sucursalid == res.sucursalid,
                InventarioModel.tenant_id == tenant_id
            ).first()

            if inv:
                inv.stockreservado = max(0, (inv.stockreservado or 0) - cant)
                inv.fechaactualizacion = ahora

                # Movimiento de inventario
                mov = MovimientoInventarioModel(
                    tenant_id=tenant_id,
                    tipomovimiento="CANCELACION_RESERVA_STOCK_LIBERADO",
                    cantidad=cant,
                    motivo=f"Cancelación manual de reserva #{res.codigoreserva}: {motivo}",
                    referencia=res.codigoreserva,
                    inventarioid=inv.id,
                    usuarioid=usuario_id or 1
                )
                db.add(mov)

        # Notificación al usuario
        notif = NotificacionModel(
            tenant_id=tenant_id,
            usuario_id=res.clienteid,
            titulo=f"Reserva #{res.codigoreserva} Cancelada",
            mensaje=f"Tu reserva #{res.codigoreserva} ha sido cancelada ({motivo}). Las prendas han sido liberadas.",
            tipo="RESERVA_CANCELADA",
            leido=False,
            enlace="/mis-reservas"
        )
        db.add(notif)

        # Auditoría en Bitácora (CU26)
        BitacoraController.registrar_accion(
            db=db,
            usuario_id=usuario_id,
            accion="CANCELAR_RESERVA",
            modulo="RESERVAS",
            detalle=f"Reserva #{res.codigoreserva} cancelada manualmente. Motivo: '{motivo}'. Prendas liberadas: {prendas_liberadas}.",
            tenant_id=tenant_id,
            datos_nuevos={"reserva_id": res.id, "motivo": motivo, "prendas": prendas_liberadas}
        )

        db.commit()
        db.refresh(res)
        return res

    @classmethod
    def listar_reservas_activas(
        cls,
        db: Session,
        tenant_id: int,
        sucursal_id: Optional[int] = None,
        horas_politica: int = 48
    ) -> List[Dict[str, Any]]:
        """
        Recupera todas las reservas activas (PENDIENTE) con el cálculo preciso de horas restantes,
        alerta de proximidad (<12h) y prendas asociadas.
        """
        ahora = get_bolivia_now()
        query = db.query(
            ReservaModel,
            UsuarioModel.nombre.label("cli_nombre"),
            UsuarioModel.apellido.label("cli_apellido"),
            UsuarioModel.email.label("cli_email"),
            SucursalModel.nombre.label("suc_nombre")
        ).join(
            UsuarioModel, ReservaModel.clienteid == UsuarioModel.id
        ).join(
            SucursalModel, ReservaModel.sucursalid == SucursalModel.id
        ).filter(
            ReservaModel.tenant_id == tenant_id,
            ReservaModel.estado == "PENDIENTE"
        )

        if sucursal_id:
            query = query.filter(ReservaModel.sucursalid == sucursal_id)

        rows = query.order_by(ReservaModel.fechareserva.asc()).all()

        resultado = []
        for res, nom, ape, email, suc_nom in rows:
            fecha_exp = (res.fechareserva or ahora) + timedelta(hours=horas_politica)
            diff_segundos = (fecha_exp - ahora).total_seconds()
            horas_restantes = round(diff_segundos / 3600.0, 1)
            en_riesgo = (0 <= horas_restantes <= 12)
            es_expirada = (horas_restantes < 0)

            # Cargar items
            items_query = db.query(
                ReservaDetalleModel,
                VarianteProductoModel,
                ProductoModel
            ).join(
                VarianteProductoModel, ReservaDetalleModel.varianteid == VarianteProductoModel.id
            ).join(
                ProductoModel, VarianteProductoModel.productoid == ProductoModel.id
            ).filter(
                ReservaDetalleModel.reservaid == res.id
            ).all()

            detalles_dto = []
            total_prendas = 0
            monto_total = 0.0

            for det, var, prod in items_query:
                pu = float(getattr(prod, "precio", 0.0) or 0.0)
                sub = float(det.cantidad * pu)
                total_prendas += det.cantidad
                monto_total += sub

                detalles_dto.append({
                    "variante_id": det.varianteid,
                    "sku": getattr(var, "sku", f"VAR-{det.varianteid}"),
                    "producto_nombre": getattr(prod, "nombre", "Prenda de Catálogo"),
                    "talla": getattr(var, "talla", "M"),
                    "color": getattr(var, "color", "Estándar"),
                    "cantidad": det.cantidad,
                    "precio_unitario": pu,
                    "subtotal": sub
                })

            cli_completo = f"{nom} {ape or ''}".strip()

            resultado.append({
                "id": res.id,
                "codigoreserva": res.codigoreserva,
                "fechareserva": res.fechareserva,
                "fecha_expiracion": fecha_exp,
                "horas_restantes": horas_restantes,
                "en_riesgo": en_riesgo,
                "es_expirada": es_expirada,
                "estado": res.estado,
                "observaciones": res.observaciones,
                "sucursalid": res.sucursalid,
                "sucursal_nombre": suc_nom or f"Sucursal #{res.sucursalid}",
                "clienteid": res.clienteid,
                "cliente_nombre": cli_completo,
                "cliente_email": email,
                "total_prendas": total_prendas,
                "monto_total_estimado": round(monto_total, 2),
                "detalles": detalles_dto
            })

        return resultado

    @classmethod
    def obtener_kpis(cls, db: Session, tenant_id: int, horas_politica: int = 48) -> Dict[str, Any]:
        """
        Calcula las métricas ejecutivas para el módulo CU24.
        """
        ahora = get_bolivia_now()
        limite_riesgo = ahora - timedelta(hours=max(0, horas_politica - 12))

        # Total activas
        activas = db.query(func.count(ReservaModel.id)).filter(
            ReservaModel.tenant_id == tenant_id,
            ReservaModel.estado == "PENDIENTE"
        ).scalar() or 0

        # En riesgo (< 12h restantes)
        en_riesgo = db.query(func.count(ReservaModel.id)).filter(
            ReservaModel.tenant_id == tenant_id,
            ReservaModel.estado == "PENDIENTE",
            ReservaModel.fechareserva <= limite_riesgo
        ).scalar() or 0

        # Históricas vencidas
        vencidas = db.query(func.count(ReservaModel.id)).filter(
            ReservaModel.tenant_id == tenant_id,
            ReservaModel.estado == "VENCIDA"
        ).scalar() or 0

        # Canceladas manual
        canceladas = db.query(func.count(ReservaModel.id)).filter(
            ReservaModel.tenant_id == tenant_id,
            ReservaModel.estado == "CANCELADA"
        ).scalar() or 0

        # Movimientos de inventario por liberación de reservas
        movs = db.query(
            func.coalesce(func.sum(MovimientoInventarioModel.cantidad), 0)
        ).filter(
            MovimientoInventarioModel.tenant_id == tenant_id,
            MovimientoInventarioModel.tipomovimiento.in_([
                "LIBERACION_RESERVA_VENCIDA",
                "CANCELACION_RESERVA_STOCK_LIBERADO"
            ])
        ).scalar() or 0

        # Estimación monetaria (asumiendo ticket promedio de 150 Bs por prenda liberada)
        valor_estimado = float(movs) * 150.0

        return {
            "total_reservas_activas": activas,
            "reservas_en_riesgo": en_riesgo,
            "reservas_vencidas_historicas": vencidas,
            "reservas_canceladas_manual": canceladas,
            "total_prendas_reintegradas": int(movs),
            "valor_total_liberado_bob": round(valor_estimado, 2),
            "horas_politica_defecto": horas_politica
        }
