# ==============================================================================
# CU17 - CONSULTAR HISTORIAL DE COMPRAS Y RESERVAS -> CAPA SERVICIO (MVC - SERVICE LAYER)
# Ubicación: backend/app/services/cu17_consultar_historial_compras_reservas/historial_service.py
# ==============================================================================

from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import io
import base64

from app.models.cu14_registrar_ventas_presenciales.venta_presencial_model import (
    VentaModel, DetalleVentaModel, PagoModel, MetodoPagoModel
)
from app.models.cu10_gestionar_reservas_prendas.reserva_model import (
    ReservaModel, ReservaDetalleModel
)
from app.models.cu5_gestionar_productos.producto_model import (
    ProductoModel, VarianteProductoModel
)
from app.models.cu4_gestionar_sucursales.sucursal_model import SucursalModel
from app.models.cu3_gestionar_clientes.cliente_model import ClienteModel
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.core.timezone import get_bolivia_now


def generar_qr_base64(contenido: str) -> str:
    """Genera código QR en formato Base64 para retiro de reservas o comprobantes"""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(contenido)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    except Exception as e:
        print(f"[CU17 QR] Aviso: {e}")
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><rect width="160" height="160" fill="#f1f5f9"/><text x="80" y="85" text-anchor="middle" font-size="10">RESERVA QR</text></svg>'
        return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"


class HistorialService:

    @staticmethod
    def _calcular_tracking(venta: VentaModel) -> List[Dict[str, Any]]:
        """Genera el timeline de seguimiento logístico para la venta"""
        estado = (venta.estado or "Pendiente").lower()
        fecha_base = venta.fecha or get_bolivia_now()

        paso1 = {"paso": 1, "titulo": "Pedido Registrado", "fecha": fecha_base.strftime("%d/%m/%Y %H:%M"), "completado": True}
        paso2 = {"paso": 2, "titulo": "Pago Confirmado", "fecha": (fecha_base + timedelta(minutes=5)).strftime("%d/%m/%Y %H:%M"), "completado": False}
        paso3 = {"paso": 3, "titulo": "En Preparación en Tienda", "fecha": (fecha_base + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M"), "completado": False}
        paso4 = {"paso": 4, "titulo": "En Ruta de Entrega / Retiro", "fecha": (fecha_base + timedelta(hours=4)).strftime("%d/%m/%Y %H:%M"), "completado": False}
        paso5 = {"paso": 5, "titulo": "Completado y Entregado", "fecha": (fecha_base + timedelta(hours=6)).strftime("%d/%m/%Y %H:%M"), "completado": False}

        if any(k in estado for k in ["completad", "pagad", "aprobad", "entregad"]):
            paso2["completado"] = True
            paso3["completado"] = True
            paso4["completado"] = True
            paso5["completado"] = True
        elif any(k in estado for k in ["camino", "enviad", "ruta", "listo"]):
            paso2["completado"] = True
            paso3["completado"] = True
            paso4["completado"] = True
        elif any(k in estado for k in ["prepar", "empaquet"]):
            paso2["completado"] = True
            paso3["completado"] = True
        elif "pendiente" in estado:
            paso2["completado"] = False

        return [paso1, paso2, paso3, paso4, paso5]

    @staticmethod
    def obtener_resumen_cliente(
        db: Session,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        CU17: Retorna indicadores clave consolidados del cliente (total pedidos, invertido y reservas activas).
        """
        tenant_id = tenant_id or current_user.tenant_id or 1

        cliente = db.query(ClienteModel).filter(
            ClienteModel.usuarioid == current_user.id,
            ClienteModel.tenant_id == tenant_id
        ).first()

        if not cliente:
            cliente = db.query(ClienteModel).filter(ClienteModel.usuarioid == current_user.id).first()

        cliente_id = cliente.id if cliente else None

        # 1. Compras aisladas por tenant
        condiciones_ventas = [VentaModel.usuarioid == current_user.id]
        if cliente_id:
            condiciones_ventas.append(VentaModel.clienteid == cliente_id)

        ventas_query = db.query(VentaModel).filter(
            VentaModel.tenant_id == tenant_id,
            or_(*condiciones_ventas)
        )

        ventas_list = ventas_query.all()
        total_compras = len(ventas_list)
        total_gastado = sum([float(v.total or 0) for v in ventas_list])

        # 2. Reservas aisladas por tenant
        total_reservas = 0
        reservas_activas = 0
        if cliente_id:
            res_query = db.query(ReservaModel).filter(
                ReservaModel.clienteid == cliente_id,
                ReservaModel.tenant_id == tenant_id
            )
            total_reservas = res_query.count()
            reservas_activas = res_query.filter(
                ReservaModel.estado.in_(["Pendiente", "Confirmada", "PENDIENTE", "CONFIRMADA"])
            ).count()

        return {
            "cliente_nombre": f"{current_user.nombre} {current_user.apellido or ''}".strip(),
            "total_pedidos": total_compras,
            "total_invertido_bs": round(total_gastado, 2),
            "total_reservas": total_reservas,
            "reservas_activas": reservas_activas
        }

    @staticmethod
    def listar_compras_cliente(
        db: Session,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        CU17: Retorna el historial completo de compras con detalle de prendas, tracking y comprobante.
        """
        tenant_id = tenant_id or current_user.tenant_id or 1

        cliente = db.query(ClienteModel).filter(
            ClienteModel.usuarioid == current_user.id,
            ClienteModel.tenant_id == tenant_id
        ).first()
        if not cliente:
            cliente = db.query(ClienteModel).filter(ClienteModel.usuarioid == current_user.id).first()

        cliente_id = cliente.id if cliente else None

        condiciones_ventas = [VentaModel.usuarioid == current_user.id]
        if cliente_id:
            condiciones_ventas.append(VentaModel.clienteid == cliente_id)

        ventas = db.query(VentaModel).filter(
            VentaModel.tenant_id == tenant_id,
            or_(*condiciones_ventas)
        ).order_by(VentaModel.id.desc()).all()

        resultado = []
        for v in ventas:
            suc = db.query(SucursalModel).filter(SucursalModel.id == v.sucursalid).first()
            sucursal_nombre = suc.nombre if suc else "Boutique Central"

            pago = db.query(PagoModel).filter(PagoModel.ventaid == v.id).first()
            metodo_nombre = "Digital"
            if pago and pago.metodo:
                metodo_nombre = pago.metodo.nombre

            detalles = db.query(DetalleVentaModel).filter(DetalleVentaModel.ventaid == v.id).all()
            items = []
            for d in detalles:
                variante = db.query(VarianteProductoModel).filter(VarianteProductoModel.id == d.varianteid).first()
                producto_nombre = "Prenda Exclusiva"
                imagen_url = None
                talla_str = "M"
                color_str = "Estándar"

                if variante:
                    if variante.talla:
                        talla_str = variante.talla.nombre
                    if variante.color:
                        color_str = variante.color.nombre
                    if variante.producto:
                        producto_nombre = variante.producto.nombre
                        imagen_url = variante.producto.imagenprincipal or getattr(variante.producto, 'imagen_url', None)

                items.append({
                    "id": d.varianteid,
                    "producto": producto_nombre,
                    "talla": talla_str,
                    "color": color_str,
                    "cantidad": d.cantidad,
                    "precio_unitario": float(d.preciounitario or 0),
                    "subtotal": float(d.subtotal or 0),
                    "imagen_url": imagen_url
                })

            resultado.append({
                "id": v.id,
                "codigo_venta": v.codigoventa,
                "tipo_venta": v.tipoventa,
                "estado": v.estado,
                "total": float(v.total or 0),
                "fecha": v.fecha.strftime("%d/%m/%Y %H:%M") if v.fecha else "",
                "sucursal": sucursal_nombre,
                "metodo_pago": metodo_nombre,
                "tracking": HistorialService._calcular_tracking(v),
                "items_count": len(items),
                "items": items,
                "comprobante_url": f"/api/v1/pagos/{v.id}/comprobante-html"
            })

        return resultado

    @staticmethod
    def listar_reservas_cliente(
        db: Session,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        CU17: Retorna el historial de reservas de prendas con QR para retiro en tienda y tiempo restante de 48h.
        """
        tenant_id = tenant_id or current_user.tenant_id or 1

        cliente = db.query(ClienteModel).filter(
            ClienteModel.usuarioid == current_user.id,
            ClienteModel.tenant_id == tenant_id
        ).first()
        if not cliente:
            cliente = db.query(ClienteModel).filter(ClienteModel.usuarioid == current_user.id).first()

        if not cliente:
            return []

        reservas = db.query(ReservaModel).filter(
            ReservaModel.clienteid == cliente.id,
            ReservaModel.tenant_id == tenant_id
        ).order_by(ReservaModel.id.desc()).all()

        resultado = []
        ahora = get_bolivia_now()

        for r in reservas:
            suc = db.query(SucursalModel).filter(SucursalModel.id == r.sucursalid).first()
            sucursal_nombre = suc.nombre if suc else "Boutique Central"
            sucursal_direccion = suc.direccion if suc else "Av. San Martín #450, Equipetrol"

            fecha_res = r.fechareserva or ahora
            fecha_limite = fecha_res + timedelta(hours=48)
            diff = fecha_limite - ahora
            horas_restantes = max(0.0, round(diff.total_seconds() / 3600, 1))

            qr_base64 = generar_qr_base64(
                f"RESERVA:{r.codigoreserva}|CLIENTE:{current_user.email}|SUCURSAL:{sucursal_nombre}|EXP:{fecha_limite.strftime('%Y-%m-%d %H:%M')}"
            )

            detalles = db.query(ReservaDetalleModel).filter(ReservaDetalleModel.reservaid == r.id).all()
            items = []
            total_estimado = 0.0
            for d in detalles:
                variante = db.query(VarianteProductoModel).filter(VarianteProductoModel.id == d.varianteid).first()
                producto_nombre = "Prenda en Reserva"
                imagen_url = None
                precio_unit = 0.0
                talla_str = "M"
                color_str = "Estándar"

                if variante:
                    precio_unit = float(getattr(variante, 'precioventa', 0) or 0)
                    if variante.talla:
                        talla_str = variante.talla.nombre
                    if variante.color:
                        color_str = variante.color.nombre
                    if variante.producto:
                        producto_nombre = variante.producto.nombre
                        if precio_unit <= 0:
                            precio_unit = float(variante.producto.preciobase or 0)
                        imagen_url = variante.producto.imagenprincipal or getattr(variante.producto, 'imagen_url', None)

                subtotal_item = round(precio_unit * d.cantidad, 2)
                total_estimado += subtotal_item
                items.append({
                    "id": d.varianteid,
                    "producto": producto_nombre,
                    "talla": talla_str,
                    "color": color_str,
                    "cantidad": d.cantidad,
                    "precio_unitario": precio_unit,
                    "subtotal": subtotal_item,
                    "imagen_url": imagen_url
                })

            resultado.append({
                "id": r.id,
                "codigo_reserva": r.codigoreserva,
                "estado": r.estado,
                "total_estimado": round(total_estimado, 2),
                "fecha_reserva": fecha_res.strftime("%d/%m/%Y %H:%M"),
                "fecha_limite": fecha_limite.strftime("%d/%m/%Y %H:%M"),
                "horas_restantes": horas_restantes,
                "sucursal_nombre": sucursal_nombre,
                "sucursal_direccion": sucursal_direccion,
                "qr_retiro": qr_base64,
                "items": items
            })

        return resultado
