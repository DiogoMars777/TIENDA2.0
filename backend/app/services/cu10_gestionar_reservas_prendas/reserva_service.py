# ==============================================================================
# CU10 - GESTIONAR RESERVAS DE PRENDAS -> CAPA SERVICIO (MVC - SERVICE)
# Arquitectura: Multi-Tenant SaaS con Vencimiento 48h, Bloqueo de Stock y Auditoría
# Ubicación: backend/app/services/cu10_gestionar_reservas_prendas/reserva_service.py
# ==============================================================================

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string
from fastapi import HTTPException, status

from app.models.models import (
    ReservaModel, ReservaDetalleModel, CarritoModel, CarritoItemModel,
    InventarioSucursalModel, SucursalModel, VarianteProductoModel,
    ProductoModel, UsuarioModel
)
from app.models.saas_tenant.tenant_model import Tenant
from app.schemas.reserva_schema import (
    ReservaCreate, ReservaResponse, ReservaDetalleResponse, ReservaSucursalResponse
)
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
from app.core.timezone import get_bolivia_now, to_bolivia_time


def generar_codigo_reserva(db: Session, tenant_id: int = 1) -> str:
    """Genera un código único alfanumérico para la reserva dentro del tenant (ej: RES-7X9K2M)."""
    while True:
        sufijo = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        codigo = f"RES-{sufijo}"
        existente = db.query(ReservaModel).filter(
            ReservaModel.codigoreserva == codigo,
            ReservaModel.tenant_id == tenant_id
        ).first()
        if not existente:
            return codigo


def formatear_reserva(reserva: ReservaModel) -> ReservaResponse:
    """Convierte un modelo ReservaModel a un schema Pydantic con cálculo de vencimiento y 48 horas."""
    sucursal_resp = None
    if reserva.sucursal:
        sucursal_resp = ReservaSucursalResponse(
            id=reserva.sucursal.id,
            nombre=reserva.sucursal.nombre,
            ciudad=reserva.sucursal.ciudad,
            direccion=reserva.sucursal.direccion,
            telefono=reserva.sucursal.telefono,
        )

    # Datos del Cliente/Usuario
    cliente_nombre = None
    cliente_email = None
    cliente_tel = None
    if reserva.cliente:
        cliente_nombre = f"{reserva.cliente.nombre} {reserva.cliente.apellido or ''}".strip()
        cliente_email = reserva.cliente.email
        cliente_tel = reserva.cliente.telefono

    detalles_resp: List[ReservaDetalleResponse] = []
    total_items = 0
    total_estimado = 0.0

    for d in reserva.detalles:
        variante = d.variante
        prod = variante.producto if variante else None

        prod_nombre = prod.nombre if prod else "Prenda"
        talla_nombre = variante.talla.nombre if variante and variante.talla else None
        color_nombre = variante.color.nombre if variante and variante.color else None
        color_hex = variante.color.codigohex if variante and variante.color else None
        imagen_url = (variante.imagenurl if variante and variante.imagenurl else None) or (prod.imagenprincipal if prod else None)

        precio = float(variante.precioventa if variante and variante.precioventa else (prod.preciobase if prod else 0.0))
        subtotal = round(precio * d.cantidad, 2)

        detalles_resp.append(
            ReservaDetalleResponse(
                variante_id=d.varianteid,
                producto_nombre=prod_nombre,
                talla=talla_nombre,
                color=color_nombre,
                codigo_hex=color_hex,
                imagen_url=imagen_url,
                precio_unitario=precio,
                cantidad=d.cantidad,
                subtotal=subtotal,
            )
        )
        total_items += d.cantidad
        total_estimado += subtotal

    # Cálculo dinámico de horas restantes para vencimiento (48 horas oficiales en hora Bolivia)
    fecha_expiracion = reserva.fechareserva + timedelta(hours=48)
    tiempo_restante = fecha_expiracion - get_bolivia_now()
    horas_restantes = max(0, int(tiempo_restante.total_seconds() // 3600)) if reserva.estado == "PENDIENTE" else 0

    return ReservaResponse(
        id=reserva.id,
        codigo_reserva=reserva.codigoreserva,
        fecha_reserva=reserva.fechareserva,
        fecha_expiracion=fecha_expiracion,
        horas_restantes=horas_restantes,
        estado=reserva.estado,
        observaciones=reserva.observaciones,
        cliente_id=reserva.clienteid,
        cliente_nombre=cliente_nombre,
        cliente_email=cliente_email,
        cliente_telefono=cliente_tel,
        sucursal=sucursal_resp,
        detalles=detalles_resp,
        total_items=total_items,
        total_estimado=round(total_estimado, 2),
    )


class ReservaService:
    """
    Servicio de dominio para la gestión del ciclo de vida de Reservas de prendas.
    Implementa vencimiento estricto de 48 horas, bloqueo temporal de stock (stockreservado),
    validación de cuota máxima de reservas por cliente y auditoría de eventos.
    """

    MAX_RESERVAS_ACTIVAS_POR_CLIENTE = 25

    @classmethod
    def _obtener_usuario_reserva(cls, db: Session, usuario_id: int, tenant_id: int = 1) -> UsuarioModel:
        """Valida que el tenant exista y localiza el usuario autenticado o cliente demo"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant con ID {tenant_id} no existe en la plataforma SaaS"
            )

        user = db.query(UsuarioModel).filter(
            UsuarioModel.id == usuario_id,
            UsuarioModel.tenant_id == tenant_id
        ).first()
        if not user:
            user = db.query(UsuarioModel).filter(
                UsuarioModel.id == usuario_id
            ).first()

        if user:
            return user

        primer_usuario = db.query(UsuarioModel).filter(
            UsuarioModel.tenant_id == tenant_id,
            UsuarioModel.activo == True
        ).first()

        if primer_usuario:
            return primer_usuario

        from app.core.security import get_password_hash
        nuevo_user = UsuarioModel(
            nombre=f"Cliente Tenant {tenant_id}",
            apellido="Invitado",
            email=f"cliente_t{tenant_id}@tienda.bo",
            passwordhash=get_password_hash("guest123"),
            telefono="70000000",
            tenant_id=tenant_id,
            rolid=3,
            activo=True
        )
        db.add(nuevo_user)
        db.commit()
        db.refresh(nuevo_user)
        return nuevo_user

    @classmethod
    def verificar_y_expirar_reservas(cls, db: Session, tenant_id: int = 1) -> int:
        """
        CU10: Verifica automáticamente las reservas en estado PENDIENTE que superaron las 48 horas.
        Cambia el estado a 'EXPIRADA' y libera el stockreservado en inventario.
        """
        limite_tiempo = get_bolivia_now() - timedelta(hours=48)
        reservas_vencidas = db.query(ReservaModel).filter(
            ReservaModel.tenant_id == tenant_id,
            ReservaModel.estado == "PENDIENTE",
            ReservaModel.fechareserva < limite_tiempo
        ).all()

        expiradas_count = 0
        for r in reservas_vencidas:
            r.estado = "EXPIRADA"
            nota_exp = "[EXPIRADA AUTOMÁTICAMENTE: Superó el plazo límite de 48 horas]"
            r.observaciones = f"{r.observaciones or ''} {nota_exp}".strip()

            # Liberar stock reservado en la sucursal física
            for d in r.detalles:
                inv = db.query(InventarioSucursalModel).filter(
                    InventarioSucursalModel.varianteid == d.varianteid,
                    InventarioSucursalModel.sucursalid == r.sucursalid,
                    InventarioSucursalModel.tenant_id == tenant_id
                ).first()
                if inv:
                    inv.stockreservado = max(0, (inv.stockreservado or 0) - d.cantidad)

            expiradas_count += 1

        if expiradas_count > 0:
            db.commit()

        return expiradas_count

    @classmethod
    def crear_reserva(
        cls,
        db: Session,
        usuario_id: int,
        datos: ReservaCreate,
        tenant_id: int = 1
    ) -> ReservaResponse:
        """
        CU10: Genera una reserva física con vigencia de 48 horas y bloqueo temporal de stock.
        Valida que el cliente no exceda su límite de reservas activas simultáneas según el plan.
        """
        # 1. Ejecutar barrido de reservas expiradas para liberar cupos y stock
        cls.verificar_y_expirar_reservas(db, tenant_id)

        user = cls._obtener_usuario_reserva(db, usuario_id, tenant_id)

        # 2. Validar límite de reservas simultáneas pendientes según cuota del plan
        reservas_activas = db.query(ReservaModel).filter(
            ReservaModel.clienteid == user.id,
            ReservaModel.tenant_id == tenant_id,
            ReservaModel.estado == "PENDIENTE"
        ).count()

        if reservas_activas >= cls.MAX_RESERVAS_ACTIVAS_POR_CLIENTE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Ha alcanzado el límite máximo de reservas simultáneas activas permitidas "
                    f"({cls.MAX_RESERVAS_ACTIVAS_POR_CLIENTE} reservas). Por favor retire o cancele "
                    f"sus reservas pendientes antes de apartar nuevas prendas."
                )
            )

        # 3. Determinar la sucursal física de retiro en el tenant
        sucursal_id = datos.sucursal_id
        carrito = None

        if not sucursal_id:
            carrito = db.query(CarritoModel).filter(
                CarritoModel.clienteid == user.id,
                CarritoModel.tenant_id == tenant_id,
                CarritoModel.estado == "ACTIVO"
            ).first()
            if carrito and carrito.sucursalid:
                sucursal_id = carrito.sucursalid

        if not sucursal_id:
            primera_suc = db.query(SucursalModel).filter(
                SucursalModel.tenant_id == tenant_id,
                SucursalModel.activo == True
            ).first()
            if primera_suc:
                sucursal_id = primera_suc.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debe seleccionar la tienda física donde retirará sus prendas reservadas."
                )

        sucursal = db.query(SucursalModel).filter(
            SucursalModel.id == sucursal_id,
            SucursalModel.tenant_id == tenant_id,
            SucursalModel.activo == True
        ).first()

        if not sucursal:
            sucursal = db.query(SucursalModel).filter(
                SucursalModel.tenant_id == tenant_id,
                SucursalModel.activo == True
            ).first()
            if sucursal:
                sucursal_id = sucursal.id

        if not sucursal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La sucursal física ID {sucursal_id} no está activa o no pertenece a este tenant."
            )

        # 4. Recolectar prendas y validar existencias físicas antes de apartar
        es_reserva_offline = (
            bool(getattr(datos, "es_offline", False)) or
            bool(getattr(datos, "codigo_reserva", None) and str(datos.codigo_reserva).startswith("RES-OFF-")) or
            bool(datos.observaciones and "OFFLINE" in datos.observaciones.upper())
        )

        inventarios_afectados: List[Tuple[InventarioSucursalModel, int]] = []
        nombres_prendas: List[str] = []
        sin_stock_item = None

        if datos.items and len(datos.items) > 0:
            for it in datos.items:
                variante = None
                if it.variante_id:
                    variante = db.query(VarianteProductoModel).join(ProductoModel).filter(
                        VarianteProductoModel.id == it.variante_id,
                        ProductoModel.tenant_id == tenant_id
                    ).first()
                elif it.producto_id:
                    variante = db.query(VarianteProductoModel).join(ProductoModel).filter(
                        VarianteProductoModel.productoid == it.producto_id,
                        ProductoModel.tenant_id == tenant_id
                    ).first()

                if not variante:
                    continue

                inv = db.query(InventarioSucursalModel).filter(
                    InventarioSucursalModel.varianteid == variante.id,
                    InventarioSucursalModel.sucursalid == sucursal_id,
                    InventarioSucursalModel.tenant_id == tenant_id
                ).first()

                stock_total = inv.cantidad if (inv and inv.cantidad is not None) else 0
                stock_res = inv.stockreservado if (inv and inv.stockreservado is not None) else 0
                disp = max(0, stock_total - stock_res)
                prod_nombre = variante.producto.nombre if variante.producto else "Prenda"

                if it.cantidad > disp or disp <= 0:
                    sin_stock_item = (prod_nombre, disp, it.cantidad, variante)
                    break

                nombres_prendas.append(prod_nombre)
                inventarios_afectados.append((inv, it.cantidad))
        else:
            if not carrito:
                carrito = db.query(CarritoModel).filter(
                    CarritoModel.clienteid == user.id,
                    CarritoModel.tenant_id == tenant_id,
                    CarritoModel.estado == "ACTIVO"
                ).first()

            if not carrito or not carrito.items:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El carrito está vacío. Agregue prendas al carrito antes de generar una reserva."
                )

            for item in carrito.items:
                inv = db.query(InventarioSucursalModel).filter(
                    InventarioSucursalModel.varianteid == item.varianteid,
                    InventarioSucursalModel.sucursalid == sucursal_id,
                    InventarioSucursalModel.tenant_id == tenant_id
                ).first()

                stock_total = inv.cantidad if (inv and inv.cantidad is not None) else 0
                stock_res = inv.stockreservado if (inv and inv.stockreservado is not None) else 0
                disp = max(0, stock_total - stock_res)

                nombre_prenda = (
                    item.variante.producto.nombre if item.variante and item.variante.producto else f"Variante #{item.varianteid}"
                )
                if item.cantidad > disp or disp <= 0:
                    sin_stock_item = (nombre_prenda, disp, item.cantidad, item.variante)
                    break

                nombres_prendas.append(nombre_prenda)
                inventarios_afectados.append((inv, item.cantidad))

        # Manejo de conflicto de concurrencia: si NO hay stock disponible
        if sin_stock_item and es_reserva_offline:
            prod_nom, disp_uds, cant_pedida, var_obj = sin_stock_item
            import re
            codigo = getattr(datos, "codigo_reserva", None)
            if not codigo and datos.observaciones:
                m = re.search(r"(RES-OFF-[A-Z0-9]+)", datos.observaciones.upper())
                if m:
                    codigo = m.group(1)
            if not codigo:
                codigo = generar_codigo_reserva(db, tenant_id)

            fecha_efectiva = to_bolivia_time(getattr(datos, "fecha_reserva", None)) or get_bolivia_now()
            mensaje_cancelacion = (
                f"No hay stock disponible para '{prod_nom}'. "
                f"La última unidad ya fue reservada o adquirida previamente por otro cliente. "
                f"Su reserva offline #{codigo} ha sido cancelada automáticamente."
            )

            reserva_cancelada = ReservaModel(
                tenant_id=tenant_id,
                codigoreserva=codigo,
                fechareserva=fecha_efectiva,
                estado="CANCELADA",
                observaciones=f"[{datos.observaciones or ''}] [CANCELADA AUTOMÁTICAMENTE: Stock agotado al sincronizar. {mensaje_cancelacion}]".strip(),
                sucursalid=sucursal_id,
                clienteid=user.id,
            )
            db.add(reserva_cancelada)
            db.flush()

            # Guardar detalles como constancia histórica
            if datos.items:
                for it in datos.items:
                    v_id = it.variante_id or (var_obj.id if var_obj else None)
                    if v_id:
                        db.add(ReservaDetalleModel(
                            varianteid=v_id,
                            reservaid=reserva_cancelada.id,
                            cantidad=it.cantidad or 1
                        ))

            # Notificación en CU19
            try:
                from app.models.cu19_gestionar_notificaciones.notificacion_model import NotificacionModel
                notif = NotificacionModel(
                    usuario_id=user.id,
                    titulo=f"❌ Reserva Cancelada #{codigo} (Sin Stock)",
                    mensaje=mensaje_cancelacion,
                    tipo="RESERVA_CANCELADA_STOCK",
                    enlace="/mis-reservas",
                    leido=False,
                    fecha_creacion=get_bolivia_now()
                )
                db.add(notif)
            except Exception:
                pass

            # Auditoría en Bitácora (CU26)
            try:
                BitacoraController.registrar_evento(
                    db=db,
                    accion="CANCELAR",
                    modulo="CU10_GESTIONAR_RESERVAS",
                    usuario_id=user.id,
                    detalle=f"Reserva offline #{codigo} cancelada automáticamente por concurrencia: stock agotado para '{prod_nom}'.",
                    datos_nuevos={"codigo": codigo, "motivo": "STOCK_AGOTADO_CONCURRENCIA", "sucursal_id": sucursal_id},
                    tenant_id=tenant_id
                )
            except Exception:
                pass

            db.commit()
            db.refresh(reserva_cancelada)

            resp = formatear_reserva(reserva_cancelada)
            resp.mensaje = mensaje_cancelacion
            resp.cancelada_sin_stock = True
            return resp

        elif sin_stock_item:
            prod_nom, disp_uds, _, _ = sin_stock_item
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para apartar '{prod_nom}'. Disponibles en tienda: {disp_uds} uds."
            )

        if not inventarios_afectados:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontraron prendas válidas para apartar."
            )

        # 5. Generar código único y cabecera de la Reserva (Hora oficial de Bolivia)
        codigo = (
            getattr(datos, "codigo_reserva", None) or
            generar_codigo_reserva(db, tenant_id)
        )
        fecha_efectiva = to_bolivia_time(getattr(datos, "fecha_reserva", None)) or get_bolivia_now()

        nueva_reserva = ReservaModel(
            tenant_id=tenant_id,
            codigoreserva=codigo,
            fechareserva=fecha_efectiva,
            estado="PENDIENTE",
            observaciones=datos.observaciones,
            sucursalid=sucursal_id,
            clienteid=user.id,
        )
        db.add(nueva_reserva)
        db.flush()

        # 6. Registrar detalles y bloquear el stock físico temporalmente (+stockreservado)
        for inv, cantidad_item in inventarios_afectados:
            detalle = ReservaDetalleModel(
                varianteid=inv.varianteid,
                reservaid=nueva_reserva.id,
                cantidad=cantidad_item,
            )
            db.add(detalle)
            inv.stockreservado = (inv.stockreservado or 0) + cantidad_item

        # 7. Si se reservó desde el carrito, marcarlo como CONVERTIDO
        if carrito:
            carrito.estado = "CONVERTIDO"

        # 8. Notificación oficial (CU19)
        try:
            from app.models.cu19_gestionar_notificaciones.notificacion_model import NotificacionModel
            resumen_prod = ", ".join(nombres_prendas[:2])
            if len(nombres_prendas) > 2:
                resumen_prod += f" y {len(nombres_prendas) - 2} prendas más"
            elif not resumen_prod:
                resumen_prod = "Prendas de Catálogo"

            notif_res = NotificacionModel(
                usuario_id=user.id,
                titulo=f"🏪 ¡Apartado en Tienda! #{codigo}",
                mensaje=(
                    f"Has apartado exitosamente: {resumen_prod}. Código de retiro: #{codigo}. "
                    f"Tienes un plazo de 48 horas para retirar tus prendas en {sucursal.nombre}."
                ),
                tipo="RESERVA_EXITOSA",
                enlace="/mis-reservas",
                leido=False,
                fecha_creacion=get_bolivia_now()
            )
            db.add(notif_res)
        except Exception as err_n:
            print(f"[Notificaciones CU19] Error en reserva: {err_n}")

        # 9. Auditoría en Bitácora (CU26)
        try:
            BitacoraController.registrar_evento(
                db=db,
                accion="CREAR",
                modulo="CU10_GESTIONAR_RESERVAS",
                usuario_id=user.id,
                detalle=(
                    f"Reserva creada con código #{codigo} en sucursal '{sucursal.nombre}'. "
                    f"Prendas apartadas: {len(inventarios_afectados)}. Vigencia: 48 horas."
                ),
                datos_nuevos={"codigo": codigo, "sucursal_id": sucursal_id, "items": len(inventarios_afectados)}
            )
        except Exception as audit_err:
            print(f"[Bitácora CU26] Error al registrar evento de reserva: {audit_err}")

        db.commit()
        db.refresh(nueva_reserva)

        return formatear_reserva(nueva_reserva)

    @classmethod
    def listar_reservas_usuario(
        cls,
        db: Session,
        usuario_id: int,
        tenant_id: int = 1,
        codigos_dispositivo: Optional[List[str]] = None
    ) -> List[ReservaResponse]:
        """Obtiene todas las reservas del usuario en el tenant con verificación de expiración automática"""
        cls.verificar_y_expirar_reservas(db, tenant_id)
        user = cls._obtener_usuario_reserva(db, usuario_id, tenant_id)

        from sqlalchemy import or_
        filtros = []
        if user and user.id:
            filtros.append(ReservaModel.clienteid == user.id)
        if codigos_dispositivo and len(codigos_dispositivo) > 0:
            filtros.append(ReservaModel.codigoreserva.in_(codigos_dispositivo))

        query = db.query(ReservaModel).filter(ReservaModel.tenant_id == tenant_id)
        if filtros:
            query = query.filter(or_(*filtros))

        reservas = query.order_by(ReservaModel.fechareserva.desc()).all()
        return [formatear_reserva(r) for r in reservas]

    @classmethod
    def obtener_reserva_por_id_o_codigo(
        cls,
        db: Session,
        id_o_codigo: str,
        usuario_id: Optional[int] = None,
        tenant_id: int = 1
    ) -> ReservaResponse:
        """Consulta el detalle de una reserva por su ID o por su código alfanumérico en el tenant"""
        cls.verificar_y_expirar_reservas(db, tenant_id)

        query = db.query(ReservaModel).filter(ReservaModel.tenant_id == tenant_id)
        if id_o_codigo.isdigit():
            query = query.filter((ReservaModel.id == int(id_o_codigo)) | (ReservaModel.codigoreserva == id_o_codigo))
        else:
            query = query.filter(ReservaModel.codigoreserva == id_o_codigo.upper())

        reserva = query.first()
        if not reserva:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró ninguna reserva con identificador '{id_o_codigo}' en este tenant."
            )

        if usuario_id:
            user = cls._obtener_usuario_reserva(db, usuario_id, tenant_id)
            es_personal = (user.rolid in [1, 2, 3]) if hasattr(user, "rolid") and user.rolid else False
            es_dueno = (reserva.clienteid == user.id)
            es_codigo_voucher = not id_o_codigo.isdigit()
            if not (es_personal or es_dueno or es_codigo_voucher):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para ver esta reserva."
                )

        return formatear_reserva(reserva)

    @classmethod
    def cancelar_reserva(
        cls,
        db: Session,
        reserva_id: int,
        usuario_id: int,
        motivo: Optional[str] = None,
        tenant_id: int = 1
    ) -> ReservaResponse:
        """
        Permite al cliente cancelar una reserva en estado PENDIENTE.
        Libera el stockreservado en inventario y audita el evento en Bitácora (CU26).
        """
        user = cls._obtener_usuario_reserva(db, usuario_id, tenant_id)

        reserva = db.query(ReservaModel).filter(
            ReservaModel.id == reserva_id,
            ReservaModel.clienteid == user.id,
            ReservaModel.tenant_id == tenant_id
        ).first()

        if not reserva:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reserva no encontrada en este tenant."
            )

        if reserva.estado != "PENDIENTE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede cancelar una reserva con estado '{reserva.estado}'. Solo se pueden cancelar reservas PENDIENTES."
            )

        # Liberar stock reservado en la sucursal física
        for d in reserva.detalles:
            inv = db.query(InventarioSucursalModel).filter(
                InventarioSucursalModel.varianteid == d.varianteid,
                InventarioSucursalModel.sucursalid == reserva.sucursalid,
                InventarioSucursalModel.tenant_id == tenant_id
            ).first()
            if inv:
                inv.stockreservado = max(0, (inv.stockreservado or 0) - d.cantidad)

        reserva.estado = "CANCELADA"
        if motivo:
            nota = f"[Cancelada por cliente: {motivo}]"
            reserva.observaciones = f"{reserva.observaciones or ''} {nota}".strip()

        # Auditoría en Bitácora (CU26)
        try:
            BitacoraController.registrar_evento(
                db=db,
                accion="CANCELAR",
                modulo="CU10_GESTIONAR_RESERVAS",
                usuario_id=user.id,
                detalle=f"Reserva #{reserva.codigoreserva} cancelada. Stock temporal liberado. Motivo: {motivo or 'N/A'}",
                datos_previos={"estado": "PENDIENTE", "codigo": reserva.codigoreserva},
                datos_nuevos={"estado": "CANCELADA", "motivo": motivo}
            )
        except Exception as audit_err:
            print(f"[Bitácora CU26] Error al registrar evento de cancelación: {audit_err}")

        db.commit()
        db.refresh(reserva)

        return formatear_reserva(reserva)

    @classmethod
    def pagar_reserva(
        cls,
        db: Session,
        reserva_id: int,
        metodo_pago: str,
        referencia: Optional[str] = None,
        origen: str = "MOVIL",
        tenant_id: int = 1
    ) -> ReservaResponse:
        """Registra el pago de una reserva (móvil o mostrador) y actualiza estado a 'PAGADA'"""
        reserva = db.query(ReservaModel).filter(
            ReservaModel.id == reserva_id,
            ReservaModel.tenant_id == tenant_id
        ).first()

        if not reserva:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reserva con ID {reserva_id} no encontrada en este tenant."
            )

        if reserva.estado in ["PAGADA", "ENTREGADA"]:
            return formatear_reserva(reserva)

        if reserva.estado in ["CANCELADA", "EXPIRADA"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede pagar una reserva con estado '{reserva.estado}'."
            )

        reserva.estado = "PAGADA"
        origen_txt = "Teléfono Móvil" if origen.upper() == "MOVIL" else "Tienda Física / Caja"
        nota = f"[PAGADA desde {origen_txt} | Método: {metodo_pago}"
        if referencia:
            nota += f" | Ref: {referencia}"
        nota += "]"
        reserva.observaciones = f"{reserva.observaciones or ''} {nota}".strip()

        db.commit()
        db.refresh(reserva)
        return formatear_reserva(reserva)
