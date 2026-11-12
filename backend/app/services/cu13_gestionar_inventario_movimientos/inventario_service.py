# ==============================================================================
# CU13 - GESTIONAR INVENTARIO Y MOVIMIENTOS -> CAPA SERVICIO (MVC - SERVICE)
# Arquitectura: Multi-Tenant SaaS, Control de Existencias Físicas y Reservadas,
# Alertas de Stock Mínimo, Traslados Inter-Sucursales y Auditoría Bitácora (CU26).
# Ubicación: backend/app/services/cu13_gestionar_inventario_movimientos/inventario_service.py
# ==============================================================================

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
from app.core.timezone import get_bolivia_now

from app.models.models import (
    UsuarioModel,
    InventarioModel,
    MovimientoInventarioModel,
    SucursalModel,
    ProductoModel,
    ColorModel,
    TallaModel,
    VarianteProductoModel,
)
from app.models.saas_tenant.tenant_model import Tenant
from app.schemas.inventario_schema import (
    MovimientoInventarioCreate,
    StockMinimoUpdate,
    TrasladoStockRequest,
)
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController


class InventarioService:
    """
    Servicio de Dominio para la Gestión de Inventarios Físicos, Reservados y Kardex.
    Implementa aislamiento multitenant estricto (tenant_id), alertas de reabastecimiento,
    traslados atómicos entre sucursales de la misma empresa y bitácora de trazabilidad.
    """

    @classmethod
    def validar_tenant(cls, db: Session, tenant_id: int) -> Tenant:
        """Verifica que el tenant exista y esté activo en la plataforma SaaS"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant con ID {tenant_id} no existe en la plataforma SaaS",
            )
        return tenant

    @classmethod
    def asegurar_variantes_e_inventario(cls, db: Session, tenant_id: int = 1) -> None:
        """
        Garantiza que todos los productos registrados del tenant dispongan de
        al menos una variante y fila en la tabla inventario para cada sucursal activa.
        """
        sucursales = (
            db.query(SucursalModel)
            .filter(
                SucursalModel.activo == True,
                SucursalModel.tenant_id == tenant_id,
            )
            .all()
        )
        if not sucursales:
            return

        productos = (
            db.query(ProductoModel)
            .filter(
                ProductoModel.activo == True,
                ProductoModel.tenant_id == tenant_id,
            )
            .all()
        )

        color_default = db.query(ColorModel).first()
        if not color_default:
            color_default = ColorModel(nombre="Estándar", codigohex="#111827", activo=True)
            db.add(color_default)
            db.flush()

        talla_default = db.query(TallaModel).first()
        if not talla_default:
            talla_default = TallaModel(nombre="Única (M)", grupoedad="Adultos", orden=1, activo=True)
            db.add(talla_default)
            db.flush()

        hubo_cambios = False
        for p in productos:
            variante = (
                db.query(VarianteProductoModel)
                .filter(
                    VarianteProductoModel.productoid == p.id,
                    VarianteProductoModel.activo == True,
                )
                .first()
            )

            if not variante:
                variante = VarianteProductoModel(
                    productoid=p.id,
                    colorid=color_default.id,
                    tallaid=talla_default.id,
                    sku=f"POL-{p.id}-{color_default.id}-{talla_default.id}",
                    precioventa=p.preciobase,
                    activo=True,
                )
                db.add(variante)
                db.flush()
                hubo_cambios = True

            for suc in sucursales:
                inv = (
                    db.query(InventarioModel)
                    .filter(
                        InventarioModel.sucursalid == suc.id,
                        InventarioModel.varianteid == variante.id,
                        InventarioModel.tenant_id == tenant_id,
                    )
                    .first()
                )

                if not inv:
                    inv = InventarioModel(
                        tenant_id=tenant_id,
                        sucursalid=suc.id,
                        varianteid=variante.id,
                        stockfisico=20,  # Stock inicial de cortesía para pruebas y tienda
                        stockreservado=0,
                        stockminimo=5,
                        fechaactualizacion=get_bolivia_now(),
                    )
                    db.add(inv)
                    hubo_cambios = True

        if hubo_cambios:
            db.commit()

    @classmethod
    def _inferir_color_y_talla(cls, producto: ProductoModel, variante: VarianteProductoModel):
        color = variante.color
        talla = variante.talla

        color_nombre = color.nombre if color else None
        color_hex = color.codigohex if color else None
        talla_nombre = talla.nombre if talla else None

        if not color_nombre or color_nombre in ("Único", "Estándar", "--"):
            p_lower = (producto.nombre or "").lower()
            if "beige" in p_lower:
                color_nombre, color_hex = "Beige", "#D4B996"
            elif "blanc" in p_lower:
                color_nombre, color_hex = "Blanco", "#FFFFFF"
            elif "roj" in p_lower:
                color_nombre, color_hex = "Rojo", "#DC2626"
            elif "negr" in p_lower:
                color_nombre, color_hex = "Negro", "#1E293B"
            elif "verd" in p_lower:
                color_nombre, color_hex = "Verde", "#059669"
            elif "azul" in p_lower:
                color_nombre, color_hex = "Azul", "#2563EB"
            elif "amarill" in p_lower:
                color_nombre, color_hex = "Amarillo", "#EAB308"
            elif "gris" in p_lower:
                color_nombre, color_hex = "Gris", "#64748B"
            elif "terracota" in p_lower:
                color_nombre, color_hex = "Terracota", "#B45309"
            else:
                color_nombre = "Rojo" if "roja" in p_lower else "Negro"
                color_hex = "#DC2626" if "roja" in p_lower else "#1E293B"

        if not talla_nombre or talla_nombre == "--":
            talla_nombre = "M"

        return color_nombre, color_hex, talla_nombre

    @classmethod
    def listar_inventario(
        cls,
        db: Session,
        sucursal_id: Optional[int] = None,
        search: Optional[str] = None,
        solo_bajo_stock: Optional[bool] = False,
        skip: int = 0,
        limit: int = 100,
        tenant_id: int = 1,
    ) -> List[Dict]:
        """
        Consulta existencias físicas, existencias reservadas, disponibilidad
        y alertas de stock de seguridad para un tenant específico.
        """
        cls.validar_tenant(db, tenant_id)
        cls.asegurar_variantes_e_inventario(db, tenant_id=tenant_id)

        query = (
            db.query(InventarioModel)
            .join(SucursalModel, InventarioModel.sucursalid == SucursalModel.id)
            .join(VarianteProductoModel, InventarioModel.varianteid == VarianteProductoModel.id)
            .join(ProductoModel, VarianteProductoModel.productoid == ProductoModel.id)
            .filter(
                InventarioModel.tenant_id == tenant_id,
                SucursalModel.tenant_id == tenant_id,
                ProductoModel.tenant_id == tenant_id,
            )
        )

        if sucursal_id:
            query = query.filter(InventarioModel.sucursalid == sucursal_id)

        if search:
            patron = f"%{search}%"
            query = query.filter(
                or_(
                    ProductoModel.nombre.ilike(patron),
                    ProductoModel.marca.ilike(patron),
                    VarianteProductoModel.sku.ilike(patron),
                    SucursalModel.nombre.ilike(patron),
                )
            )

        if solo_bajo_stock:
            query = query.filter(InventarioModel.stockfisico <= InventarioModel.stockminimo)

        items = query.order_by(InventarioModel.id.desc()).offset(skip).limit(limit).all()

        resultado = []
        for inv in items:
            p = inv.variante.producto
            color_nombre, color_hex, talla_nombre = cls._inferir_color_y_talla(p, inv.variante)

            stock_reservado = inv.stockreservado or 0
            stock_fisico = inv.stockfisico or 0
            stock_disponible = max(0, stock_fisico - stock_reservado)

            estado_stock = "NORMAL"
            if stock_fisico <= 0:
                estado_stock = "AGOTADO"
            elif stock_fisico <= inv.stockminimo:
                estado_stock = "BAJO_STOCK"

            resultado.append({
                "id": inv.id,
                "sucursal_id": inv.sucursalid,
                "sucursal_nombre": inv.sucursal.nombre if inv.sucursal else "Sucursal Central",
                "variante_id": inv.varianteid,
                "producto_id": p.id,
                "producto_nombre": p.nombre,
                "producto_marca": p.marca,
                "producto_precio": Decimal(str(inv.variante.precioventa or p.preciobase)),
                "color_nombre": color_nombre,
                "color_hex": color_hex,
                "talla_nombre": talla_nombre,
                "color": color_nombre,
                "talla": talla_nombre,
                "sku": inv.variante.sku or f"SKU-{p.id}",
                "stockfisico": stock_fisico,
                "stockreservado": stock_reservado,
                "stockdisponible": stock_disponible,
                "stockminimo": inv.stockminimo,
                "estado_stock": estado_stock,
                "imagen_url": p.imagenprincipal or getattr(p, "imagen_url", None),
                "fechaactualizacion": inv.fechaactualizacion,
            })

        return resultado

    @classmethod
    def obtener_detalle_inventario(
        cls,
        db: Session,
        inventario_id: int,
        tenant_id: int = 1,
    ) -> Dict:
        """Obtiene un ítem específico de inventario validando pertenencia al tenant"""
        inv = (
            db.query(InventarioModel)
            .filter(
                InventarioModel.id == inventario_id,
                InventarioModel.tenant_id == tenant_id,
            )
            .first()
        )
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registro de inventario #{inventario_id} no encontrado en este tenant",
            )

        p = inv.variante.producto
        color_nombre, color_hex, talla_nombre = cls._inferir_color_y_talla(p, inv.variante)
        stock_reservado = inv.stockreservado or 0
        stock_fisico = inv.stockfisico or 0
        stock_disponible = max(0, stock_fisico - stock_reservado)

        estado_stock = "NORMAL"
        if stock_fisico <= 0:
            estado_stock = "AGOTADO"
        elif stock_fisico <= inv.stockminimo:
            estado_stock = "BAJO_STOCK"

        return {
            "id": inv.id,
            "sucursal_id": inv.sucursalid,
            "sucursal_nombre": inv.sucursal.nombre if inv.sucursal else "Sucursal Central",
            "variante_id": inv.varianteid,
            "producto_id": p.id,
            "producto_nombre": p.nombre,
            "producto_marca": p.marca,
            "producto_precio": Decimal(str(inv.variante.precioventa or p.preciobase)),
            "color_nombre": color_nombre,
            "color_hex": color_hex,
            "talla_nombre": talla_nombre,
            "color": color_nombre,
            "talla": talla_nombre,
            "sku": inv.variante.sku or f"SKU-{p.id}",
            "stockfisico": stock_fisico,
            "stockreservado": stock_reservado,
            "stockdisponible": stock_disponible,
            "stockminimo": inv.stockminimo,
            "estado_stock": estado_stock,
            "imagen_url": p.imagenprincipal or getattr(p, "imagen_url", None),
            "fechaactualizacion": inv.fechaactualizacion,
        }

    @classmethod
    def registrar_movimiento(
        cls,
        db: Session,
        inventario_id: int,
        data: MovimientoInventarioCreate,
        usuario_id: int,
        tenant_id: int = 1,
        ip_origen: str = "127.0.0.1",
    ) -> Dict:
        """
        Registra una Entrada, Salida o Ajuste manual en el inventario con control de
        reservas y registro automático en Bitácora (CU26).
        """
        inv = (
            db.query(InventarioModel)
            .filter(
                InventarioModel.id == inventario_id,
                InventarioModel.tenant_id == tenant_id,
            )
            .first()
        )
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registro de inventario #{inventario_id} no encontrado en este tenant",
            )

        tipo = data.tipo_normalizado
        cant = data.cantidad
        stock_reservado = inv.stockreservado or 0
        stock_anterior = inv.stockfisico

        if tipo == "Entrada":
            inv.stockfisico += cant
        elif tipo == "Salida":
            disponible = inv.stockfisico - stock_reservado
            if cant > disponible:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Stock disponible insuficiente. Stock físico: {inv.stockfisico}, "
                        f"Reservado: {stock_reservado}, Disponible para retiro: {disponible}, Solicitado: {cant}"
                    ),
                )
            inv.stockfisico -= cant
        elif tipo == "Ajuste":
            if cant < stock_reservado:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"El nuevo stock físico ({cant}) no puede ser menor a las unidades comprometidas "
                        f"en reservas pendientes de retiro ({stock_reservado})"
                    ),
                )
            inv.stockfisico = cant
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de movimiento inválido. Use 'Entrada', 'Salida' o 'Ajuste'.",
            )

        inv.fechaactualizacion = get_bolivia_now()

        movimiento = MovimientoInventarioModel(
            tenant_id=tenant_id,
            tipomovimiento=tipo,
            cantidad=cant,
            motivo=data.motivo or f"Operación manual de {tipo}",
            referencia=data.referencia,
            fecha=get_bolivia_now(),
            inventarioid=inv.id,
            usuarioid=usuario_id,
        )
        db.add(movimiento)
        db.commit()
        db.refresh(inv)

        # Auditoría Bitácora CU26
        BitacoraController.registrar_accion(
            db=db,
            usuario_id=usuario_id,
            accion=f"MOVIMIENTO_INVENTARIO_{tipo.upper()}",
            detalle=(
                f"Movimiento {tipo} de {cant} un. en inventario #{inv.id} "
                f"(Sucursal #{inv.sucursalid}, Variante #{inv.varianteid}). "
                f"Stock: {stock_anterior} -> {inv.stockfisico} un."
            ),
            ip_origen=ip_origen,
            tenant_id=tenant_id,
        )

        return {
            "mensaje": f"Movimiento de {tipo} registrado exitosamente",
            "stock_anterior": stock_anterior,
            "stock_actual": inv.stockfisico,
            "stock_actualizado": inv.stockfisico,
            "stockreservado": inv.stockreservado,
            "stockdisponible": max(0, inv.stockfisico - (inv.stockreservado or 0)),
            "inventario_id": inv.id,
        }

    @classmethod
    def trasladar_stock(
        cls,
        db: Session,
        inventario_origen_id: int,
        data: TrasladoStockRequest,
        usuario_id: int,
        tenant_id: int = 1,
        ip_origen: str = "127.0.0.1",
    ) -> Dict:
        """
        Traslada existencias físicas de una prenda entre dos sucursales de la MISMA empresa.
        Verifica disponibilidad, descuenta origen, incrementa destino y genera movimientos cruzados.
        """
        inv_origen = (
            db.query(InventarioModel)
            .filter(
                InventarioModel.id == inventario_origen_id,
                InventarioModel.tenant_id == tenant_id,
            )
            .first()
        )
        if not inv_origen:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventario de origen #{inventario_origen_id} no encontrado en este tenant",
            )

        if inv_origen.sucursalid == data.sucursal_destino_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La sucursal de destino no puede ser la misma sucursal de origen.",
            )

        suc_destino = (
            db.query(SucursalModel)
            .filter(
                SucursalModel.id == data.sucursal_destino_id,
                SucursalModel.tenant_id == tenant_id,
                SucursalModel.activo == True,
            )
            .first()
        )
        if not suc_destino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sucursal de destino #{data.sucursal_destino_id} no encontrada o inactiva en este tenant",
            )

        suc_origen = inv_origen.sucursal
        suc_origen_nombre = suc_origen.nombre if suc_origen else f"Sucursal #{inv_origen.sucursalid}"

        # Validar stock disponible en origen (no reservado)
        stock_reservado = inv_origen.stockreservado or 0
        stock_disponible = max(0, inv_origen.stockfisico - stock_reservado)
        if data.cantidad > stock_disponible:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Stock disponible insuficiente en {suc_origen_nombre}. "
                    f"Físico: {inv_origen.stockfisico}, Reservado: {stock_reservado}, "
                    f"Disponible para transferir: {stock_disponible}, Solicitado: {data.cantidad}"
                ),
            )

        # 1. Descontar del origen
        inv_origen.stockfisico -= data.cantidad
        inv_origen.fechaactualizacion = get_bolivia_now()

        # 2. Localizar o crear registro en destino
        inv_destino = (
            db.query(InventarioModel)
            .filter(
                InventarioModel.sucursalid == data.sucursal_destino_id,
                InventarioModel.varianteid == inv_origen.varianteid,
                InventarioModel.tenant_id == tenant_id,
            )
            .first()
        )

        if not inv_destino:
            inv_destino = InventarioModel(
                tenant_id=tenant_id,
                sucursalid=data.sucursal_destino_id,
                varianteid=inv_origen.varianteid,
                stockfisico=data.cantidad,
                stockreservado=0,
                stockminimo=inv_origen.stockminimo,
                fechaactualizacion=get_bolivia_now(),
            )
            db.add(inv_destino)
            db.flush()
        else:
            inv_destino.stockfisico += data.cantidad
            inv_destino.fechaactualizacion = get_bolivia_now()

        referencia = data.referencia or f"TRF-{inv_origen.sucursalid}->{data.sucursal_destino_id}-{get_bolivia_now().strftime('%Y%m%d%H%M')}"
        motivo_texto = data.motivo or "Reabastecimiento y balance de inventario entre sucursales"

        # 3. Kardex de salida en origen
        mov_salida = MovimientoInventarioModel(
            tenant_id=tenant_id,
            tipomovimiento="TRASLADO_SALIDA",
            cantidad=data.cantidad,
            motivo=f"Hacia {suc_destino.nombre}: {motivo_texto}",
            referencia=referencia,
            fecha=get_bolivia_now(),
            inventarioid=inv_origen.id,
            usuarioid=usuario_id,
        )
        db.add(mov_salida)

        # 4. Kardex de entrada en destino
        mov_entrada = MovimientoInventarioModel(
            tenant_id=tenant_id,
            tipomovimiento="TRASLADO_ENTRADA",
            cantidad=data.cantidad,
            motivo=f"Desde {suc_origen_nombre}: {motivo_texto}",
            referencia=referencia,
            fecha=get_bolivia_now(),
            inventarioid=inv_destino.id,
            usuarioid=usuario_id,
        )
        db.add(mov_entrada)

        db.commit()
        db.refresh(inv_origen)
        db.refresh(inv_destino)

        # 5. Auditoría Bitácora CU26
        BitacoraController.registrar_accion(
            db=db,
            usuario_id=usuario_id,
            accion="TRASLADO_INVENTARIO",
            detalle=(
                f"Traslado de {data.cantidad} un. de variante #{inv_origen.varianteid} "
                f"desde '{suc_origen_nombre}' hacia '{suc_destino.nombre}'. "
                f"Stock origen restante: {inv_origen.stockfisico}, stock destino actual: {inv_destino.stockfisico}. Ref: {referencia}"
            ),
            ip_origen=ip_origen,
            tenant_id=tenant_id,
        )

        return {
            "mensaje": f"Traslado de {data.cantidad} unidades completado exitosamente a {suc_destino.nombre}",
            "inventario_origen_id": inv_origen.id,
            "inventario_destino_id": inv_destino.id,
            "sucursal_origen_id": inv_origen.sucursalid,
            "sucursal_destino_id": suc_destino.id,
            "sucursal_origen_nombre": suc_origen_nombre,
            "sucursal_destino_nombre": suc_destino.nombre,
            "cantidad_trasladada": data.cantidad,
            "stock_origen_restante": inv_origen.stockfisico,
            "stock_destino_actual": inv_destino.stockfisico,
        }

    @classmethod
    def actualizar_stock_minimo(
        cls,
        db: Session,
        inventario_id: int,
        data: StockMinimoUpdate,
        usuario_id: int,
        tenant_id: int = 1,
        ip_origen: str = "127.0.0.1",
    ) -> Dict:
        """Actualiza el umbral de seguridad para alertas de stock con auditoría"""
        inv = (
            db.query(InventarioModel)
            .filter(
                InventarioModel.id == inventario_id,
                InventarioModel.tenant_id == tenant_id,
            )
            .first()
        )
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registro de inventario #{inventario_id} no encontrado en este tenant",
            )

        anterior = inv.stockminimo
        inv.stockminimo = data.stockminimo
        inv.fechaactualizacion = get_bolivia_now()
        db.commit()
        db.refresh(inv)

        # Auditoría Bitácora CU26
        BitacoraController.registrar_accion(
            db=db,
            usuario_id=usuario_id,
            accion="MODIFICAR_STOCK_MINIMO",
            detalle=(
                f"Stock mínimo modificado en inventario #{inv.id} "
                f"(Sucursal #{inv.sucursalid}): {anterior} -> {inv.stockminimo} un."
            ),
            ip_origen=ip_origen,
            tenant_id=tenant_id,
        )

        return {
            "mensaje": "Nivel de stock mínimo actualizado exitosamente",
            "inventario_id": inv.id,
            "stockminimo": inv.stockminimo,
        }

    @classmethod
    def obtener_kardex(
        cls,
        db: Session,
        inventario_id: int,
        limit: int = 50,
        tenant_id: int = 1,
    ) -> List[Dict]:
        """Consulta el historial cronológico de movimientos kardex para un inventario"""
        inv = (
            db.query(InventarioModel)
            .filter(
                InventarioModel.id == inventario_id,
                InventarioModel.tenant_id == tenant_id,
            )
            .first()
        )
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registro de inventario #{inventario_id} no encontrado en este tenant",
            )

        movimientos = (
            db.query(MovimientoInventarioModel)
            .filter(
                MovimientoInventarioModel.inventarioid == inventario_id,
                MovimientoInventarioModel.tenant_id == tenant_id,
            )
            .order_by(MovimientoInventarioModel.id.desc())
            .limit(limit)
            .all()
        )

        resultado = []
        for m in movimientos:
            usuario_str = "Sistema"
            if m.usuario:
                usuario_str = f"{m.usuario.nombre} {m.usuario.apellido or ''}".strip()

            resultado.append({
                "id": m.id,
                "tipomovimiento": m.tipomovimiento,
                "cantidad": m.cantidad,
                "motivo": m.motivo,
                "referencia": m.referencia,
                "fecha": m.fecha,
                "usuario_nombre": usuario_str,
            })

        return resultado
