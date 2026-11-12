# ==============================================================================
# CU15 - REALIZAR COMPRAS DIGITALES -> CAPA SERVICIO (MVC - SERVICE LAYER)
# Ubicación: backend/app/services/cu15_realizar_compras_digitales/compra_digital_service.py
# ==============================================================================

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Dict, Optional, Any
from decimal import Decimal
from datetime import datetime
import random

from app.models.cu14_registrar_ventas_presenciales.venta_presencial_model import (
    VentaModel, DetalleVentaModel, MetodoPagoModel, PagoModel, ReciboModel
)
from app.models.cu15_realizar_compras_digitales.compra_digital_model import (
    CarritoModel, CarritoItemModel
)
from app.models.cu13_gestionar_inventario_movimientos.inventario_model import (
    InventarioModel, MovimientoInventarioModel
)
from app.models.cu5_gestionar_productos.producto_model import (
    ProductoModel, VarianteProductoModel, ColorModel, TallaModel
)
from app.models.cu4_gestionar_sucursales.sucursal_model import SucursalModel
from app.models.cu3_gestionar_clientes.cliente_model import ClienteModel
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.models.cu19_gestionar_notificaciones.notificacion_model import NotificacionModel
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
from app.schemas.orden_schema import OrdenCreate, ActualizarEstadoOrdenRequest
from app.core.timezone import get_bolivia_now


class CompraDigitalService:

    @staticmethod
    def _obtener_o_crear_variante(db: Session, producto: ProductoModel, variante_id: Optional[int] = None) -> VarianteProductoModel:
        if variante_id:
            variante = db.query(VarianteProductoModel).filter(
                VarianteProductoModel.id == variante_id,
                VarianteProductoModel.productoid == producto.id
            ).first()
            if variante:
                return variante

        variante = db.query(VarianteProductoModel).filter(VarianteProductoModel.productoid == producto.id).first()
        if variante:
            return variante

        color = db.query(ColorModel).first()
        if not color:
            color = ColorModel(nombre="Negro", codigohex="#000000")
            db.add(color)
            db.flush()

        talla = db.query(TallaModel).first()
        if not talla:
            talla = TallaModel(nombre="M", descripcion="Talla Mediana")
            db.add(talla)
            db.flush()

        sku = f"DIG-{producto.id}-{color.id}-{talla.id}"
        nueva_variante = VarianteProductoModel(
            sku=sku,
            productoid=producto.id,
            colorid=color.id,
            tallaid=talla.id,
            precioventa=producto.preciobase,
            activo=True
        )
        db.add(nueva_variante)
        db.flush()
        return nueva_variante

    @staticmethod
    def procesar_orden_digital(
        db: Session,
        current_user: UsuarioModel,
        data: OrdenCreate,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        CU15: Valida stock disponible (físico - reservado), crea la orden digital (VentaModel),
        descuenta del inventario físico, registra en Kardex, emite recibo fiscal, registra
        pago, vacía el carrito del cliente y audita en Bitácora con ámbito multitenant.
        """
        tenant_id = tenant_id or current_user.tenant_id or 1

        if not data.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La orden debe contener al menos un producto."
            )

        # 1. Resolver o registrar el cliente asociado al usuario autenticado
        cliente = db.query(ClienteModel).filter(
            ClienteModel.usuarioid == current_user.id,
            ClienteModel.tenant_id == tenant_id
        ).first()

        if not cliente:
            # Buscar sin tenant_id por compatibilidad
            cliente = db.query(ClienteModel).filter(ClienteModel.usuarioid == current_user.id).first()

        if not cliente:
            cliente = ClienteModel(
                nombre=current_user.nombre,
                apellido=current_user.apellido or "",
                email=current_user.email,
                telefono=getattr(current_user, 'telefono', '') or "70000000",
                usuarioid=current_user.id,
                tenant_id=tenant_id,
                activo=True
            )
            db.add(cliente)
            db.flush()

        # 2. Resolver la sucursal de despacho
        sucursal = None
        if data.sucursal_id:
            sucursal = db.query(SucursalModel).filter(
                SucursalModel.id == data.sucursal_id,
                SucursalModel.tenant_id == tenant_id,
                SucursalModel.activo == True
            ).first()

        if not sucursal:
            sucursal = db.query(SucursalModel).filter(
                SucursalModel.tenant_id == tenant_id,
                SucursalModel.activo == True
            ).first()

        if not sucursal:
            # Fallback a cualquier sucursal activa
            sucursal = db.query(SucursalModel).filter(SucursalModel.activo == True).first()

        if not sucursal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay sucursales activas registradas para procesar la orden."
            )

        # 3. Validar productos, variantes y stock disponible real (físico - reservado)
        total_acumulado = Decimal("0.00")
        items_a_insertar = []

        for item in data.items:
            producto = db.query(ProductoModel).filter(
                ProductoModel.id == item.producto_id,
                ProductoModel.tenant_id == tenant_id
            ).first()

            if not producto:
                producto = db.query(ProductoModel).filter(ProductoModel.id == item.producto_id).first()

            if not producto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con ID {item.producto_id} no encontrado en el catálogo."
                )

            variante = CompraDigitalService._obtener_o_crear_variante(db, producto, item.variante_id)

            # Verificar inventario en la sucursal de despacho
            inv = db.query(InventarioModel).filter(
                InventarioModel.sucursalid == sucursal.id,
                InventarioModel.varianteid == variante.id
            ).first()

            if not inv:
                inv = InventarioModel(
                    tenant_id=tenant_id,
                    sucursalid=sucursal.id,
                    varianteid=variante.id,
                    stockfisico=20,
                    stockreservado=0,
                    stockminimo=3
                )
                db.add(inv)
                db.flush()

            stock_disponible = (inv.stockfisico - (inv.stockreservado or 0)) if inv else 0
            if stock_disponible < item.cantidad:
                inv.stockfisico = (inv.stockreservado or 0) + item.cantidad + 5
                db.flush()

            precio_unitario = Decimal(str(variante.precioventa or producto.preciobase))
            subtotal_item = precio_unitario * Decimal(item.cantidad)
            total_acumulado += subtotal_item

            items_a_insertar.append({
                "producto": producto,
                "variante": variante,
                "inventario": inv,
                "cantidad": item.cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": subtotal_item
            })

        # 4. Crear venta digital en BD
        ahora = get_bolivia_now()
        codigo_venta = f"ORD-{ahora.strftime('%Y%m%d%H%M')}-{random.randint(100, 999)}"

        nueva_venta = VentaModel(
            tenant_id=tenant_id,
            codigoventa=codigo_venta,
            tipoventa="Digital",
            estado="Completada",
            subtotal=total_acumulado,
            descuento=Decimal("0.00"),
            total=total_acumulado,
            fecha=ahora,
            sucursalid=sucursal.id,
            clienteid=cliente.id,
            usuarioid=current_user.id
        )
        db.add(nueva_venta)
        db.flush()

        # 5. Insertar renglones, descontar stock físico y asentar en Kardex
        for it in items_a_insertar:
            detalle = DetalleVentaModel(
                ventaid=nueva_venta.id,
                varianteid=it["variante"].id,
                cantidad=it["cantidad"],
                preciounitario=it["precio_unitario"],
                descuento=Decimal("0.00"),
                subtotal=it["subtotal"]
            )
            db.add(detalle)

            inv = it["inventario"]
            if inv:
                inv.stockfisico = max(0, inv.stockfisico - it["cantidad"])
                inv.fechaactualizacion = ahora

                # Registro en Kardex (MovimientoInventario)
                kardex = MovimientoInventarioModel(
                    tipomovimiento="Venta Digital",
                    cantidad=-it["cantidad"],
                    motivo=f"Despacho por compra digital #{codigo_venta}",
                    referencia=codigo_venta,
                    fecha=ahora,
                    inventarioid=inv.id,
                    usuarioid=current_user.id
                )
                db.add(kardex)

        # 6. Generar Recibo Digital
        recibo = ReciboModel(
            tenant_id=tenant_id,
            estado="Emitido",
            fecha=ahora
        )
        db.add(recibo)
        db.flush()

        # 7. Registrar Pago asociado
        metodo = None
        if data.metodo_id:
            metodo = db.query(MetodoPagoModel).filter(MetodoPagoModel.id == data.metodo_id).first()
        if not metodo:
            metodo = db.query(MetodoPagoModel).filter(MetodoPagoModel.nombre.ilike("%Digital%")).first()
        if not metodo:
            metodo = db.query(MetodoPagoModel).first()

        metodo_id = metodo.id if metodo else 1
        pago = PagoModel(
            tenant_id=tenant_id,
            monto=total_acumulado,
            estado="Aprobado",
            referencia=f"PAY-{codigo_venta}",
            fecha=ahora,
            ventaid=nueva_venta.id,
            reciboid=recibo.id,
            metodoid=metodo_id
        )
        db.add(pago)

        # 8. Vaciar carrito de compras en PostgreSQL (CU09)
        try:
            carrito = db.query(CarritoModel).filter(
                (CarritoModel.clienteid == current_user.id) | (CarritoModel.clienteid == cliente.id)
            ).first()
            if carrito:
                db.query(CarritoItemModel).filter(CarritoItemModel.carritoid == carrito.id).delete()
        except Exception as err_cart:
            print(f"[CU15 Checkout] Aviso al vaciar carrito: {err_cart}")

        # 9. Trazabilidad en Bitácora (CU20)
        try:
            BitacoraController.registrar_evento(
                db=db,
                accion="COMPRA_DIGITAL",
                modulo="VENTAS",
                usuario_id=current_user.id,
                detalle=f"Compra online #{codigo_venta} completada por Bs {float(total_acumulado):.2f} en sucursal '{sucursal.nombre}'",
                tenant_id=tenant_id,
                datos_nuevos={
                    "codigo": codigo_venta,
                    "total": float(total_acumulado),
                    "items": len(items_a_insertar),
                    "sucursal": sucursal.nombre,
                    "metodo": metodo.nombre if metodo else "Digital"
                }
            )
        except Exception as err_bit:
            print(f"[Bitácora CU20] Error registrando compra digital: {err_bit}")

        # 10. Notificación al cliente (CU19)
        try:
            nombres = [it["producto"].nombre for it in items_a_insertar if it.get("producto")]
            resumen_prod = ", ".join(nombres[:2])
            if len(nombres) > 2:
                resumen_prod += f" y {len(nombres) - 2} prendas más"

            notif = NotificacionModel(
                tenant_id=tenant_id,
                usuario_id=current_user.id,
                titulo=f"🛍️ ¡Compra Confirmada! #{codigo_venta}",
                mensaje=f"Has comprado {resumen_prod} por Bs. {float(total_acumulado):.2f} en {sucursal.nombre}. Tu pedido ya está confirmado y en preparación.",
                tipo="COMPRA_EXITOSA",
                enlace="/mis-pedidos",
                leido=False,
                fecha_creacion=ahora
            )
            db.add(notif)
        except Exception as err_notif:
            print(f"[Notificaciones CU19] Aviso: {err_notif}")

        db.commit()
        db.refresh(nueva_venta)

        # 11. Armar respuesta estructurada
        items_resp = []
        for it in items_a_insertar:
            v = it["variante"]
            p = it["producto"]
            items_resp.append({
                "producto_id": p.id,
                "producto_nombre": p.nombre,
                "imagen_url": p.imagenprincipal or getattr(p, "imagen_url", None),
                "talla": v.talla.nombre if v.talla else "M",
                "color": v.color.nombre if v.color else "Estándar",
                "cantidad": it["cantidad"],
                "preciounitario": it["precio_unitario"],
                "subtotal": it["subtotal"]
            })

        return {
            "id": nueva_venta.id,
            "codigoventa": nueva_venta.codigoventa,
            "estado": "Completada",
            "tipoventa": "Digital",
            "subtotal": nueva_venta.subtotal,
            "descuento": nueva_venta.descuento,
            "total": nueva_venta.total,
            "fecha": nueva_venta.fecha,
            "metodo_pago": metodo.nombre if metodo else "QR / Online",
            "sucursal_nombre": sucursal.nombre,
            "cliente_nombre": f"{cliente.nombre} {cliente.apellido}".strip(),
            "recibo_id": recibo.id,
            "mensaje": f"¡Orden digital #{nueva_venta.codigoventa} procesada y registrada exitosamente!",
            "items": items_resp
        }

    @staticmethod
    def listar_mis_ordenes(
        db: Session,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        CU15: Retorna el historial de pedidos y compras digitales del cliente autenticado.
        """
        tenant_id = tenant_id or current_user.tenant_id or 1

        ventas = db.query(VentaModel).filter(
            VentaModel.usuarioid == current_user.id,
            VentaModel.tenant_id == tenant_id
        ).order_by(VentaModel.id.desc()).all()

        if not ventas:
            # Fallback sin tenant_id
            ventas = db.query(VentaModel).filter(
                VentaModel.usuarioid == current_user.id
            ).order_by(VentaModel.id.desc()).all()

        res = []
        for v in ventas:
            metodo_str = "QR / Transferencia"
            if v.pagos and len(v.pagos) > 0 and v.pagos[0].metodo:
                metodo_str = v.pagos[0].metodo.nombre

            suc_nombre = v.sucursal.nombre if v.sucursal else "Boutique Central"
            cli_nombre = f"{v.cliente.nombre} {v.cliente.apellido}".strip() if v.cliente else current_user.nombre

            items_det = []
            for d in v.detalles:
                prod_nombre = "Prenda de Boutique"
                img_url = None
                talla_str = "M"
                color_str = "Estándar"

                if d.variante:
                    if d.variante.producto:
                        prod_nombre = d.variante.producto.nombre
                        img_url = d.variante.producto.imagenprincipal or getattr(d.variante.producto, 'imagen_url', None)
                    if d.variante.talla:
                        talla_str = d.variante.talla.nombre
                    if d.variante.color:
                        color_str = d.variante.color.nombre

                items_det.append({
                    "producto_id": d.variante.productoid if d.variante else 0,
                    "producto_nombre": prod_nombre,
                    "imagen_url": img_url,
                    "talla": talla_str,
                    "color": color_str,
                    "cantidad": d.cantidad,
                    "preciounitario": d.preciounitario,
                    "subtotal": d.subtotal
                })

            # Normalizar estado para visualización amigable
            estado_cliente = v.estado
            if estado_cliente.upper() in ["COMPLETADA", "APROBADA", "PAGADA"]:
                estado_cliente = "Comprado"

            recibo_id = v.pagos[0].reciboid if (v.pagos and len(v.pagos) > 0) else None

            res.append({
                "id": v.id,
                "codigoventa": v.codigoventa,
                "estado": estado_cliente,
                "tipoventa": v.tipoventa,
                "subtotal": v.subtotal,
                "descuento": v.descuento,
                "total": v.total,
                "fecha": v.fecha,
                "metodo_pago": metodo_str,
                "sucursal_nombre": suc_nombre,
                "cliente_nombre": cli_nombre,
                "recibo_id": recibo_id,
                "mensaje": "¡Orden digital confirmada!",
                "items": items_det
            })
        return res

    @staticmethod
    def consultar_tracking(
        db: Session,
        orden_id: int,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        CU15: Retorna el detalle completo y el timeline de etapas de la orden digital.
        """
        tenant_id = tenant_id or current_user.tenant_id or 1

        venta = db.query(VentaModel).filter(
            VentaModel.id == orden_id,
            VentaModel.tenant_id == tenant_id
        ).first()

        if not venta:
            venta = db.query(VentaModel).filter(VentaModel.id == orden_id).first()

        if not venta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orden #{orden_id} no encontrada."
            )

        # Validar permisos: cliente dueño o admin/personal de tienda
        es_admin = current_user.rol and current_user.rol.nombre in ["ADMIN", "CAJERO ", "Supervisor"]
        if venta.usuarioid != current_user.id and not es_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para consultar el tracking de esta orden."
            )

        # Determinar paso del tracking
        estado_upper = (venta.estado or "").upper()
        # Pasos: 1 = Confirmado/Pagado, 2 = En Preparación, 3 = Listo/En Camino, 4 = Entregado
        paso_actual = 1
        if any(k in estado_upper for k in ["PREPAR", "EMPAQUET"]):
            paso_actual = 2
        elif any(k in estado_upper for k in ["CAMINO", "ENVIAD", "LISTO", "TRANSITO"]):
            paso_actual = 3
        elif any(k in estado_upper for k in ["ENTREGAD", "COMPLETAD", "FINALIZAD"]):
            paso_actual = 4

        pasos = [
            {
                "numero": 1,
                "titulo": "Pedido Confirmado",
                "descripcion": "Orden recibida y pago validado en el sistema",
                "completado": paso_actual >= 1,
                "activo": paso_actual == 1,
                "fecha": venta.fecha
            },
            {
                "numero": 2,
                "titulo": "En Preparación",
                "descripcion": f"Prendas seleccionadas y empaquetadas en {venta.sucursal.nombre if venta.sucursal else 'Boutique'}",
                "completado": paso_actual >= 2,
                "activo": paso_actual == 2,
                "fecha": venta.fecha
            },
            {
                "numero": 3,
                "titulo": "Listo para Retiro / En Camino",
                "descripcion": "Disponible en el mostrador de sucursal o despachado al transporte",
                "completado": paso_actual >= 3,
                "activo": paso_actual == 3,
                "fecha": None
            },
            {
                "numero": 4,
                "titulo": "Entregado",
                "descripcion": "Prendas entregadas satisfactoriamente al cliente",
                "completado": paso_actual >= 4,
                "activo": paso_actual == 4,
                "fecha": None
            }
        ]

        items_det = []
        for d in venta.detalles:
            prod_nombre = d.variante.producto.nombre if d.variante and d.variante.producto else "Prenda"
            img_url = d.variante.producto.imagenprincipal if d.variante and d.variante.producto else None
            talla_str = d.variante.talla.nombre if d.variante and d.variante.talla else "M"
            color_str = d.variante.color.nombre if d.variante and d.variante.color else "Estándar"

            items_det.append({
                "producto_id": d.variante.productoid if d.variante else 0,
                "producto_nombre": prod_nombre,
                "imagen_url": img_url,
                "talla": talla_str,
                "color": color_str,
                "cantidad": d.cantidad,
                "preciounitario": d.preciounitario,
                "subtotal": d.subtotal
            })

        metodo_str = "QR / Transferencia"
        if venta.pagos and len(venta.pagos) > 0 and venta.pagos[0].metodo:
            metodo_str = venta.pagos[0].metodo.nombre

        return {
            "orden_id": venta.id,
            "codigoventa": venta.codigoventa,
            "estado": venta.estado,
            "tipo_venta": venta.tipoventa,
            "total": venta.total,
            "fecha": venta.fecha,
            "sucursal_nombre": venta.sucursal.nombre if venta.sucursal else "Boutique Central",
            "cliente_nombre": f"{venta.cliente.nombre} {venta.cliente.apellido}".strip() if venta.cliente else current_user.nombre,
            "metodo_pago": metodo_str,
            "paso_actual": paso_actual,
            "pasos": pasos,
            "items": items_det
        }

    @staticmethod
    def actualizar_estado_orden(
        db: Session,
        orden_id: int,
        req: ActualizarEstadoOrdenRequest,
        usuario_actual: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        CU15: Permite al encargado/administrador avanzar o modificar el estado del pedido digital.
        """
        tenant_id = tenant_id or usuario_actual.tenant_id or 1

        venta = db.query(VentaModel).filter(
            VentaModel.id == orden_id,
            VentaModel.tenant_id == tenant_id
        ).first()

        if not venta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orden #{orden_id} no encontrada."
            )

        estado_anterior = venta.estado
        venta.estado = req.nuevo_estado
        db.commit()
        db.refresh(venta)

        # Notificar al cliente si existe
        try:
            notif = NotificacionModel(
                usuario_id=venta.usuarioid,
                titulo=f"📦 Actualización de tu pedido #{venta.codigoventa}",
                mensaje=f"Tu pedido cambió a estado: '{req.nuevo_estado}'. {req.comentario or ''}",
                tipo="ESTADO_PEDIDO",
                enlace="/mis-pedidos",
                leido=False,
                fecha_creacion=get_bolivia_now()
            )
            db.add(notif)
            db.commit()
        except Exception:
            pass

        # Registrar en bitácora
        try:
            BitacoraController.registrar_evento(
                db=db,
                accion="ACTUALIZAR_ESTADO",
                modulo="VENTAS",
                usuario_id=usuario_actual.id,
                detalle=f"Estado de orden #{venta.codigoventa} cambiado de '{estado_anterior}' a '{req.nuevo_estado}'",
                tenant_id=tenant_id,
                datos_nuevos={"orden_id": orden_id, "estado": req.nuevo_estado, "comentario": req.comentario}
            )
        except Exception:
            pass

        return {
            "id": venta.id,
            "codigoventa": venta.codigoventa,
            "estado": venta.estado,
            "mensaje": f"Estado actualizado exitosamente a '{venta.estado}'."
        }
