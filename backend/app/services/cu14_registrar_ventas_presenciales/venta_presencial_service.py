# ==============================================================================
# CU14 - REGISTRAR VENTAS PRESENCIALES -> CAPA SERVICIO (MVC - SERVICE)
# Arquitectura: Multi-Tenant SaaS, Descuento Atómico de Stock, Emisión de
# Comprobante/Recibo, Control de Existencias Reservadas y Auditoría en Bitácora.
# Ubicación: backend/app/services/cu14_registrar_ventas_presenciales/venta_presencial_service.py
# ==============================================================================

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
import random
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.timezone import get_bolivia_now

from app.models.cu14_registrar_ventas_presenciales.venta_presencial_model import (
    VentaModel,
    DetalleVentaModel,
    MetodoPagoModel,
    PagoModel,
    ReciboModel,
)
from app.models.cu13_gestionar_inventario_movimientos.inventario_model import (
    InventarioModel,
    MovimientoInventarioModel,
)
from app.models.cu5_gestionar_productos.producto_model import (
    ProductoModel,
    VarianteProductoModel,
    ColorModel,
    TallaModel,
)
from app.models.cu4_gestionar_sucursales.sucursal_model import SucursalModel
from app.models.cu3_gestionar_clientes.cliente_model import ClienteModel
from app.models.saas_tenant.tenant_model import Tenant
from app.schemas.orden_schema import VentaPresencialCreate
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController


class VentaPresencialService:
    """
    Servicio de Dominio para el Registro de Ventas Físicas en Mostrador (POS).
    Garantiza aislamiento multitenant estricto (tenant_id), validación de existencias
    disponibles libres de reservas previas, generación de comprobante y trazabilidad en bitácora.
    """

    @classmethod
    def validar_tenant(cls, db: Session, tenant_id: int) -> Tenant:
        """Verifica que el tenant exista en la plataforma SaaS"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant con ID {tenant_id} no existe en la plataforma SaaS",
            )
        return tenant

    @classmethod
    def asegurar_metodos_pago(cls, db: Session) -> None:
        """Garantiza la existencia de métodos de pago estándar para el mostrador"""
        count = db.query(MetodoPagoModel).count()
        if count == 0:
            metodos_defecto = [
                MetodoPagoModel(nombre="Efectivo", estado=True),
                MetodoPagoModel(nombre="Tarjeta de Débito / Crédito", estado=True),
                MetodoPagoModel(nombre="QR / Transferencia Bancaria", estado=True),
                MetodoPagoModel(nombre="Pago Digital / Online", estado=True),
            ]
            db.add_all(metodos_defecto)
            db.commit()

    @classmethod
    def _obtener_o_crear_variante(
        cls, db: Session, producto: ProductoModel, variante_id: Optional[int] = None
    ) -> VarianteProductoModel:
        """Localiza o asocia la variante específica de la prenda a vender"""
        if variante_id:
            variante = (
                db.query(VarianteProductoModel)
                .filter(
                    VarianteProductoModel.id == variante_id,
                    VarianteProductoModel.productoid == producto.id,
                )
                .first()
            )
            if variante:
                return variante

        variante = (
            db.query(VarianteProductoModel)
            .filter(VarianteProductoModel.productoid == producto.id)
            .first()
        )
        if variante:
            return variante

        color = db.query(ColorModel).first()
        if not color:
            color = ColorModel(nombre="Negro", codigohex="#000000", activo=True)
            db.add(color)
            db.flush()

        talla = db.query(TallaModel).first()
        if not talla:
            talla = TallaModel(nombre="M", grupoedad="Adultos", orden=1, activo=True)
            db.add(talla)
            db.flush()

        sku = f"POL-{producto.id}-{color.id}-{talla.id}"
        nueva_variante = VarianteProductoModel(
            sku=sku,
            productoid=producto.id,
            colorid=color.id,
            tallaid=talla.id,
            precioventa=producto.preciobase,
            activo=True,
        )
        db.add(nueva_variante)
        db.flush()
        return nueva_variante

    @classmethod
    def registrar_venta_presencial(
        cls,
        db: Session,
        data: VentaPresencialCreate,
        usuario_id: int,
        tenant_id: int = 1,
        ip_origen: str = "127.0.0.1",
    ) -> Dict:
        """
        Registra una venta física en mostrador:
        1. Valida pertenencia de sucursal, productos y cliente al tenant.
        2. Verifica que las unidades solicitadas no excedan el stock disponible no reservado.
        3. Descuenta existencias físicas y asienta el movimiento en Kardex.
        4. Genera venta, detalles, recibo y pago de caja.
        5. Audita la transacción en la Bitácora (CU26).
        """
        cls.validar_tenant(db, tenant_id)

        if not data.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe ingresar al menos un producto en la venta",
            )

        cls.asegurar_metodos_pago(db)

        # 1. Validar Sucursal en este Tenant
        sucursal = (
            db.query(SucursalModel)
            .filter(
                SucursalModel.id == data.sucursal_id,
                SucursalModel.tenant_id == tenant_id,
                SucursalModel.activo == True,
            )
            .first()
        )
        if not sucursal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sucursal #{data.sucursal_id} no encontrada o no pertenece a este tenant",
            )

        # 2. Resolver Cliente (registrado en el tenant o Consumidor Final)
        cliente = None
        if data.cliente_id:
            cliente = (
                db.query(ClienteModel)
                .filter(
                    ClienteModel.id == data.cliente_id,
                    ClienteModel.tenant_id == tenant_id,
                )
                .first()
            )

        if not cliente:
            cliente = (
                db.query(ClienteModel)
                .filter(
                    ClienteModel.tenant_id == tenant_id,
                    ClienteModel.nombre.ilike("Consumidor Final"),
                )
                .first()
            )
            if not cliente:
                cliente = ClienteModel(
                    tenant_id=tenant_id,
                    nombre=data.cliente_nombre or "Consumidor Final",
                    apellido="",
                    email=f"consumidor_final_t{tenant_id}_{random.randint(1000, 9999)}@tienda.com",
                    telefono="",
                    usuarioid=usuario_id,
                    activo=True,
                )
                db.add(cliente)
                db.flush()

        # 3. Validar Método de Pago
        metodo_pago = (
            db.query(MetodoPagoModel)
            .filter(
                MetodoPagoModel.id == data.metodo_pago_id,
                MetodoPagoModel.estado == True,
            )
            .first()
        )
        if not metodo_pago:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Método de pago #{data.metodo_pago_id} no válido o inactivo",
            )

        # 4. Validar Disponibilidad y Armar Detalles
        total_acumulado = Decimal("0.00")
        items_a_procesar = []

        for item in data.items:
            prod = (
                db.query(ProductoModel)
                .filter(
                    ProductoModel.id == item.producto_id,
                    ProductoModel.tenant_id == tenant_id,
                )
                .first()
            )
            if not prod:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con ID {item.producto_id} no encontrado en este tenant",
                )

            variante = cls._obtener_o_crear_variante(db, prod, item.variante_id)

            inv = (
                db.query(InventarioModel)
                .filter(
                    InventarioModel.sucursalid == sucursal.id,
                    InventarioModel.varianteid == variante.id,
                    InventarioModel.tenant_id == tenant_id,
                )
                .first()
            )

            stock_fisico = inv.stockfisico if inv else 0
            stock_reservado = (inv.stockreservado if inv else 0) or 0
            stock_disponible = max(0, stock_fisico - stock_reservado)

            if not inv or stock_disponible < item.cantidad:
                talla_str = variante.talla.nombre if variante.talla else "M"
                color_str = variante.color.nombre if variante.color else "Estándar"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Stock disponible insuficiente para '{prod.nombre}' (Talla: {talla_str}, Color: {color_str}). "
                        f"Físico: {stock_fisico}, Reservado: {stock_reservado}, "
                        f"Disponible para venta: {stock_disponible}, Solicitado: {item.cantidad}"
                    ),
                )

            precio_unit = Decimal(str(variante.precioventa or prod.preciobase))
            subtotal = precio_unit * Decimal(item.cantidad)
            total_acumulado += subtotal

            items_a_procesar.append({
                "producto": prod,
                "variante": variante,
                "cantidad": item.cantidad,
                "precio_unitario": precio_unit,
                "subtotal": subtotal,
                "inv": inv,
            })

        # 5. Generar Venta Presencial
        ahora = get_bolivia_now()
        codigo_venta = f"POS-{ahora.strftime('%Y%m%d%H%M')}-{random.randint(100, 999)}"

        nueva_venta = VentaModel(
            tenant_id=tenant_id,
            codigoventa=codigo_venta,
            tipoventa="Presencial",
            estado="Completada",
            subtotal=total_acumulado,
            descuento=Decimal("0.00"),
            total=total_acumulado,
            fecha=ahora,
            sucursalid=sucursal.id,
            clienteid=cliente.id,
            usuarioid=usuario_id,
        )
        db.add(nueva_venta)
        db.flush()

        # 6. Renglones de Detalle, Descuento de Stock y Kardex
        for it in items_a_procesar:
            det = DetalleVentaModel(
                ventaid=nueva_venta.id,
                varianteid=it["variante"].id,
                cantidad=it["cantidad"],
                preciounitario=it["precio_unitario"],
                descuento=Decimal("0.00"),
                subtotal=it["subtotal"],
            )
            db.add(det)

            # Descontar stock físico
            it["inv"].stockfisico = max(0, it["inv"].stockfisico - it["cantidad"])
            it["inv"].fechaactualizacion = ahora

            # Registrar movimiento Kardex
            kardex = MovimientoInventarioModel(
                tenant_id=tenant_id,
                tipomovimiento="SALIDA_VENTA",
                cantidad=it["cantidad"],
                motivo=f"Venta presencial en mostrador #{codigo_venta}",
                referencia=codigo_venta,
                fecha=ahora,
                inventarioid=it["inv"].id,
                usuarioid=usuario_id,
            )
            db.add(kardex)

        # 7. Crear Recibo Fiscal / Comprobante
        recibo = ReciboModel(
            tenant_id=tenant_id,
            estado="Emitido",
            fecha=ahora,
        )
        db.add(recibo)
        db.flush()

        # 8. Registrar Pago
        pago = PagoModel(
            tenant_id=tenant_id,
            monto=total_acumulado,
            estado="Aprobado",
            referencia=f"CAJA-{codigo_venta}",
            fecha=ahora,
            ventaid=nueva_venta.id,
            reciboid=recibo.id,
            metodoid=metodo_pago.id,
        )
        db.add(pago)

        db.commit()
        db.refresh(nueva_venta)

        # 9. Auditoría en Bitácora (CU26)
        cliente_label = f"{cliente.nombre} {cliente.apellido or ''}".strip()
        BitacoraController.registrar_accion(
            db=db,
            usuario_id=usuario_id,
            accion="VENTA_PRESENCIAL_POS",
            modulo="VENTAS",
            detalle=(
                f"Venta POS #{codigo_venta} emitida por Bs {float(total_acumulado):.2f} "
                f"en '{sucursal.nombre}'. Cliente: '{cliente_label}'. Método: {metodo_pago.nombre}. "
                f"Total prendas: {len(items_a_procesar)}."
            ),
            ip_origen=ip_origen,
            tenant_id=tenant_id,
            datos_nuevos={
                "codigo_venta": codigo_venta,
                "total": float(total_acumulado),
                "items": len(items_a_procesar),
                "sucursal_id": sucursal.id,
                "recibo_id": recibo.id,
            },
        )

        cambio = Decimal("0.00")
        if data.monto_recibido and data.monto_recibido > total_acumulado:
            cambio = data.monto_recibido - total_acumulado

        return {
            "id": nueva_venta.id,
            "codigoventa": nueva_venta.codigoventa,
            "tipoventa": nueva_venta.tipoventa,
            "estado": nueva_venta.estado,
            "subtotal": nueva_venta.subtotal,
            "descuento": nueva_venta.descuento,
            "total": nueva_venta.total,
            "fecha": nueva_venta.fecha,
            "sucursalid": sucursal.id,
            "sucursal_nombre": sucursal.nombre,
            "cliente_nombre": cliente_label,
            "metodo_pago_nombre": metodo_pago.nombre,
            "cambio": cambio,
        }

    @classmethod
    def listar_todas_ventas(
        cls,
        db: Session,
        tipoventa: Optional[str] = None,
        sucursal_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        tenant_id: int = 1,
    ) -> List[Dict]:
        """Consulta histórica de ventas con aislamiento multitenant"""
        cls.validar_tenant(db, tenant_id)

        query = db.query(VentaModel).filter(VentaModel.tenant_id == tenant_id)

        if tipoventa:
            query = query.filter(VentaModel.tipoventa.ilike(f"%{tipoventa}%"))

        if sucursal_id:
            query = query.filter(VentaModel.sucursalid == sucursal_id)

        ventas = query.order_by(VentaModel.id.desc()).offset(skip).limit(limit).all()

        resultado = []
        for v in ventas:
            metodo_nombre = None
            if v.pagos and len(v.pagos) > 0:
                metodo_nombre = v.pagos[0].metodo.nombre if v.pagos[0].metodo else None

            resultado.append({
                "id": v.id,
                "codigoventa": v.codigoventa,
                "tipoventa": v.tipoventa,
                "estado": v.estado,
                "subtotal": v.subtotal,
                "descuento": v.descuento,
                "total": v.total,
                "fecha": v.fecha,
                "sucursalid": v.sucursalid,
                "sucursal_nombre": v.sucursal.nombre if v.sucursal else "Sucursal Central",
                "cliente_nombre": f"{v.cliente.nombre} {v.cliente.apellido or ''}".strip() if v.cliente else "Consumidor Final",
                "metodo_pago_nombre": metodo_nombre or "Efectivo",
                "cambio": Decimal("0.00"),
            })

        return resultado

    @classmethod
    def obtener_venta_por_id(
        cls,
        db: Session,
        venta_id: int,
        tenant_id: int = 1,
    ) -> Dict:
        """Recupera el comprobante y detalle de renglones de una venta específica"""
        cls.validar_tenant(db, tenant_id)

        v = (
            db.query(VentaModel)
            .filter(
                VentaModel.id == venta_id,
                VentaModel.tenant_id == tenant_id,
            )
            .first()
        )
        if not v:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Venta #{venta_id} no encontrada en este tenant",
            )

        metodo_nombre = None
        if v.pagos and len(v.pagos) > 0:
            metodo_nombre = v.pagos[0].metodo.nombre if v.pagos[0].metodo else None

        detalles_lista = []
        for d in v.detalles:
            prod_nombre = "Prenda"
            talla_nombre = "-"
            color_nombre = "-"
            if d.variante:
                if d.variante.producto:
                    prod_nombre = d.variante.producto.nombre
                if d.variante.talla:
                    talla_nombre = d.variante.talla.nombre
                if d.variante.color:
                    color_nombre = d.variante.color.nombre

            detalles_lista.append({
                "variante_id": d.varianteid,
                "producto_nombre": prod_nombre,
                "talla": talla_nombre,
                "color": color_nombre,
                "cantidad": d.cantidad,
                "preciounitario": d.preciounitario,
                "descuento": d.descuento,
                "subtotal": d.subtotal,
            })

        return {
            "id": v.id,
            "codigoventa": v.codigoventa,
            "tipoventa": v.tipoventa,
            "estado": v.estado,
            "subtotal": v.subtotal,
            "descuento": v.descuento,
            "total": v.total,
            "fecha": v.fecha,
            "sucursalid": v.sucursalid,
            "sucursal_nombre": v.sucursal.nombre if v.sucursal else "Sucursal Central",
            "cliente_nombre": f"{v.cliente.nombre} {v.cliente.apellido or ''}".strip() if v.cliente else "Consumidor Final",
            "metodo_pago_nombre": metodo_nombre or "Efectivo",
            "cambio": Decimal("0.00"),
            "detalles": detalles_lista,
        }

    @classmethod
    def listar_metodos_pago(cls, db: Session) -> List[MetodoPagoModel]:
        """Retorna las modalidades de cobro físico disponibles"""
        cls.asegurar_metodos_pago(db)
        return (
            db.query(MetodoPagoModel)
            .filter(
                MetodoPagoModel.estado == True,
                ~MetodoPagoModel.nombre.ilike("%Online%"),
                ~MetodoPagoModel.nombre.ilike("%Digital%"),
            )
            .order_by(MetodoPagoModel.id.asc())
            .all()
        )
