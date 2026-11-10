# ==============================================================================
# CU25 - GESTIONAR CAMBIOS Y DEVOLUCIONES DE PRENDAS -> SERVICIO (MVC - SERVICE)
# Ubicación: backend/app/services/cu25_gestionar_cambios_devoluciones/devolucion_service.py
# ==============================================================================

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from app.models.cu25_gestionar_cambios_devoluciones.devolucion_model import Devolucion, DetalleDevolucion
from app.models.cu14_registrar_ventas_presenciales.venta_presencial_model import (
    VentaModel, DetalleVentaModel
)
from app.models.cu13_gestionar_inventario_movimientos.inventario_model import (
    InventarioModel, MovimientoInventarioModel
)
from app.models.cu5_gestionar_productos.producto_model import VarianteProductoModel, ProductoModel
from app.models.cu3_gestionar_clientes.cliente_model import ClienteModel
from app.models.cu4_gestionar_sucursales.sucursal_model import SucursalModel
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.models.cu19_gestionar_notificaciones.notificacion_model import NotificacionModel
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController


class DevolucionService:
    """
    Motor de Gestión de Cambios y Devoluciones de Prendas (CU25).
    - Valida plazos comerciales de devolución (por defecto 15 días calendario).
    - Inspección física de prenda:
        * PERFECTO_ESTADO -> Reingreso inmediato a stock comercial disponible.
        * DEFECTUOSO_FABRICA -> Baja a cuarentena/merma sin ingreso comercial.
    - Soporta Cambios de Talla, Cambios de Prenda, Reembolsos Monetarios y Notas de Crédito.
    - Trazabilidad en Kardex y emisión de Comprobante de Cambio oficial.
    - Notificaciones al cliente (CU19) y Auditoría Nativa en Bitácora (CU26).
    """

    @staticmethod
    def _extraer_nombre_atributo(obj: Any, attr: str, default: str = "") -> str:
        val = getattr(obj, attr, None)
        if val is None:
            return default
        if hasattr(val, "nombre"):
            return str(val.nombre or default)
        return str(val)

    @classmethod
    def validar_venta_para_cambio(
        cls,
        db: Session,
        tenant_id: int,
        venta_id: Any,
        plazo_dias: int = 15
    ) -> Dict[str, Any]:
        """
        Verifica si la venta existe (por ID numérico o por Código de Venta como VTA-SYNC-...),
        si está dentro del plazo de garantía y lista las prendas adquiridas.
        """
        raw_query = str(venta_id).strip()
        venta = None

        if raw_query.isdigit():
            venta = db.query(VentaModel).filter(
                VentaModel.id == int(raw_query),
                VentaModel.tenant_id == tenant_id
            ).first()

        if not venta:
            venta = db.query(VentaModel).filter(
                VentaModel.tenant_id == tenant_id,
                VentaModel.codigoventa.ilike(f"%{raw_query}%")
            ).order_by(desc(VentaModel.id)).first()

        if not venta:
            return {
                "venta_valida": False,
                "venta_id": int(raw_query) if raw_query.isdigit() else 0,
                "codigoventa": "NO_EXISTE",
                "fecha_venta": datetime.utcnow(),
                "dias_transcurridos": 0,
                "dentro_de_plazo": False,
                "plazo_maximo_dias": plazo_dias,
                "cliente_nombre": "Desconocido",
                "sucursal_nombre": "Desconocida",
                "total_venta": 0.0,
                "items_comprados": [],
                "mensaje": f"No se encontró la venta '{raw_query}' en tu empresa actual."
            }

        ahora = datetime.utcnow()
        dias_transcurridos = max(0, (ahora - (venta.fecha or ahora)).days)
        dentro_de_plazo = dias_transcurridos <= plazo_dias

        # Obtener datos de cliente y sucursal
        cli = db.query(ClienteModel).filter(ClienteModel.id == venta.clienteid).first()
        cliente_nom = f"{cli.nombre} {cli.apellido or ''}".strip() if cli else "Cliente Mostrador"

        suc = db.query(SucursalModel).filter(SucursalModel.id == venta.sucursalid).first()
        suc_nom = suc.nombre if suc else f"Sucursal #{venta.sucursalid}"

        # Obtener items de DetalleVenta
        detalles_venta = db.query(
            DetalleVentaModel,
            VarianteProductoModel,
            ProductoModel
        ).join(
            VarianteProductoModel, DetalleVentaModel.varianteid == VarianteProductoModel.id
        ).join(
            ProductoModel, VarianteProductoModel.productoid == ProductoModel.id
        ).filter(
            DetalleVentaModel.ventaid == venta.id
        ).all()

        items_dto = []
        for det, var, prod in detalles_venta:
            items_dto.append({
                "variante_id": det.varianteid,
                "sku": getattr(var, "sku", f"VAR-{det.varianteid}"),
                "producto_nombre": getattr(prod, "nombre", "Prenda"),
                "talla": cls._extraer_nombre_atributo(var, "talla", "M"),
                "color": cls._extraer_nombre_atributo(var, "color", "Estándar"),
                "cantidad_comprada": det.cantidad,
                "precio_unitario": float(det.preciounitario),
                "subtotal": float(det.subtotal)
            })

        mensaje = "Venta apta para cambio o devolución dentro del plazo oficial." if dentro_de_plazo else (
            f"El plazo de garantía de {plazo_dias} días ha expirado ({dias_transcurridos} días transcurridos)."
        )

        return {
            "venta_valida": True,
            "venta_id": venta.id,
            "codigoventa": venta.codigoventa,
            "fecha_venta": venta.fecha,
            "dias_transcurridos": dias_transcurridos,
            "dentro_de_plazo": dentro_de_plazo,
            "plazo_maximo_dias": plazo_dias,
            "cliente_nombre": cliente_nom,
            "sucursal_nombre": suc_nom,
            "total_venta": float(venta.total),
            "items_comprados": items_dto,
            "mensaje": mensaje
        }

    @classmethod
    def solicitar_devolucion(
        cls,
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
    ) -> Devolucion:
        """
        Procesa el cambio de prenda o devolución monetaria, actualizando inventario, Kardex,
        notificando al cliente y auditando en Bitácora.
        """
        venta = db.query(VentaModel).filter(
            VentaModel.id == venta_id,
            VentaModel.tenant_id == tenant_id
        ).first()

        codigo = f"DEV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        cli_id = cliente_id or (venta.clienteid if venta else 1)
        if venta and venta.sucursalid:
            sucursal_id = venta.sucursalid

        devolucion = Devolucion(
            tenant_id=tenant_id,
            venta_id=venta_id,
            cliente_id=cli_id,
            usuario_id=usuario_id,
            sucursal_id=sucursal_id,
            codigo_devolucion=codigo,
            tipo_devolucion=tipo_devolucion,
            motivo=motivo,
            estado="APROBADA",
            monto_reembolso=monto_reembolso,
            reingreso_inventario=True,
            fecha_solicitud=datetime.utcnow(),
            fecha_resolucion=datetime.utcnow()
        )
        db.add(devolucion)
        db.flush()

        total_prendas_reingresadas = 0
        total_prendas_baja_defecto = 0

        for item in items:
            v_dev_id = item["variante_devuelta_id"]
            v_new_id = item.get("variante_nueva_id")
            cant = int(item.get("cantidad", 1))
            pu = float(item.get("precio_unitario", 0.0))
            sub = float(item.get("subtotal", cant * pu))
            estado_prenda = item.get("estado_prenda", "PERFECTO_ESTADO")

            det = DetalleDevolucion(
                devolucion_id=devolucion.id,
                variante_devuelta_id=v_dev_id,
                variante_nueva_id=v_new_id,
                cantidad=cant,
                precio_unitario=pu,
                subtotal=sub,
                estado_prenda=estado_prenda
            )
            db.add(det)

            # 1. Tratamiento de la prenda devuelta
            if estado_prenda == "PERFECTO_ESTADO":
                # Reingreso al stock físico comercial disponible
                inv_devuelto = db.query(InventarioModel).filter(
                    InventarioModel.varianteid == v_dev_id,
                    InventarioModel.sucursalid == sucursal_id,
                    InventarioModel.tenant_id == tenant_id
                ).first()

                if not inv_devuelto:
                    inv_devuelto = InventarioModel(
                        tenant_id=tenant_id,
                        sucursalid=sucursal_id,
                        varianteid=v_dev_id,
                        stockfisico=cant,
                        stockreservado=0,
                        stockminimo=5
                    )
                    db.add(inv_devuelto)
                    db.flush()
                else:
                    inv_devuelto.stockfisico = (inv_devuelto.stockfisico or 0) + cant

                # Movimiento de entrada en Kardex
                mov_in = MovimientoInventarioModel(
                    tenant_id=tenant_id,
                    tipomovimiento="ENTRADA_DEVOLUCION_STOCK",
                    cantidad=cant,
                    motivo=f"Reingreso de prenda apta #{codigo}: {motivo}",
                    referencia=codigo,
                    inventarioid=inv_devuelto.id,
                    usuarioid=usuario_id or 1
                )
                db.add(mov_in)
                total_prendas_reingresadas += cant

            else:
                # Prenda defectuosa -> Salida a Merma/Garantía sin reintegrar a vitrina
                inv_devuelto = db.query(InventarioModel).filter(
                    InventarioModel.varianteid == v_dev_id,
                    InventarioModel.sucursalid == sucursal_id,
                    InventarioModel.tenant_id == tenant_id
                ).first()

                inv_id = inv_devuelto.id if inv_devuelto else 1

                mov_merma = MovimientoInventarioModel(
                    tenant_id=tenant_id,
                    tipomovimiento="MERMA_DEFECTO_FABRICA",
                    cantidad=cant,
                    motivo=f"Baja por prenda defectuosa #{codigo}: {motivo}",
                    referencia=codigo,
                    inventarioid=inv_id,
                    usuarioid=usuario_id or 1
                )
                db.add(mov_merma)
                total_prendas_baja_defecto += cant

            # 2. Si es cambio por otra variante (variante_nueva_id)
            if v_new_id:
                inv_nuevo = db.query(InventarioModel).filter(
                    InventarioModel.varianteid == v_new_id,
                    InventarioModel.sucursalid == sucursal_id,
                    InventarioModel.tenant_id == tenant_id
                ).first()

                if inv_nuevo:
                    inv_nuevo.stockfisico = max(0, (inv_nuevo.stockfisico or 0) - cant)
                    mov_out = MovimientoInventarioModel(
                        tenant_id=tenant_id,
                        tipomovimiento="SALIDA_CAMBIO_PRENDA",
                        cantidad=cant,
                        motivo=f"Salida de prenda entregada por cambio #{codigo}",
                        referencia=codigo,
                        inventarioid=inv_nuevo.id,
                        usuarioid=usuario_id or 1
                    )
                    db.add(mov_out)

        # 3. Notificación al cliente (CU19)
        usuario_destinatario_id = None
        if cli_id:
            cliente_obj = db.query(ClienteModel).filter(ClienteModel.id == cli_id).first()
            if cliente_obj and cliente_obj.usuarioid:
                if db.query(UsuarioModel).filter(UsuarioModel.id == cliente_obj.usuarioid).first():
                    usuario_destinatario_id = cliente_obj.usuarioid

        if usuario_destinatario_id:
            notif = NotificacionModel(
                tenant_id=tenant_id,
                usuario_id=usuario_destinatario_id,
                titulo=f"Comprobante de {tipo_devolucion} #{codigo}",
                mensaje=(
                    f"Tu solicitud de {tipo_devolucion} por Bs. {monto_reembolso:,.2f} ha sido procesada "
                    f"satisfactoriamente en la sucursal. Comprobante: {codigo}."
                ),
                tipo="DEVOLUCION_PROCESADA",
                leido=False,
                enlace="/historial"
            )
            db.add(notif)

        # 4. Auditoría en Bitácora (CU26)
        BitacoraController.registrar_accion(
            db=db,
            usuario_id=usuario_id,
            accion="REGISTRAR_DEVOLUCION",
            modulo="VENTAS",
            detalle=(
                f"{tipo_devolucion} #{codigo} aprobada para Venta #{venta_id}. "
                f"Reembolso: Bs. {monto_reembolso:,.2f}. "
                f"Prendas aptas: {total_prendas_reingresadas}, Merma defecto: {total_prendas_baja_defecto}."
            ),
            tenant_id=tenant_id,
            datos_nuevos={"codigo_devolucion": codigo, "tipo": tipo_devolucion, "monto": monto_reembolso}
        )

        db.commit()
        db.refresh(devolucion)
        listado = cls.listar_devoluciones(db=db, tenant_id=tenant_id)
        for item_dto in listado:
            if item_dto["id"] == devolucion.id:
                return item_dto
        return devolucion

    @classmethod
    def listar_devoluciones(
        cls,
        db: Session,
        tenant_id: int,
        sucursal_id: Optional[int] = None,
        tipo: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista todas las devoluciones y cambios registrados con metadatos completos y detalles de prendas.
        """
        query = db.query(
            Devolucion,
            VentaModel.codigoventa.label("vta_codigo"),
            UsuarioModel.nombre.label("usr_nombre"),
            SucursalModel.nombre.label("suc_nombre"),
            ClienteModel.nombre.label("cli_nombre"),
            ClienteModel.apellido.label("cli_apellido")
        ).outerjoin(
            VentaModel, Devolucion.venta_id == VentaModel.id
        ).outerjoin(
            UsuarioModel, Devolucion.usuario_id == UsuarioModel.id
        ).outerjoin(
            SucursalModel, Devolucion.sucursal_id == SucursalModel.id
        ).outerjoin(
            ClienteModel, Devolucion.cliente_id == ClienteModel.id
        ).filter(
            Devolucion.tenant_id == tenant_id
        )

        if sucursal_id:
            query = query.filter(Devolucion.sucursal_id == sucursal_id)
        if tipo and tipo != "TODOS":
            query = query.filter(Devolucion.tipo_devolucion == tipo)

        rows = query.order_by(desc(Devolucion.id)).all()

        resultado = []
        for dev, v_cod, u_nom, s_nom, c_nom, c_ape in rows:
            cli_full = f"{c_nom or 'Cliente'} {c_ape or ''}".strip()

            # Consultar detalles
            detalles_query = db.query(DetalleDevolucion).filter(
                DetalleDevolucion.devolucion_id == dev.id
            ).all()

            detalles_dto = []
            for d in detalles_query:
                # Variante devuelta
                var_dev = db.query(VarianteProductoModel).filter(VarianteProductoModel.id == d.variante_devuelta_id).first()
                prod_dev = db.query(ProductoModel).filter(ProductoModel.id == var_dev.productoid).first() if var_dev else None

                # Variante nueva (si hubo cambio)
                var_new = db.query(VarianteProductoModel).filter(VarianteProductoModel.id == d.variante_nueva_id).first() if d.variante_nueva_id else None
                prod_new = db.query(ProductoModel).filter(ProductoModel.id == var_new.productoid).first() if var_new else None

                detalles_dto.append({
                    "id": d.id,
                    "variante_devuelta_id": d.variante_devuelta_id,
                    "variante_devuelta_sku": var_dev.sku if var_dev else None,
                    "producto_devuelto_nombre": prod_dev.nombre if prod_dev else f"Prenda #{d.variante_devuelta_id}",
                    "talla_devuelta": cls._extraer_nombre_atributo(var_dev, "talla", "M") if var_dev else None,
                    "color_devuelto": cls._extraer_nombre_atributo(var_dev, "color", "Estándar") if var_dev else None,
                    "variante_nueva_id": d.variante_nueva_id,
                    "variante_nueva_sku": var_new.sku if var_new else None,
                    "producto_nuevo_nombre": prod_new.nombre if prod_new else None,
                    "talla_nueva": cls._extraer_nombre_atributo(var_new, "talla", "M") if var_new else None,
                    "color_nueva": cls._extraer_nombre_atributo(var_new, "color", "Estándar") if var_new else None,
                    "cantidad": d.cantidad,
                    "precio_unitario": float(d.precio_unitario),
                    "subtotal": float(d.subtotal),
                    "estado_prenda": d.estado_prenda
                })

            resultado.append({
                "id": dev.id,
                "codigo_devolucion": dev.codigo_devolucion,
                "tenant_id": dev.tenant_id,
                "venta_id": dev.venta_id,
                "codigoventa": v_cod or f"VTA-{dev.venta_id}",
                "cliente_id": dev.cliente_id,
                "cliente_nombre": cli_full,
                "usuario_id": dev.usuario_id,
                "usuario_nombre": u_nom or "Encargado de Caja",
                "sucursal_id": dev.sucursal_id,
                "sucursal_nombre": s_nom or f"Sucursal #{dev.sucursal_id}",
                "tipo_devolucion": dev.tipo_devolucion,
                "motivo": dev.motivo,
                "estado": dev.estado,
                "monto_reembolso": float(dev.monto_reembolso or 0.0),
                "reingreso_inventario": dev.reingreso_inventario,
                "fecha_solicitud": dev.fecha_solicitud,
                "fecha_resolucion": dev.fecha_resolucion,
                "detalles": detalles_dto
            })

        return resultado

    @classmethod
    def obtener_kpis(cls, db: Session, tenant_id: int, plazo_dias: int = 15) -> Dict[str, Any]:
        """
        Calcula indicadores clave de cambios y devoluciones para el dashboard gerencial.
        """
        total = db.query(func.count(Devolucion.id)).filter(
            Devolucion.tenant_id == tenant_id
        ).scalar() or 0

        cambios = db.query(func.count(Devolucion.id)).filter(
            Devolucion.tenant_id == tenant_id,
            Devolucion.tipo_devolucion.in_(["CAMBIO_TALLA", "CAMBIO_PRENDA"])
        ).scalar() or 0

        reembolsos = db.query(func.count(Devolucion.id)).filter(
            Devolucion.tenant_id == tenant_id,
            Devolucion.tipo_devolucion.in_(["REEMBOLSO_TOTAL", "NOTA_CREDITO"])
        ).scalar() or 0

        monto_total = db.query(func.coalesce(func.sum(Devolucion.monto_reembolso), 0.0)).filter(
            Devolucion.tenant_id == tenant_id
        ).scalar() or 0.0

        # Prendas aptas reincorporadas al stock
        aptas = db.query(func.coalesce(func.sum(DetalleDevolucion.cantidad), 0)).join(
            Devolucion, DetalleDevolucion.devolucion_id == Devolucion.id
        ).filter(
            Devolucion.tenant_id == tenant_id,
            DetalleDevolucion.estado_prenda == "PERFECTO_ESTADO"
        ).scalar() or 0

        # Prendas dadas de baja por defecto
        defectos = db.query(func.coalesce(func.sum(DetalleDevolucion.cantidad), 0)).join(
            Devolucion, DetalleDevolucion.devolucion_id == Devolucion.id
        ).filter(
            Devolucion.tenant_id == tenant_id,
            DetalleDevolucion.estado_prenda != "PERFECTO_ESTADO"
        ).scalar() or 0

        return {
            "total_operaciones": total,
            "cambios_talla_prenda": cambios,
            "reembolsos_notas_credito": reembolsos,
            "prendas_aptas_reincorporadas": int(aptas),
            "prendas_baja_defecto": int(defectos),
            "monto_total_reembolsado_bob": round(float(monto_total), 2),
            "plazo_garantia_dias": plazo_dias
        }
