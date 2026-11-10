# ==============================================================================
# CAPA SERVICIO (MVC - SERVICE)
# Módulo: CU5 - Gestionar Productos y Catálogo Retail (Multi-Tenant SaaS)
# Ubicación: backend/app/services/cu5_gestionar_productos/producto_service.py
# ==============================================================================

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from fastapi import HTTPException, status

from app.models.models import (
    Producto, VarianteProducto, Categoria, 
    Tenant, PlanSuscripcion, Bitacora
)
from app.schemas.producto_schema import ProductoCreate, ProductoUpdate


class ProductoService:
    """
    Servicio de dominio para el catálogo de productos y prendas,
    aislamiento multi-tenant, control de cuotas por plan de suscripción y auditoría.
    """

    @staticmethod
    def listar_productos(
        db: Session,
        tenant_id: int = 1,
        search: Optional[str] = None,
        categoria_id: Optional[int] = None,
        genero: Optional[str] = None,
        activo: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Producto]:
        """
        Lista productos pertenecientes al tenant aplicando filtros de búsqueda y clasificación.
        """
        query = db.query(Producto).filter(Producto.tenant_id == tenant_id)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                (Producto.nombre.ilike(pattern)) |
                (Producto.marca.ilike(pattern)) |
                (Producto.descripcion.ilike(pattern))
            )

        if categoria_id:
            query = query.filter(Producto.categoriaid == categoria_id)

        if genero:
            query = query.filter(Producto.genero.ilike(f"%{genero.strip()}%"))

        if activo is not None:
            query = query.filter(Producto.activo == activo)

        return query.order_by(Producto.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def obtener_producto_por_id(
        db: Session,
        id: int,
        tenant_id: Optional[int] = None
    ) -> Producto:
        """
        Obtiene el detalle de un producto validando el tenant asignado.
        """
        query = db.query(Producto).filter(Producto.id == id)
        if tenant_id is not None:
            query = query.filter(Producto.tenant_id == tenant_id)

        producto = query.first()
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado en el catálogo de este comercio"
            )
        return producto

    @staticmethod
    def crear_producto(
        db: Session,
        data: ProductoCreate,
        tenant_id: int = 1,
        usuario_id: Optional[int] = None
    ) -> Producto:
        """
        Registra un nuevo producto en el catálogo validando la cuota máxima del Plan de Suscripción.
        """
        # 1. Validar restricción de cuota según Plan de Suscripción
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant and tenant.plan_id:
            plan = db.query(PlanSuscripcion).filter(PlanSuscripcion.id == tenant.plan_id).first()
            if plan and plan.limite_productos:
                total_activos = db.query(Producto).filter(
                    Producto.tenant_id == tenant_id,
                    Producto.activo == True
                ).count()
                if total_activos >= plan.limite_productos:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=(
                            f"Límite de productos alcanzado: su plan '{plan.nombre}' permite un máximo de "
                            f"{plan.limite_productos} productos en el catálogo. Actualice su suscripción para registrar más prendas."
                        )
                    )

        # 2. Comprobar que no exista duplicado con el mismo nombre en el tenant
        clean_nombre = data.nombre.strip()
        existente = db.query(Producto).filter(
            func.lower(Producto.nombre) == clean_nombre.lower(),
            Producto.tenant_id == tenant_id
        ).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un producto con ese nombre en este catálogo"
            )

        # 3. Validar categoría si fue provista
        if data.categoriaid is not None:
            cat = db.query(Categoria).filter(Categoria.id == data.categoriaid).first()
            if not cat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La categoría seleccionada (ID: {data.categoriaid}) no existe en el catálogo."
                )

        # 4. Crear nuevo producto
        nuevo = Producto(
            tenant_id=tenant_id,
            nombre=clean_nombre,
            descripcion=data.descripcion.strip() if data.descripcion else None,
            marca=data.marca.strip() if data.marca else None,
            genero=data.genero.strip() if data.genero else None,
            grupoedad=data.grupoedad.strip() if data.grupoedad else None,
            preciobase=data.preciobase,
            imagenprincipal=data.imagenprincipal,
            categoriaid=data.categoriaid,
            activo=data.activo if data.activo is not None else True
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)

        # 4. Asegurar variantes e inventarios iniciales para las sucursales del tenant
        try:
            from app.services.cu13_gestionar_inventario_movimientos.inventario_service import InventarioService
            InventarioService.asegurar_variantes_e_inventario(db, tenant_id=tenant_id)
        except Exception:
            pass

        # 5. Auditoría en Bitácora (CU20)
        try:
            from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
            BitacoraController.registrar_evento(
                db=db,
                accion="CREAR_PRODUCTO",
                modulo="PRODUCTOS",
                usuario_id=usuario_id or 1,
                detalle=f"Registro de nuevo producto: {nuevo.nombre} (ID: {nuevo.id}) en tenant #{tenant_id}",
                datos_nuevos={"id": nuevo.id, "nombre": nuevo.nombre, "precio": float(nuevo.preciobase or 0)}
            )
        except Exception:
            pass

        return nuevo

    @staticmethod
    def actualizar_producto(
        db: Session,
        id: int,
        data: ProductoUpdate,
        tenant_id: Optional[int] = None,
        usuario_id: Optional[int] = None
    ) -> Producto:
        """
        Actualiza los atributos del producto.
        """
        producto = ProductoService.obtener_producto_por_id(db, id=id, tenant_id=tenant_id)

        update_data = data.dict(exclude_unset=True)
        if "nombre" in update_data and update_data["nombre"]:
            nuevo_nombre = update_data["nombre"].strip()
            if nuevo_nombre.lower() != producto.nombre.lower():
                existente = db.query(Producto).filter(
                    func.lower(Producto.nombre) == nuevo_nombre.lower(),
                    Producto.tenant_id == producto.tenant_id,
                    Producto.id != producto.id
                ).first()
                if existente:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Ya existe otro producto con ese nombre en este comercio"
                    )
                producto.nombre = nuevo_nombre
                del update_data["nombre"]

        for key, value in update_data.items():
            setattr(producto, key, value)

        db.commit()
        db.refresh(producto)

        try:
            from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
            BitacoraController.registrar_evento(
                db=db,
                accion="ACTUALIZAR_PRODUCTO",
                modulo="PRODUCTOS",
                usuario_id=usuario_id or 1,
                detalle=f"Actualización del producto ID={id} ({producto.nombre})",
                datos_nuevos={"id": producto.id, "nombre": producto.nombre, "precio": float(producto.preciobase or 0)}
            )
        except Exception:
            pass

        return producto

    @staticmethod
    def cambiar_estado_producto(
        db: Session,
        id: int,
        activo: bool,
        tenant_id: Optional[int] = None,
        usuario_id: Optional[int] = None
    ) -> Producto:
        """
        Activa o suspende un producto del catálogo, verificando cuota al reactivar.
        """
        producto = ProductoService.obtener_producto_por_id(db, id=id, tenant_id=tenant_id)

        # Si se reactiva, verificar límite de plan
        if activo and not producto.activo:
            tenant = db.query(Tenant).filter(Tenant.id == producto.tenant_id).first()
            if tenant and tenant.plan_id:
                plan = db.query(PlanSuscripcion).filter(PlanSuscripcion.id == tenant.plan_id).first()
                if plan and plan.limite_productos:
                    total_activos = db.query(Producto).filter(
                        Producto.tenant_id == producto.tenant_id,
                        Producto.activo == True
                    ).count()
                    if total_activos >= plan.limite_productos:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"No se puede reactivar: su plan '{plan.nombre}' permite un máximo de {plan.limite_productos} productos."
                        )

        producto.activo = activo
        db.commit()
        db.refresh(producto)

        try:
            from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
            BitacoraController.registrar_evento(
                db=db,
                accion="CAMBIO_ESTADO_PRODUCTO",
                modulo="PRODUCTOS",
                usuario_id=usuario_id or 1,
                detalle=f"Cambio de estado del producto ID={id} a {'Activo' if activo else 'Inactivo'}",
                datos_nuevos={"id": id, "activo": activo}
            )
        except Exception:
            pass

        return producto

    @staticmethod
    def eliminar_producto(
        db: Session,
        id: int,
        tenant_id: Optional[int] = None,
        usuario_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Elimina de forma segura un producto si no posee ventas registradas, o aplica baja lógica.
        """
        producto = ProductoService.obtener_producto_por_id(db, id=id, tenant_id=tenant_id)
        nombre_prod = producto.nombre

        # 1. Obtener variantes asociadas al producto
        variantes = db.query(VarianteProducto).filter(VarianteProducto.productoid == id).all()
        var_ids = [v.id for v in variantes]

        if var_ids:
            v_ids_str = ",".join(str(i) for i in var_ids)

            # 2. Verificar ventas registradas
            try:
                ventas_count = db.execute(
                    text(f"SELECT count(*) FROM detalle_venta WHERE varianteid IN ({v_ids_str})")
                ).scalar() or 0
                if ventas_count > 0:
                    producto.activo = False
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"No se puede eliminar permanentemente '{nombre_prod}' porque tiene {ventas_count} venta(s) registrada(s). Ha sido desactivado del catálogo."
                    )
            except HTTPException:
                raise
            except Exception:
                pass

            # 3. Limpiar dependencias en carritos y reservas
            try:
                db.execute(text(f"DELETE FROM carrito_item WHERE varianteid IN ({v_ids_str})"))
                db.execute(text(f"DELETE FROM reserva_detalle WHERE varianteid IN ({v_ids_str})"))
            except Exception:
                pass

            # 4. Limpiar inventarios y movimientos
            try:
                inv_ids = db.execute(text(f"SELECT id FROM inventario WHERE varianteid IN ({v_ids_str})")).fetchall()
                if inv_ids:
                    inv_ids_str = ",".join(str(row[0]) for row in inv_ids)
                    db.execute(text(f"DELETE FROM movimiento_inventario WHERE inventarioid IN ({inv_ids_str})"))
                db.execute(text(f"DELETE FROM inventario WHERE varianteid IN ({v_ids_str})"))
            except Exception:
                pass

            # 5. Eliminar variantes
            db.execute(text(f"DELETE FROM variante_producto WHERE id IN ({v_ids_str})"))

        # 6. Eliminar asociaciones con proveedores
        try:
            db.execute(text("DELETE FROM producto_proveedor WHERE idproducto = :pid"), {"pid": id})
        except Exception:
            pass

        db.delete(producto)
        db.commit()

        try:
            from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
            BitacoraController.registrar_evento(
                db=db,
                accion="ELIMINAR_PRODUCTO",
                modulo="PRODUCTOS",
                usuario_id=usuario_id or 1,
                detalle=f"Eliminación definitiva del producto '{nombre_prod}' (ID={id})"
            )
        except Exception:
            pass

        return {"message": f"Producto '{nombre_prod}' eliminado definitivamente de la base de datos", "id": id}


# ==============================================================================
# ALIASES DE RETROCOMPATIBILIDAD
# ==============================================================================
ProductoService.get_all = ProductoService.listar_productos
ProductoService.get_by_id = ProductoService.obtener_producto_por_id
ProductoService.create = ProductoService.crear_producto
ProductoService.update = ProductoService.actualizar_producto
ProductoService.toggle_status = ProductoService.cambiar_estado_producto
ProductoService.delete = ProductoService.eliminar_producto
ProductoService.logical_delete = ProductoService.eliminar_producto
