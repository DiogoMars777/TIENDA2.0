# ==============================================================================
# CU09 - GESTIONAR CARRITO DE COMPRAS -> CAPA SERVICIO (MVC - SERVICE)
# Arquitectura: Multi-Tenant SaaS con Validación de Stock en Tiempo Real
# Ubicación: backend/app/services/cu9_gestionar_carrito_compras/carrito_service.py
# ==============================================================================

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException, status
from app.core.timezone import get_bolivia_now

from app.models.models import (
    CarritoModel, CarritoItemModel, VarianteProductoModel, ProductoModel,
    SucursalModel, InventarioSucursalModel, UsuarioModel
)
from app.models.saas_tenant.tenant_model import Tenant
from app.schemas.carrito_schema import (
    CarritoResponse, CarritoItemResponse,
    AgregarItemCarritoRequest, ActualizarCantidadItemRequest,
    AsignarSucursalCarritoRequest
)


class CarritoService:
    """
    Servicio de dominio para la gestión integral del Carrito de Compras.
    Implementa aislamiento multi-tenant SaaS, cálculo reactivo de subtotales,
    asociación a sucursal física de retiro/compra y validación de existencias.
    """

    @classmethod
    def _obtener_o_crear_usuario(cls, db: Session, usuario_id: int, tenant_id: int = 1) -> UsuarioModel:
        """Localiza o inicializa el registro del Usuario para el tenant especificado"""
        # 0. Validar existencia del Tenant
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant con ID {tenant_id} no existe en la plataforma SaaS"
            )

        # 1. ¿usuario_id coincide con un UsuarioModel del tenant?
        user = db.query(UsuarioModel).filter(
            UsuarioModel.id == usuario_id,
            UsuarioModel.tenant_id == tenant_id
        ).first()
        if user:
            return user

        # 2. Si no coincide el tenant o id, buscar primer usuario activo del tenant
        primer_usuario = db.query(UsuarioModel).filter(
            UsuarioModel.tenant_id == tenant_id,
            UsuarioModel.activo == True
        ).first()
        if primer_usuario:
            return primer_usuario

        # 3. Crear usuario invitado por defecto para este tenant si no existe ninguno
        from app.core.security import get_password_hash
        nuevo_invitado = UsuarioModel(
            nombre=f"Cliente Tenant {tenant_id}",
            apellido="Invitado",
            email=f"invitado_tenant{tenant_id}@tienda.bo",
            passwordhash=get_password_hash("guest123"),
            telefono="70000000",
            tenant_id=tenant_id,
            rolid=3,
            activo=True
        )
        db.add(nuevo_invitado)
        db.commit()
        db.refresh(nuevo_invitado)
        return nuevo_invitado

    @classmethod
    def _obtener_carrito_activo(cls, db: Session, usuario_id: int, tenant_id: int = 1) -> CarritoModel:
        """Busca el carrito activo del usuario con aislamiento estricto por tenant o crea uno nuevo"""
        user = cls._obtener_o_crear_usuario(db, usuario_id, tenant_id)

        carrito = db.query(CarritoModel).filter(
            CarritoModel.clienteid == user.id,
            CarritoModel.tenant_id == tenant_id,
            CarritoModel.estado == "ACTIVO"
        ).first()

        if not carrito:
            carrito = CarritoModel(
                clienteid=user.id,
                tenant_id=tenant_id,
                estado="ACTIVO",
                fechacreacion=get_bolivia_now(),
                fechaactualizacion=get_bolivia_now()
            )
            db.add(carrito)
            db.commit()
            db.refresh(carrito)

        return carrito

    @classmethod
    def obtener_carrito(cls, db: Session, usuario_id: int, tenant_id: int = 1) -> CarritoResponse:
        """Construye la respuesta completa del carrito con cálculo de stock y subtotales en tiempo real"""
        carrito = cls._obtener_carrito_activo(db, usuario_id, tenant_id)

        items_resp: List[CarritoItemResponse] = []
        total_items = 0
        total_precio = Decimal("0.00")
        tiene_alertas = False

        sucursal_nombre = carrito.sucursal.nombre if carrito.sucursal else None

        for item in carrito.items:
            variante = item.variante
            if not variante:
                continue

            producto = variante.producto
            if not producto:
                continue

            # Calcular stock disponible en la sucursal del carrito (o stock total del tenant)
            if carrito.sucursalid:
                inv = db.query(InventarioSucursalModel).filter(
                    InventarioSucursalModel.varianteid == variante.id,
                    InventarioSucursalModel.sucursalid == carrito.sucursalid,
                    InventarioSucursalModel.tenant_id == tenant_id
                ).first()
                stock_disp = max(0, (inv.cantidad - (inv.stockreservado or 0))) if inv else 0
            else:
                invs = db.query(InventarioSucursalModel).filter(
                    InventarioSucursalModel.varianteid == variante.id,
                    InventarioSucursalModel.tenant_id == tenant_id
                ).all()
                stock_disp = sum(max(0, (i.cantidad - (i.stockreservado or 0))) for i in invs)

            subtotal = Decimal(str(item.cantidad)) * item.preciounitario
            stock_suficiente = item.cantidad <= stock_disp

            if not stock_suficiente:
                tiene_alertas = True

            total_items += item.cantidad
            total_precio += subtotal

            items_resp.append(
                CarritoItemResponse(
                    variante_id=variante.id,
                    producto_id=producto.id,
                    producto_nombre=producto.nombre,
                    imagen_url=variante.imagenurl or producto.imagenprincipal,
                    sku=variante.sku,
                    talla=variante.talla.nombre if variante.talla else None,
                    color=variante.color.nombre if variante.color else None,
                    codigohex=variante.color.codigohex if variante.color else None,
                    precio_unitario=item.preciounitario,
                    cantidad=item.cantidad,
                    subtotal=subtotal,
                    stock_disponible=stock_disp,
                    stock_suficiente=stock_suficiente
                )
            )

        return CarritoResponse(
            id=carrito.id,
            estado=carrito.estado,
            cliente_id=carrito.clienteid,
            sucursal_id=carrito.sucursalid,
            sucursal_nombre=sucursal_nombre,
            items=items_resp,
            total_items=total_items,
            total_precio=total_precio,
            tiene_alertas_stock=tiene_alertas,
            fecha_actualizacion=carrito.fechaactualizacion
        )

    @classmethod
    def agregar_item(
        cls,
        db: Session,
        usuario_id: int,
        datos: AgregarItemCarritoRequest,
        tenant_id: int = 1
    ) -> CarritoResponse:
        """Agrega una prenda o variante al carrito con verificación multi-tenant y validación de existencias"""
        variante = db.query(VarianteProductoModel).join(ProductoModel).filter(
            VarianteProductoModel.id == datos.variante_id,
            VarianteProductoModel.activo == True,
            ProductoModel.tenant_id == tenant_id
        ).first()

        if not variante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variante de prenda con ID {datos.variante_id} no encontrada en este tenant"
            )

        carrito = cls._obtener_carrito_activo(db, usuario_id, tenant_id)

        # Si se especificó sucursal en el request, verificar que pertenezca al tenant y asignarla
        if datos.sucursal_id:
            sucursal = db.query(SucursalModel).filter(
                SucursalModel.id == datos.sucursal_id,
                SucursalModel.tenant_id == tenant_id,
                SucursalModel.activo == True
            ).first()
            if not sucursal:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Sucursal con ID {datos.sucursal_id} no encontrada en este tenant"
                )
            carrito.sucursalid = datos.sucursal_id
        elif not carrito.sucursalid:
            # Buscar una sucursal del tenant que cuente con stock suficiente para esta prenda
            inv_con_stock = db.query(InventarioSucursalModel).filter(
                InventarioSucursalModel.varianteid == datos.variante_id,
                InventarioSucursalModel.tenant_id == tenant_id,
                (InventarioSucursalModel.cantidad - (InventarioSucursalModel.stockreservado or 0)) >= datos.cantidad
            ).first()
            if inv_con_stock:
                carrito.sucursalid = inv_con_stock.sucursalid

        # Validar stock disponible
        if carrito.sucursalid:
            inv = db.query(InventarioSucursalModel).filter(
                InventarioSucursalModel.varianteid == datos.variante_id,
                InventarioSucursalModel.sucursalid == carrito.sucursalid,
                InventarioSucursalModel.tenant_id == tenant_id
            ).first()
            stock_disp = max(0, (inv.cantidad - (inv.stockreservado or 0))) if inv else 0
        else:
            invs = db.query(InventarioSucursalModel).filter(
                InventarioSucursalModel.varianteid == datos.variante_id,
                InventarioSucursalModel.tenant_id == tenant_id
            ).all()
            stock_disp = sum(max(0, (i.cantidad - (i.stockreservado or 0))) for i in invs)

        item = db.query(CarritoItemModel).filter(
            CarritoItemModel.carritoid == carrito.id,
            CarritoItemModel.varianteid == datos.variante_id
        ).first()

        cantidad_final = (item.cantidad + datos.cantidad) if item else datos.cantidad

        if cantidad_final > stock_disp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente en la tienda. Disponibles: {stock_disp} uds."
            )

        if item:
            item.cantidad = cantidad_final
        else:
            nuevo_item = CarritoItemModel(
                carritoid=carrito.id,
                varianteid=datos.variante_id,
                cantidad=datos.cantidad,
                preciounitario=variante.precioventa or variante.producto.preciobase,
                fechaagregado=get_bolivia_now()
            )
            db.add(nuevo_item)

        carrito.fechaactualizacion = get_bolivia_now()
        db.commit()

        return cls.obtener_carrito(db, usuario_id, tenant_id)

    @classmethod
    def actualizar_cantidad(
        cls,
        db: Session,
        usuario_id: int,
        variante_id: int,
        datos: ActualizarCantidadItemRequest,
        tenant_id: int = 1
    ) -> CarritoResponse:
        """Modifica la cantidad solicitada de un ítem en el carrito"""
        carrito = cls._obtener_carrito_activo(db, usuario_id, tenant_id)

        item = db.query(CarritoItemModel).filter(
            CarritoItemModel.carritoid == carrito.id,
            CarritoItemModel.varianteid == variante_id
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El ítem seleccionado no se encuentra en el carrito"
            )

        if datos.cantidad <= 0:
            db.delete(item)
        else:
            # Validar stock disponible
            if carrito.sucursalid:
                inv = db.query(InventarioSucursalModel).filter(
                    InventarioSucursalModel.varianteid == variante_id,
                    InventarioSucursalModel.sucursalid == carrito.sucursalid,
                    InventarioSucursalModel.tenant_id == tenant_id
                ).first()
                stock_disp = max(0, (inv.cantidad - (inv.stockreservado or 0))) if inv else 0
            else:
                invs = db.query(InventarioSucursalModel).filter(
                    InventarioSucursalModel.varianteid == variante_id,
                    InventarioSucursalModel.tenant_id == tenant_id
                ).all()
                stock_disp = sum(max(0, (i.cantidad - (i.stockreservado or 0))) for i in invs)

            if datos.cantidad > stock_disp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No puedes agregar {datos.cantidad} unidades. Stock disponible: {stock_disp} uds."
                )

            item.cantidad = datos.cantidad

        carrito.fechaactualizacion = get_bolivia_now()
        db.commit()

        return cls.obtener_carrito(db, usuario_id, tenant_id)

    @classmethod
    def eliminar_item(
        cls,
        db: Session,
        usuario_id: int,
        variante_id: int,
        tenant_id: int = 1
    ) -> CarritoResponse:
        """Quita una prenda o variante del carrito"""
        carrito = cls._obtener_carrito_activo(db, usuario_id, tenant_id)

        item = db.query(CarritoItemModel).filter(
            CarritoItemModel.carritoid == carrito.id,
            CarritoItemModel.varianteid == variante_id
        ).first()

        if item:
            db.delete(item)
            carrito.fechaactualizacion = get_bolivia_now()
            db.commit()

        return cls.obtener_carrito(db, usuario_id, tenant_id)

    @classmethod
    def asignar_sucursal(
        cls,
        db: Session,
        usuario_id: int,
        datos: AsignarSucursalCarritoRequest,
        tenant_id: int = 1
    ) -> CarritoResponse:
        """Asigna o cambia la tienda física donde se retirará o comprará el carrito"""
        sucursal = db.query(SucursalModel).filter(
            SucursalModel.id == datos.sucursal_id,
            SucursalModel.tenant_id == tenant_id,
            SucursalModel.activo == True
        ).first()

        if not sucursal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sucursal con ID {datos.sucursal_id} no encontrada en este tenant"
            )

        carrito = cls._obtener_carrito_activo(db, usuario_id, tenant_id)
        carrito.sucursalid = datos.sucursal_id
        carrito.fechaactualizacion = get_bolivia_now()
        db.commit()

        return cls.obtener_carrito(db, usuario_id, tenant_id)

    @classmethod
    def vaciar_carrito(
        cls,
        db: Session,
        usuario_id: int,
        tenant_id: int = 1
    ) -> CarritoResponse:
        """Elimina todos los productos del carrito activo"""
        carrito = cls._obtener_carrito_activo(db, usuario_id, tenant_id)

        db.query(CarritoItemModel).filter(
            CarritoItemModel.carritoid == carrito.id
        ).delete()

        carrito.fechaactualizacion = get_bolivia_now()
        db.commit()

        return cls.obtener_carrito(db, usuario_id, tenant_id)
