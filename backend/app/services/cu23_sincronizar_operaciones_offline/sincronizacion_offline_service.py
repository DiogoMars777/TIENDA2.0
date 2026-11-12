# ==============================================================================
# CU23 - SINCRONIZAR OPERACIONES OFFLINE -> SERVICIO (MVC - SERVICE)
# Ubicación: backend/app/services/cu23_sincronizar_operaciones_offline/sincronizacion_offline_service.py
# ==============================================================================

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid

from app.models.cu23_sincronizar_operaciones_offline.sincronizacion_offline_model import OperacionOfflineSync
from app.models.cu22_registrar_cobros_contado_offline.cobro_offline_model import CobroOffline
from app.models.cu13_gestionar_inventario_movimientos.inventario_model import InventarioModel, MovimientoInventarioModel
from app.models.cu14_registrar_ventas_presenciales.venta_presencial_model import (
    VentaModel, DetalleVentaModel, PagoModel
)
from app.models.cu3_gestionar_clientes.cliente_model import ClienteModel
from app.models.cu4_gestionar_sucursales.sucursal_model import SucursalModel
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
from app.core.timezone import get_bolivia_now, to_bolivia_time


class SincronizacionOfflineService:
    """
    Motor de Sincronización Offline y Resolución de Conflictos (CU23).
    - Ingesta de operaciones locales diferidas (CU22 CobroOffline y lotes cliente).
    - Verificación y deducción atómica de inventario (Kardex).
    - Políticas de resolución de discrepancias:
        * PRIORIZAR_TIENDA_FISICA (Prevalencia de la venta física en mostrador).
        * AJUSTE_KARDEX (Ajuste compensatorio de stock en almacén).
        * BLOQUEAR / RECHAZAR (Retención en cola para auditoría manual).
    - Creación oficial de Venta, DetalleVenta y Pago.
    - Idempotencia garantizada por UUID.
    - Registro de logs y auditoría nativa en Bitácora (CU26).
    """

    @staticmethod
    def _parsear_payload_cobro(observaciones_raw: Optional[str]) -> List[Dict[str, Any]]:
        """Extrae la lista de items vendidos del JSON de observaciones o retorna lista vacía"""
        if not observaciones_raw:
            return []
        try:
            data = json.loads(observaciones_raw)
            if isinstance(data, dict):
                return data.get("items", [])
            elif isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    @classmethod
    def sincronizar_cobros_offline_pendientes(
        cls,
        db: Session,
        tenant_id: int,
        usuario_id: Optional[int] = None,
        sucursal_id: Optional[int] = None,
        estrategia_preferida: str = "PRIORIZAR_TIENDA_FISICA"
    ) -> Dict[str, Any]:
        """
        Consolida todas las operaciones de cobro offline (CU22) pendientes de sincronización en el Tenant.
        """
        query = db.query(CobroOffline).filter(
            CobroOffline.tenant_id == tenant_id,
            CobroOffline.sincronizado == False
        )
        if sucursal_id:
            query = query.filter(CobroOffline.sucursal_id == sucursal_id)

        pendientes = query.order_by(CobroOffline.fecha_cobro.asc(), CobroOffline.id.asc()).all()

        total = len(pendientes)
        procesadas = 0
        sincronizadas = 0
        conflictos_resueltos = 0
        errores = 0
        resultados = []

        cliente_default = db.query(ClienteModel).filter(ClienteModel.tenant_id == tenant_id).first()
        cliente_id_default = cliente_default.id if cliente_default else 1

        for cobro in pendientes:
            try:
                # 1. Verificar idempotencia en sincronizacion_offline
                sync_previo = db.query(OperacionOfflineSync).filter(
                    OperacionOfflineSync.uuid_operacion == cobro.uuid_operacion
                ).first()

                if sync_previo and sync_previo.estado in ("SINCRONIZADO", "CONFLICTO_RESUELTO"):
                    cobro.sincronizado = True
                    cobro.fecha_sincronizacion = get_bolivia_now()
                    procesadas += 1
                    sincronizadas += 1
                    resultados.append({
                        "uuid_operacion": cobro.uuid_operacion,
                        "tipo": "COBRO_OFFLINE",
                        "estado": "DUPLICADO_IGNORADO",
                        "mensaje": f"Recibo {cobro.nro_recibo_provisional} ya se encontraba sincronizado.",
                        "nro_recibo": cobro.nro_recibo_provisional,
                        "conflicto_detectado": False,
                        "estrategia_aplicada": sync_previo.estrategia_conflicto
                    })
                    continue

                items = cls._parsear_payload_cobro(cobro.observaciones)

                # 2. Análisis de Stock y Detección de Discrepancias
                hay_conflicto = False
                detalles_conflicto = []

                for it in items:
                    v_id = it.get("variante_id")
                    cant = int(it.get("cantidad", 1))
                    if not v_id:
                        continue

                    inv = db.query(InventarioModel).filter(
                        InventarioModel.tenant_id == tenant_id,
                        InventarioModel.sucursalid == cobro.sucursal_id,
                        InventarioModel.varianteid == v_id
                    ).first()

                    if not inv or inv.stockfisico < cant:
                        hay_conflicto = True
                        stock_actual = inv.stockfisico if inv else 0
                        detalles_conflicto.append(
                            f"Variante #{v_id} (Sol: {cant}, Disp: {stock_actual})"
                        )

                # 3. Aplicación de Estrategia de Resolución
                estado_sync = "SINCRONIZADO"
                estrategia_aplicada = "STOCK_SUFICIENTE"

                if hay_conflicto:
                    if estrategia_preferida == "PRIORIZAR_TIENDA_FISICA":
                        estado_sync = "CONFLICTO_RESUELTO"
                        estrategia_aplicada = "PRIORIZAR_TIENDA_FISICA"
                        conflictos_resueltos += 1

                        # Descontar stock y permitir ajuste automático
                        for it in items:
                            v_id = it.get("variante_id")
                            cant = int(it.get("cantidad", 1))
                            if not v_id:
                                continue

                            inv = db.query(InventarioModel).filter(
                                InventarioModel.tenant_id == tenant_id,
                                InventarioModel.sucursalid == cobro.sucursal_id,
                                InventarioModel.varianteid == v_id
                            ).first()

                            if not inv:
                                inv = InventarioModel(
                                    tenant_id=tenant_id,
                                    sucursalid=cobro.sucursal_id,
                                    varianteid=v_id,
                                    stockfisico=-cant,
                                    stockreservado=0,
                                    stockminimo=5
                                )
                                db.add(inv)
                                db.flush()
                            else:
                                inv.stockfisico -= cant

                            # Registrar en MovimientoInventario
                            mov = MovimientoInventarioModel(
                                tenant_id=tenant_id,
                                tipomovimiento="VENTA_OFFLINE_DISCREPANCIA",
                                cantidad=cant,
                                motivo=f"Venta física offline con prevalencia #{cobro.nro_recibo_provisional}",
                                referencia=cobro.nro_recibo_provisional,
                                inventarioid=inv.id,
                                usuarioid=usuario_id or cobro.cajero_id or 1
                            )
                            db.add(mov)

                    elif estrategia_preferida == "AJUSTE_KARDEX":
                        estado_sync = "CONFLICTO_RESUELTO"
                        estrategia_aplicada = "AJUSTE_KARDEX"
                        conflictos_resueltos += 1

                        for it in items:
                            v_id = it.get("variante_id")
                            cant = int(it.get("cantidad", 1))
                            if not v_id:
                                continue

                            inv = db.query(InventarioModel).filter(
                                InventarioModel.tenant_id == tenant_id,
                                InventarioModel.sucursalid == cobro.sucursal_id,
                                InventarioModel.varianteid == v_id
                            ).first()

                            if inv:
                                inv.stockfisico = max(0, inv.stockfisico - cant)
                                mov = MovimientoInventarioModel(
                                    tenant_id=tenant_id,
                                    tipomovimiento="AJUSTE_KARDEX_OFFLINE",
                                    cantidad=cant,
                                    motivo=f"Ajuste Kardex venta offline #{cobro.nro_recibo_provisional}",
                                    referencia=cobro.nro_recibo_provisional,
                                    inventarioid=inv.id,
                                    usuarioid=usuario_id or cobro.cajero_id or 1
                                )
                                db.add(mov)
                    else:
                        # BLOQUEAR / REQUIERE_INTERVENCION
                        estado_sync = "CONFLICTO_PENDIENTE"
                        estrategia_aplicada = "BLOQUEAR_MANUAL"

                else:
                    # Stock normal
                    sincronizadas += 1
                    for it in items:
                        v_id = it.get("variante_id")
                        cant = int(it.get("cantidad", 1))
                        if not v_id:
                            continue

                        inv = db.query(InventarioModel).filter(
                            InventarioModel.tenant_id == tenant_id,
                            InventarioModel.sucursalid == cobro.sucursal_id,
                            InventarioModel.varianteid == v_id
                        ).first()

                        if inv:
                            inv.stockfisico -= cant
                            mov = MovimientoInventarioModel(
                                tenant_id=tenant_id,
                                tipomovimiento="SALIDA_VENTA",
                                cantidad=cant,
                                motivo=f"Venta presencial offline sincronizada #{cobro.nro_recibo_provisional}",
                                referencia=cobro.nro_recibo_provisional,
                                inventarioid=inv.id,
                                usuarioid=usuario_id or cobro.cajero_id or 1
                            )
                            db.add(mov)

                # 4. Creación de registros oficiales (Venta, DetalleVenta, Pago)
                nueva_venta = None
                if estado_sync in ("SINCRONIZADO", "CONFLICTO_RESUELTO"):
                    cod_venta = f"VTA-SYNC-{cobro.nro_recibo_provisional}"
                    # Garantizar unicidad
                    if db.query(VentaModel).filter(VentaModel.codigoventa == cod_venta).first():
                        cod_venta = f"{cod_venta}-{uuid.uuid4().hex[:4].upper()}"

                    nueva_venta = VentaModel(
                        tenant_id=tenant_id,
                        codigoventa=cod_venta,
                        tipoventa="Presencial Offline",
                        estado="Completada",
                        subtotal=cobro.monto,
                        descuento=0,
                        total=cobro.monto,
                        fecha=cobro.fecha_cobro,
                        sucursalid=cobro.sucursal_id,
                        clienteid=cliente_id_default,
                        usuarioid=cobro.cajero_id or usuario_id or 1
                    )
                    db.add(nueva_venta)
                    db.flush()

                    # DetalleVenta
                    for it in items:
                        v_id = it.get("variante_id")
                        cant = int(it.get("cantidad", 1))
                        pu = float(it.get("precio_unitario", 0))
                        sub = float(it.get("subtotal", cant * pu))
                        if v_id:
                            det = DetalleVentaModel(
                                ventaid=nueva_venta.id,
                                varianteid=v_id,
                                cantidad=cant,
                                preciounitario=pu,
                                descuento=0,
                                subtotal=sub
                            )
                            db.add(det)

                    # Pago
                    pago = PagoModel(
                        tenant_id=tenant_id,
                        monto=cobro.monto,
                        estado="Aprobado",
                        referencia=f"RECIBO-OFFLINE-{cobro.nro_recibo_provisional}",
                        fecha=cobro.fecha_cobro,
                        ventaid=nueva_venta.id,
                        metodoid=1  # 1: Efectivo
                    )
                    db.add(pago)

                    # Marcar CobroOffline
                    cobro.sincronizado = True
                    cobro.fecha_sincronizacion = get_bolivia_now()
                    cobro.venta_id = nueva_venta.id

                    # Si el cobro offline corresponde a una Reserva (ej. REC-RES-XXXXXX o nota con RES-XXXXXX), marcarla como ENTREGADA
                    try:
                        import re
                        from app.models.models import ReservaModel
                        texto_busqueda = f"{cobro.nro_recibo_provisional or ''} {cobro.observaciones or ''}"
                        match_res = re.search(r"(RES-[A-Z0-9]{4,10})", texto_busqueda.upper())
                        if match_res:
                            cod_res = match_res.group(1)
                            res_obj = db.query(ReservaModel).filter(
                                ReservaModel.tenant_id == tenant_id,
                                ReservaModel.codigoreserva == cod_res
                            ).first()
                            if res_obj and res_obj.estado == "PENDIENTE":
                                res_obj.estado = "ENTREGADA"
                                res_obj.observaciones = f"{res_obj.observaciones or ''} [Pagada y Entregada vía Cobro Offline {cobro.nro_recibo_provisional}]".strip()
                                for det_res in res_obj.detalles:
                                    inv_res = db.query(InventarioModel).filter(
                                        InventarioModel.tenant_id == tenant_id,
                                        InventarioModel.sucursalid == res_obj.sucursalid,
                                        InventarioModel.varianteid == det_res.varianteid
                                    ).first()
                                    if inv_res:
                                        inv_res.stockreservado = max(0, (inv_res.stockreservado or 0) - det_res.cantidad)
                    except Exception:
                        pass

                # 5. Registrar log en OperacionOfflineSync
                if not sync_previo:
                    sync_rec = OperacionOfflineSync(
                        tenant_id=tenant_id,
                        usuario_id=usuario_id or cobro.cajero_id,
                        sucursal_id=cobro.sucursal_id,
                        tipo_operacion="COBRO_VENTA_OFFLINE",
                        uuid_operacion=cobro.uuid_operacion,
                        payload_json=json.dumps({
                            "nro_recibo": cobro.nro_recibo_provisional,
                            "monto": float(cobro.monto),
                            "cliente_nombre": cobro.cliente_nombre,
                            "cliente_nit": cobro.cliente_nit,
                            "items": items,
                            "detalles_conflicto": detalles_conflicto
                        }, ensure_ascii=False, default=str),
                        estado=estado_sync,
                        estrategia_conflicto=estrategia_aplicada,
                        reintentos=1,
                        fecha_operacion_origen=cobro.fecha_cobro,
                        fecha_recibido=get_bolivia_now(),
                        fecha_procesado=get_bolivia_now() if estado_sync != "CONFLICTO_PENDIENTE" else None
                    )
                    db.add(sync_rec)
                else:
                    sync_previo.estado = estado_sync
                    sync_previo.estrategia_conflicto = estrategia_aplicada
                    sync_previo.fecha_procesado = get_bolivia_now()
                    sync_previo.reintentos += 1

                # 6. Auditoría en Bitácora (CU26)
                BitacoraController.registrar_accion(
                    db=db,
                    usuario_id=usuario_id or cobro.cajero_id,
                    accion="SINCRONIZAR",
                    modulo="SINCRONIZACION_OFFLINE",
                    detalle=(
                        f"Sincronizado cobro offline #{cobro.nro_recibo_provisional} -> "
                        f"Venta #{nueva_venta.id if nueva_venta else 'N/A'}. "
                        f"Estado: {estado_sync}, Estrategia: {estrategia_aplicada}"
                    ),
                    tenant_id=tenant_id,
                    datos_nuevos={"nro_recibo": cobro.nro_recibo_provisional, "estado": estado_sync}
                )

                procesadas += 1
                resultados.append({
                    "uuid_operacion": cobro.uuid_operacion,
                    "tipo": "COBRO_OFFLINE",
                    "estado": estado_sync,
                    "mensaje": (
                        f"Cobro {cobro.nro_recibo_provisional} procesado exitosamente "
                        f"({'Conflicto resuelto: ' + estrategia_aplicada if hay_conflicto else 'Stock consolidado'})."
                    ),
                    "venta_id": nueva_venta.id if nueva_venta else None,
                    "nro_recibo": cobro.nro_recibo_provisional,
                    "conflicto_detectado": hay_conflicto,
                    "estrategia_aplicada": estrategia_aplicada
                })

            except Exception as e:
                errores += 1
                resultados.append({
                    "uuid_operacion": cobro.uuid_operacion,
                    "tipo": "COBRO_OFFLINE",
                    "estado": "ERROR",
                    "mensaje": f"Error al procesar recibo {cobro.nro_recibo_provisional}: {str(e)}",
                    "venta_id": None,
                    "nro_recibo": cobro.nro_recibo_provisional,
                    "conflicto_detectado": True,
                    "estrategia_aplicada": "FALLO_TRANSACCIONAL"
                })

        db.commit()

        return {
            "total": total,
            "procesadas": procesadas,
            "sincronizadas": sincronizadas,
            "conflictos_resueltos": conflictos_resueltos,
            "errores": errores,
            "resultados": resultados
        }

    @classmethod
    def sincronizar_lote(
        cls,
        db: Session,
        tenant_id: int,
        usuario_id: Optional[int],
        sucursal_id: int,
        operaciones: List[Any],
        estrategia_preferida: str = "PRIORIZAR_TIENDA_FISICA"
    ) -> Dict[str, Any]:
        """
        Sincroniza un lote de operaciones directas enviadas desde la caché offline del navegador (IndexedDB / LocalStorage).
        """
        procesadas = 0
        sincronizadas = 0
        conflictos_resueltos = 0
        errores = 0
        resultados = []

        cliente_default = db.query(ClienteModel).filter(ClienteModel.tenant_id == tenant_id).first()
        cliente_id_default = cliente_default.id if cliente_default else 1

        for op in operaciones:
            op_dict = op if isinstance(op, dict) else (op.dict() if hasattr(op, "dict") else op.__dict__)
            op_uuid = op_dict.get("uuid_operacion") or str(uuid.uuid4())
            tipo = op_dict.get("tipo") or op_dict.get("tipo_operacion") or "VENTA"
            payload = op_dict.get("payload") or {}
            fecha_origen_raw = op_dict.get("fecha_operacion")
            fecha_origen = to_bolivia_time(fecha_origen_raw) if fecha_origen_raw else get_bolivia_now()

            # Idempotencia
            existente = db.query(OperacionOfflineSync).filter(
                OperacionOfflineSync.uuid_operacion == op_uuid
            ).first()

            if existente:
                resultados.append({
                    "uuid_operacion": op_uuid,
                    "tipo": tipo,
                    "estado": "DUPLICADO_IGNORADO",
                    "mensaje": "La transacción ya fue procesada anteriormente.",
                    "conflicto_detectado": False,
                    "estrategia_aplicada": existente.estrategia_conflicto
                })
                continue

            try:
                items = payload.get("items", [])
                monto_total = float(payload.get("monto") or payload.get("total") or 0)
                nro_recibo = payload.get("nro_recibo") or f"REC-LOT-{uuid.uuid4().hex[:6].upper()}"

                # Analizar stock
                hay_conflicto = False
                for it in items:
                    v_id = it.get("variante_id")
                    cant = int(it.get("cantidad", 1))
                    if not v_id:
                        continue
                    inv = db.query(InventarioModel).filter(
                        InventarioModel.tenant_id == tenant_id,
                        InventarioModel.sucursalid == sucursal_id,
                        InventarioModel.varianteid == v_id
                    ).first()
                    if not inv or inv.stockfisico < cant:
                        hay_conflicto = True

                estado_op = "SINCRONIZADO"
                estrategia_aplicada = "STOCK_SUFICIENTE"

                if hay_conflicto:
                    if estrategia_preferida == "PRIORIZAR_TIENDA_FISICA":
                        estado_op = "CONFLICTO_RESUELTO"
                        estrategia_aplicada = "PRIORIZAR_TIENDA_FISICA"
                        conflictos_resueltos += 1

                        for it in items:
                            v_id = it.get("variante_id")
                            cant = int(it.get("cantidad", 1))
                            if not v_id:
                                continue
                            inv = db.query(InventarioModel).filter(
                                InventarioModel.tenant_id == tenant_id,
                                InventarioModel.sucursalid == sucursal_id,
                                InventarioModel.varianteid == v_id
                            ).first()
                            if not inv:
                                inv = InventarioModel(
                                    tenant_id=tenant_id,
                                    sucursalid=sucursal_id,
                                    varianteid=v_id,
                                    stockfisico=-cant,
                                    stockreservado=0,
                                    stockminimo=5
                                )
                                db.add(inv)
                                db.flush()
                            else:
                                inv.stockfisico -= cant

                            mov = MovimientoInventarioModel(
                                tenant_id=tenant_id,
                                tipomovimiento="VENTA_OFFLINE_DISCREPANCIA",
                                cantidad=cant,
                                motivo=f"Venta lote offline prevalencia física {nro_recibo}",
                                referencia=nro_recibo,
                                inventarioid=inv.id,
                                usuarioid=usuario_id or 1
                            )
                            db.add(mov)

                    elif estrategia_preferida == "AJUSTE_KARDEX":
                        estado_op = "CONFLICTO_RESUELTO"
                        estrategia_aplicada = "AJUSTE_KARDEX"
                        conflictos_resueltos += 1
                        for it in items:
                            v_id = it.get("variante_id")
                            cant = int(it.get("cantidad", 1))
                            if not v_id:
                                continue
                            inv = db.query(InventarioModel).filter(
                                InventarioModel.tenant_id == tenant_id,
                                InventarioModel.sucursalid == sucursal_id,
                                InventarioModel.varianteid == v_id
                            ).first()
                            if inv:
                                inv.stockfisico = max(0, inv.stockfisico - cant)
                    else:
                        estado_op = "CONFLICTO_PENDIENTE"
                        estrategia_aplicada = "BLOQUEAR_MANUAL"

                else:
                    sincronizadas += 1
                    for it in items:
                        v_id = it.get("variante_id")
                        cant = int(it.get("cantidad", 1))
                        if not v_id:
                            continue
                        inv = db.query(InventarioModel).filter(
                            InventarioModel.tenant_id == tenant_id,
                            InventarioModel.sucursalid == sucursal_id,
                            InventarioModel.varianteid == v_id
                        ).first()
                        if inv:
                            inv.stockfisico -= cant
                            mov = MovimientoInventarioModel(
                                tenant_id=tenant_id,
                                tipomovimiento="SALIDA_VENTA",
                                cantidad=cant,
                                motivo=f"Venta lote offline sincronizada {nro_recibo}",
                                referencia=nro_recibo,
                                inventarioid=inv.id,
                                usuarioid=usuario_id or 1
                            )
                            db.add(mov)

                nueva_venta = None
                if estado_op in ("SINCRONIZADO", "CONFLICTO_RESUELTO"):
                    cod_vta = f"VTA-SYNC-{nro_recibo}"
                    if db.query(VentaModel).filter(VentaModel.codigoventa == cod_vta).first():
                        cod_vta = f"{cod_vta}-{uuid.uuid4().hex[:4].upper()}"

                    nueva_venta = VentaModel(
                        tenant_id=tenant_id,
                        codigoventa=cod_vta,
                        tipoventa="Presencial Offline",
                        estado="Completada",
                        subtotal=monto_total,
                        descuento=0,
                        total=monto_total,
                        fecha=fecha_origen,
                        sucursalid=sucursal_id,
                        clienteid=cliente_id_default,
                        usuarioid=usuario_id or 1
                    )
                    db.add(nueva_venta)
                    db.flush()

                    for it in items:
                        v_id = it.get("variante_id")
                        cant = int(it.get("cantidad", 1))
                        pu = float(it.get("precio_unitario", 0))
                        sub = float(it.get("subtotal", cant * pu))
                        if v_id:
                            det = DetalleVentaModel(
                                ventaid=nueva_venta.id,
                                varianteid=v_id,
                                cantidad=cant,
                                preciounitario=pu,
                                descuento=0,
                                subtotal=sub
                            )
                            db.add(det)

                    pago = PagoModel(
                        tenant_id=tenant_id,
                        monto=monto_total,
                        estado="Aprobado",
                        referencia=f"LOTE-OFFLINE-{nro_recibo}",
                        fecha=fecha_origen,
                        ventaid=nueva_venta.id,
                        metodoid=1
                    )
                    db.add(pago)

                sync_reg = OperacionOfflineSync(
                    tenant_id=tenant_id,
                    usuario_id=usuario_id,
                    sucursal_id=sucursal_id,
                    tipo_operacion=tipo,
                    uuid_operacion=op_uuid,
                    payload_json=json.dumps(payload, ensure_ascii=False, default=str),
                    estado=estado_op,
                    estrategia_conflicto=estrategia_aplicada,
                    reintentos=1,
                    fecha_operacion_origen=fecha_origen,
                    fecha_recibido=get_bolivia_now(),
                    fecha_procesado=get_bolivia_now() if estado_op != "CONFLICTO_PENDIENTE" else None
                )
                db.add(sync_reg)

                BitacoraController.registrar_accion(
                    db=db,
                    usuario_id=usuario_id,
                    accion="SINCRONIZAR",
                    modulo="SINCRONIZACION_OFFLINE",
                    detalle=f"Sincronizado lote offline UUID: {op_uuid[:8]} -> Venta #{nueva_venta.id if nueva_venta else 'N/A'}",
                    tenant_id=tenant_id
                )

                procesadas += 1
                resultados.append({
                    "uuid_operacion": op_uuid,
                    "tipo": tipo,
                    "estado": estado_op,
                    "mensaje": f"Operación {op_uuid[:8]} sincronizada exitosamente.",
                    "venta_id": nueva_venta.id if nueva_venta else None,
                    "nro_recibo": nro_recibo,
                    "conflicto_detectado": hay_conflicto,
                    "estrategia_aplicada": estrategia_aplicada
                })

            except Exception as e:
                errores += 1
                resultados.append({
                    "uuid_operacion": op_uuid,
                    "tipo": tipo,
                    "estado": "ERROR",
                    "mensaje": f"Fallo al procesar operación: {str(e)}",
                    "conflicto_detectado": True,
                    "estrategia_aplicada": "FALLO_TRANSACCIONAL"
                })

        db.commit()

        return {
            "total": len(operaciones),
            "procesadas": procesadas,
            "sincronizadas": sincronizadas,
            "conflictos_resueltos": conflictos_resueltos,
            "errores": errores,
            "resultados": resultados
        }

    @classmethod
    def obtener_kpis(cls, db: Session, tenant_id: int) -> Dict[str, Any]:
        """
        Calcula las métricas ejecutivas del motor de sincronización offline (CU23).
        """
        total_ops = db.query(func.count(OperacionOfflineSync.id)).filter(
            OperacionOfflineSync.tenant_id == tenant_id
        ).scalar() or 0

        sincronizadas = db.query(func.count(OperacionOfflineSync.id)).filter(
            OperacionOfflineSync.tenant_id == tenant_id,
            OperacionOfflineSync.estado == "SINCRONIZADO"
        ).scalar() or 0

        conflictos = db.query(func.count(OperacionOfflineSync.id)).filter(
            OperacionOfflineSync.tenant_id == tenant_id,
            OperacionOfflineSync.estado == "CONFLICTO_RESUELTO"
        ).scalar() or 0

        errores = db.query(func.count(OperacionOfflineSync.id)).filter(
            OperacionOfflineSync.tenant_id == tenant_id,
            OperacionOfflineSync.estado == "ERROR"
        ).scalar() or 0

        # Pendientes en CU22 CobroOffline
        cobros_pendientes = db.query(CobroOffline).filter(
            CobroOffline.tenant_id == tenant_id,
            CobroOffline.sincronizado == False
        ).all()

        cant_pendientes = len(cobros_pendientes)
        monto_pendiente = sum(float(c.monto) for c in cobros_pendientes)

        return {
            "total_operaciones": total_ops,
            "sincronizadas": sincronizadas,
            "conflictos_resueltos": conflictos,
            "errores": errores,
            "cobros_pendientes_en_cola": cant_pendientes,
            "monto_pendiente_en_cola": round(monto_pendiente, 2),
            "estado_motor": "ACTIVO_EN_LINEA"
        }

    @classmethod
    def listar_historial_sincronizaciones(
        cls,
        db: Session,
        tenant_id: int,
        limite: int = 50,
        estado: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recupera el historial de sincronizaciones con metadatos de usuario y sucursal.
        """
        query = db.query(
            OperacionOfflineSync,
            UsuarioModel.nombre.label("usuario_nombre"),
            SucursalModel.nombre.label("sucursal_nombre")
        ).outerjoin(
            UsuarioModel, OperacionOfflineSync.usuario_id == UsuarioModel.id
        ).outerjoin(
            SucursalModel, OperacionOfflineSync.sucursal_id == SucursalModel.id
        ).filter(
            OperacionOfflineSync.tenant_id == tenant_id
        )

        if estado and estado.upper() != "TODOS":
            query = query.filter(OperacionOfflineSync.estado == estado.upper())

        rows = query.order_by(desc(OperacionOfflineSync.id)).limit(limite).all()

        resultado = []
        for sync_op, u_nombre, s_nombre in rows:
            payload_parsed = None
            if sync_op.payload_json:
                try:
                    payload_parsed = json.loads(sync_op.payload_json)
                except Exception:
                    payload_parsed = {"raw": sync_op.payload_json}

            resultado.append({
                "id": sync_op.id,
                "tenant_id": sync_op.tenant_id,
                "usuario_id": sync_op.usuario_id,
                "usuario_nombre": u_nombre or "Cajero Offline",
                "sucursal_id": sync_op.sucursal_id,
                "sucursal_nombre": s_nombre or f"Sucursal #{sync_op.sucursal_id}",
                "tipo_operacion": sync_op.tipo_operacion,
                "uuid_operacion": sync_op.uuid_operacion,
                "estado": sync_op.estado,
                "estrategia_conflicto": sync_op.estrategia_conflicto,
                "reintentos": sync_op.reintentos,
                "error_detalle": sync_op.error_detalle,
                "fecha_operacion_origen": sync_op.fecha_operacion_origen,
                "fecha_recibido": sync_op.fecha_recibido,
                "fecha_procesado": sync_op.fecha_procesado,
                "payload": payload_parsed
            })

        return resultado

    @classmethod
    def resolver_conflicto_manual(
        cls,
        db: Session,
        tenant_id: int,
        usuario_id: int,
        sync_id: int,
        estrategia: str,
        notas: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Permite al administrador o encargado de sucursal resolver manualmente un conflicto retenido.
        """
        sync_op = db.query(OperacionOfflineSync).filter(
            OperacionOfflineSync.id == sync_id,
            OperacionOfflineSync.tenant_id == tenant_id
        ).first()

        if not sync_op:
            raise ValueError(f"No se encontró el registro de sincronización #{sync_id}")

        sync_op.estado = "CONFLICTO_RESUELTO"
        sync_op.estrategia_conflicto = estrategia
        sync_op.fecha_procesado = get_bolivia_now()
        sync_op.error_detalle = notas

        # Si corresponde a un CobroOffline, marcarlo sincronizado
        cobro = db.query(CobroOffline).filter(
            CobroOffline.uuid_operacion == sync_op.uuid_operacion
        ).first()
        if cobro:
            cobro.sincronizado = True
            cobro.fecha_sincronizacion = get_bolivia_now()

        db.commit()

        BitacoraController.registrar_accion(
            db=db,
            usuario_id=usuario_id,
            accion="RESOLVER_CONFLICTO",
            modulo="SINCRONIZACION_OFFLINE",
            detalle=f"Conflicto #{sync_id} resuelto manualmente con estrategia '{estrategia}'. Notas: {notas or 'N/A'}",
            tenant_id=tenant_id
        )

        return {
            "exito": True,
            "sync_id": sync_id,
            "estado": "CONFLICTO_RESUELTO",
            "estrategia": estrategia,
            "mensaje": f"Conflicto #{sync_id} resuelto satisfactoriamente."
        }
