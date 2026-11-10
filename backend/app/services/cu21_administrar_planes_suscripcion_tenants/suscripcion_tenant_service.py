# ==============================================================================
# CU21 - ADMINISTRAR PLANES DE SUSCRIPCIÓN Y TENANTS -> SERVICIO (MVC - SERVICE)
# Ubicación: backend/app/services/cu21_administrar_planes_suscripcion_tenants/suscripcion_tenant_service.py
# ==============================================================================

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.models.saas_tenant.tenant_model import (
    PlanSuscripcion, Tenant, TenantSuscripcion, TenantConfiguracion
)
from app.models.cu4_gestionar_sucursales.sucursal_model import SucursalModel
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.models.cu5_gestionar_productos.producto_model import ProductoModel
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
from app.schemas.cu21_administrar_planes_suscripcion_tenants.suscripcion_tenant_schema import (
    PlanSuscripcionCreate, PlanSuscripcionUpdate, TenantCreate, TenantUpdate
)


class SuscripcionTenantService:
    """
    Servicio de Administración Multi-Tenant SaaS (CU21).
    Controla el ciclo de vida de los planes comerciales, alta de tenants,
    cuotas de recursos (sucursales, usuarios, catálogo) y auditoría inmutable.
    """

    # --------------------------------------------------------------------------
    # GESTIÓN DE PLANES DE SUSCRIPCIÓN
    # --------------------------------------------------------------------------

    @staticmethod
    def listar_planes(db: Session, solo_activos: bool = False) -> List[PlanSuscripcion]:
        """Retorna el catálogo de planes comerciales SaaS."""
        query = db.query(PlanSuscripcion)
        if solo_activos:
            query = query.filter(PlanSuscripcion.activo == True)
        return query.order_by(PlanSuscripcion.precio_mensual.asc()).all()

    @staticmethod
    def obtener_plan_por_id(db: Session, plan_id: int) -> Optional[PlanSuscripcion]:
        """Obtiene un plan específico por su identificador primario."""
        return db.query(PlanSuscripcion).filter(PlanSuscripcion.id == plan_id).first()

    @staticmethod
    def crear_plan(db: Session, data: PlanSuscripcionCreate, usuario_id: Optional[int] = None) -> PlanSuscripcion:
        """Crea un nuevo plan de suscripción en el catálogo SaaS."""
        existente = db.query(PlanSuscripcion).filter(
            func.lower(PlanSuscripcion.nombre) == func.lower(data.nombre)
        ).first()
        if existente:
            raise ValueError(f"Ya existe un plan con el nombre '{data.nombre}'.")

        nuevo_plan = PlanSuscripcion(
            nombre=data.nombre.strip(),
            descripcion=data.descripcion,
            precio_mensual=data.precio_mensual,
            limite_sucursales=data.limite_sucursales,
            limite_usuarios=data.limite_usuarios,
            limite_productos=data.limite_productos,
            habilitar_reportes_ia=data.habilitar_reportes_ia,
            habilitar_vestidor_ia=data.habilitar_vestidor_ia,
            activo=data.activo,
            fechacreacion=datetime.utcnow()
        )
        db.add(nuevo_plan)
        db.commit()
        db.refresh(nuevo_plan)

        BitacoraController.registrar_evento(
            db=db,
            accion="CREAR",
            modulo="PLANES_SUSCRIPCION",
            usuario_id=usuario_id,
            detalle=f"Plan SaaS '{nuevo_plan.nombre}' creado con precio Bs. {nuevo_plan.precio_mensual}.",
            datos_nuevos={
                "id": nuevo_plan.id,
                "nombre": nuevo_plan.nombre,
                "precio": float(nuevo_plan.precio_mensual),
                "sucursales": nuevo_plan.limite_sucursales,
                "usuarios": nuevo_plan.limite_usuarios
            }
        )
        return nuevo_plan

    @staticmethod
    def actualizar_plan(db: Session, plan_id: int, data: PlanSuscripcionUpdate, usuario_id: Optional[int] = None) -> PlanSuscripcion:
        """Actualiza las condiciones o cuotas de un plan comercial."""
        plan = db.query(PlanSuscripcion).filter(PlanSuscripcion.id == plan_id).first()
        if not plan:
            raise ValueError(f"Plan con ID {plan_id} no encontrado.")

        datos_previos = {
            "nombre": plan.nombre,
            "precio": float(plan.precio_mensual),
            "sucursales": plan.limite_sucursales,
            "usuarios": plan.limite_usuarios,
            "activo": plan.activo
        }

        if data.nombre is not None:
            plan.nombre = data.nombre.strip()
        if data.descripcion is not None:
            plan.descripcion = data.descripcion
        if data.precio_mensual is not None:
            plan.precio_mensual = data.precio_mensual
        if data.limite_sucursales is not None:
            plan.limite_sucursales = data.limite_sucursales
        if data.limite_usuarios is not None:
            plan.limite_usuarios = data.limite_usuarios
        if data.limite_productos is not None:
            plan.limite_productos = data.limite_productos
        if data.habilitar_reportes_ia is not None:
            plan.habilitar_reportes_ia = data.habilitar_reportes_ia
        if data.habilitar_vestidor_ia is not None:
            plan.habilitar_vestidor_ia = data.habilitar_vestidor_ia
        if data.activo is not None:
            plan.activo = data.activo

        db.commit()
        db.refresh(plan)

        BitacoraController.registrar_evento(
            db=db,
            accion="MODIFICAR",
            modulo="PLANES_SUSCRIPCION",
            usuario_id=usuario_id,
            detalle=f"Plan '{plan.nombre}' (ID {plan.id}) actualizado.",
            datos_previos=datos_previos,
            datos_nuevos={
                "nombre": plan.nombre,
                "precio": float(plan.precio_mensual),
                "sucursales": plan.limite_sucursales,
                "usuarios": plan.limite_usuarios,
                "activo": plan.activo
            }
        )
        return plan

    # --------------------------------------------------------------------------
    # GESTIÓN DE TENANTS Y CUOTAS DE USO
    # --------------------------------------------------------------------------

    @staticmethod
    def calcular_metricas_tenant(db: Session, tenant_id: int, plan: Optional[PlanSuscripcion]) -> Dict[str, Any]:
        """Calcula el consumo actual de recursos frente a las cuotas permitidas."""
        lim_suc = plan.limite_sucursales if plan else 1
        lim_usr = plan.limite_usuarios if plan else 3
        lim_prod = plan.limite_productos if plan else 100

        usadas_suc = db.query(SucursalModel).filter(SucursalModel.tenant_id == tenant_id).count()
        usados_usr = db.query(UsuarioModel).filter(UsuarioModel.tenant_id == tenant_id).count()
        usados_prod = db.query(ProductoModel).filter(ProductoModel.tenant_id == tenant_id).count()

        porc_suc = round((usadas_suc / lim_suc * 100) if lim_suc > 0 else 0.0, 1)
        porc_usr = round((usados_usr / lim_usr * 100) if lim_usr > 0 else 0.0, 1)

        return {
            "sucursales_usadas": usadas_suc,
            "sucursales_limite": lim_suc,
            "usuarios_usados": usados_usr,
            "usuarios_limite": lim_usr,
            "productos_usados": usados_prod,
            "productos_limite": lim_prod,
            "porcentaje_sucursales": porc_suc,
            "porcentaje_usuarios": porc_usr
        }

    @staticmethod
    def listar_tenants_enriquecidos(db: Session) -> List[Dict[str, Any]]:
        """Retorna la nómina de tenants con su suscripción vigente y métricas de consumo."""
        tenants = db.query(Tenant).options(joinedload(Tenant.plan)).order_by(Tenant.id.asc()).all()
        resultado = []

        for t in tenants:
            suscripcion_actual = (
                db.query(TenantSuscripcion)
                .filter(TenantSuscripcion.tenant_id == t.id)
                .order_by(desc(TenantSuscripcion.fecha_fin))
                .first()
            )

            # Auto-seed de suscripción de cortesía si el tenant no tiene ninguna registrada
            if not suscripcion_actual and t.plan_id:
                suscripcion_actual = TenantSuscripcion(
                    tenant_id=t.id,
                    plan_id=t.plan_id,
                    fecha_inicio=datetime.utcnow(),
                    fecha_fin=datetime.utcnow() + timedelta(days=365),
                    estado="ACTIVA" if t.activo else "SUSPENDIDA",
                    monto_pagado=t.plan.precio_mensual * 12 if t.plan else Decimal("0.00"),
                    metodo_pago="REGISTRO_INICIAL"
                )
                db.add(suscripcion_actual)
                db.commit()
                db.refresh(suscripcion_actual)

            metricas = SuscripcionTenantService.calcular_metricas_tenant(db, t.id, t.plan)

            susc_dict = None
            if suscripcion_actual:
                susc_dict = {
                    "id": suscripcion_actual.id,
                    "plan_id": suscripcion_actual.plan_id,
                    "plan_nombre": t.plan.nombre if t.plan else "Sin Plan",
                    "fecha_inicio": suscripcion_actual.fecha_inicio,
                    "fecha_fin": suscripcion_actual.fecha_fin,
                    "estado": suscripcion_actual.estado,
                    "monto_pagado": suscripcion_actual.monto_pagado,
                    "metodo_pago": suscripcion_actual.metodo_pago
                }

            plan_dict = None
            if t.plan:
                plan_dict = {
                    "id": t.plan.id,
                    "nombre": t.plan.nombre,
                    "descripcion": t.plan.descripcion,
                    "precio_mensual": t.plan.precio_mensual,
                    "limite_sucursales": t.plan.limite_sucursales,
                    "limite_usuarios": t.plan.limite_usuarios,
                    "limite_productos": t.plan.limite_productos,
                    "habilitar_reportes_ia": bool(getattr(t.plan, "habilitar_reportes_ia", False) or getattr(t.plan, "habilitar_vestidor_ia", False)),
                    "habilitar_vestidor_ia": t.plan.habilitar_vestidor_ia,
                    "activo": t.plan.activo,
                    "fechacreacion": t.plan.fechacreacion
                }

            # Buscar el usuario Administrador asignado a este Tenant
            from app.models.cu1_gestionar_autenticacion.usuario_rol_model import RolModel
            admin_usr = (
                db.query(UsuarioModel)
                .join(RolModel, UsuarioModel.rolid == RolModel.id)
                .filter(
                    UsuarioModel.tenant_id == t.id,
                    RolModel.nombre.in_(["ADMIN", "ADMINISTRADOR"])
                )
                .order_by(UsuarioModel.id.asc())
                .first()
            )
            if not admin_usr:
                admin_usr = (
                    db.query(UsuarioModel)
                    .filter(UsuarioModel.tenant_id == t.id, UsuarioModel.rolid == 1)
                    .order_by(UsuarioModel.id.asc())
                    .first()
                )

            admin_dict = None
            if admin_usr:
                admin_dict = {
                    "id": admin_usr.id,
                    "nombre": admin_usr.nombre,
                    "apellido": admin_usr.apellido or "",
                    "email": admin_usr.email,
                    "activo": admin_usr.activo
                }

            resultado.append({
                "id": t.id,
                "uuid": str(t.uuid),
                "nombre": t.nombre,
                "slug": t.slug,
                "dominio_personalizado": t.dominio_personalizado,
                "nit_ruc": t.nit_ruc,
                "email_contacto": t.email_contacto,
                "telefono_contacto": t.telefono_contacto,
                "direccion_fiscal": t.direccion_fiscal,
                "logo_url": t.logo_url,
                "plan_id": t.plan_id,
                "plan": plan_dict,
                "activo": t.activo,
                "fechacreacion": t.fechacreacion,
                "suscripcion_actual": susc_dict,
                "metricas_uso": metricas,
                "administrador": admin_dict
            })

        return resultado

    @staticmethod
    def obtener_tenant_detalle(db: Session, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un tenant con todas sus métricas y configuración."""
        tenant = db.query(Tenant).options(
            joinedload(Tenant.plan),
            joinedload(Tenant.configuracion)
        ).filter(Tenant.id == tenant_id).first()

        if not tenant:
            return None

        metricas = SuscripcionTenantService.calcular_metricas_tenant(db, tenant.id, tenant.plan)
        suscripcion = (
            db.query(TenantSuscripcion)
            .filter(TenantSuscripcion.tenant_id == tenant.id)
            .order_by(desc(TenantSuscripcion.fecha_fin))
            .first()
        )

        return {
            "tenant": tenant,
            "metricas": metricas,
            "suscripcion": suscripcion,
            "configuracion": tenant.configuracion
        }

    @staticmethod
    def crear_tenant_completo(
        db: Session,
        data: TenantCreate,
        usuario_id: Optional[int] = None
    ) -> Tenant:
        """Crea un nuevo Tenant con configuración inicial y suscripción vinculada."""
        # Validar duplicados de slug
        slug_limpio = data.slug.strip().lower().replace(" ", "-")
        existente = db.query(Tenant).filter(Tenant.slug == slug_limpio).first()
        if existente:
            raise ValueError(f"El identificador de dominio/slug '{slug_limpio}' ya está en uso.")

        plan = db.query(PlanSuscripcion).filter(PlanSuscripcion.id == data.plan_id).first()
        if not plan:
            raise ValueError(f"Plan con ID {data.plan_id} no existe.")

        nuevo_tenant = Tenant(
            uuid=uuid.uuid4(),
            nombre=data.nombre.strip(),
            slug=slug_limpio,
            nit_ruc=data.nit_ruc.strip() if data.nit_ruc else None,
            email_contacto=data.email_contacto.strip().lower(),
            telefono_contacto=data.telefono_contacto.strip() if data.telefono_contacto else None,
            direccion_fiscal=data.direccion_fiscal,
            logo_url=data.logo_url,
            plan_id=plan.id,
            activo=True,
            fechacreacion=datetime.utcnow()
        )
        db.add(nuevo_tenant)
        db.flush()  # Obtener ID generado

        # Configuración por defecto
        config = TenantConfiguracion(
            tenant_id=nuevo_tenant.id,
            moneda_simbolo="Bs.",
            moneda_iso="BOB",
            zona_horaria="America/La_Paz",
            tiempo_expiracion_reserva_horas=48,
            color_primario_hex="#0f172a",
            color_secundario_hex="#4f46e5"
        )
        db.add(config)

        # Suscripción inicial
        dias = data.meses_suscripcion * 30
        monto_total = Decimal(str(plan.precio_mensual)) * Decimal(str(data.meses_suscripcion))

        suscripcion = TenantSuscripcion(
            tenant_id=nuevo_tenant.id,
            plan_id=plan.id,
            fecha_inicio=datetime.utcnow(),
            fecha_fin=datetime.utcnow() + timedelta(days=dias),
            estado="ACTIVA",
            monto_pagado=monto_total,
            metodo_pago="ALTA_INICIAL"
        )
        db.add(suscripcion)

        # Crear sucursal principal inicial para el nuevo tenant
        sucursal_inicial = SucursalModel(
            tenant_id=nuevo_tenant.id,
            nombre=f"Sucursal Central - {nuevo_tenant.nombre}",
            ciudad="Santa Cruz",
            direccion=data.direccion_fiscal or "Av. Principal #100",
            telefono=data.telefono_contacto or "70000000",
            activo=True
        )
        db.add(sucursal_inicial)
        db.flush()

        # Crear usuario Administrador del Tenant
        from app.core.security import get_password_hash
        from app.models.cu1_gestionar_autenticacion.usuario_rol_model import RolModel
        admin_rol = db.query(RolModel).filter(RolModel.nombre == "ADMIN").first()
        rol_admin_id = admin_rol.id if admin_rol else 1

        email_admin = (data.admin_email or data.email_contacto).strip().lower()
        pass_admin = (data.admin_password or "Admin123.").strip()
        nombre_admin = (data.admin_nombre or f"Admin {nuevo_tenant.nombre}").strip()
        apellido_admin = (data.admin_apellido or "Gerencia").strip()

        usr_existente = db.query(UsuarioModel).filter(func.lower(UsuarioModel.email) == email_admin).first()
        if not usr_existente:
            nuevo_admin = UsuarioModel(
                tenant_id=nuevo_tenant.id,
                nombre=nombre_admin,
                apellido=apellido_admin,
                email=email_admin,
                passwordhash=get_password_hash(pass_admin),
                telefono=data.telefono_contacto,
                rolid=rol_admin_id,
                sucursalid=sucursal_inicial.id,
                activo=True,
                verificado=True
            )
            db.add(nuevo_admin)
        else:
            usr_existente.tenant_id = nuevo_tenant.id
            usr_existente.rolid = rol_admin_id
            usr_existente.passwordhash = get_password_hash(pass_admin)
            usr_existente.activo = True
            usr_existente.verificado = True

        db.commit()
        db.refresh(nuevo_tenant)

        BitacoraController.registrar_evento(
            db=db,
            accion="CREAR",
            modulo="TENANTS_SAAS",
            usuario_id=usuario_id,
            detalle=f"Nuevo Tenant '{nuevo_tenant.nombre}' (slug: {nuevo_tenant.slug}) creado con Plan '{plan.nombre}'.",
            datos_nuevos={
                "tenant_id": nuevo_tenant.id,
                "nombre": nuevo_tenant.nombre,
                "slug": nuevo_tenant.slug,
                "plan": plan.nombre,
                "meses": data.meses_suscripcion
            }
        )
        return nuevo_tenant

    @staticmethod
    def cambiar_plan_tenant(
        db: Session,
        tenant_id: int,
        nuevo_plan_id: int,
        motivo: Optional[str] = None,
        usuario_id: Optional[int] = None
    ) -> Tenant:
        """Asigna un nuevo plan a un tenant (Upgrade/Downgrade)."""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant con ID {tenant_id} no encontrado.")

        nuevo_plan = db.query(PlanSuscripcion).filter(PlanSuscripcion.id == nuevo_plan_id).first()
        if not nuevo_plan:
            raise ValueError(f"Plan con ID {nuevo_plan_id} no existe.")

        plan_anterior_id = tenant.plan_id
        tenant.plan_id = nuevo_plan.id

        # Registrar nueva suscripción
        nueva_suscripcion = TenantSuscripcion(
            tenant_id=tenant.id,
            plan_id=nuevo_plan.id,
            fecha_inicio=datetime.utcnow(),
            fecha_fin=datetime.utcnow() + timedelta(days=365),
            estado="ACTIVA",
            monto_pagado=nuevo_plan.precio_mensual * 12,
            metodo_pago="CAMBIO_PLAN"
        )
        db.add(nueva_suscripcion)
        db.commit()
        db.refresh(tenant)

        BitacoraController.registrar_evento(
            db=db,
            accion="CAMBIO_ESTADO",
            modulo="TENANTS_SAAS",
            usuario_id=usuario_id,
            detalle=f"Tenant '{tenant.nombre}' migrado a Plan '{nuevo_plan.nombre}'. Motivo: {motivo or 'N/A'}",
            datos_previos={"plan_id": plan_anterior_id},
            datos_nuevos={"plan_id": nuevo_plan.id, "plan_nombre": nuevo_plan.nombre}
        )
        return tenant

    @staticmethod
    def toggle_tenant_estado(
        db: Session,
        tenant_id: int,
        activo: bool,
        motivo: Optional[str] = None,
        usuario_id: Optional[int] = None
    ) -> Tenant:
        """Activa o suspende el acceso integral de una empresa / tenant."""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant con ID {tenant_id} no encontrado.")

        estado_anterior = tenant.activo
        tenant.activo = activo

        # Actualizar estado en suscripción vigente
        suscripcion = (
            db.query(TenantSuscripcion)
            .filter(TenantSuscripcion.tenant_id == tenant.id)
            .order_by(desc(TenantSuscripcion.fecha_fin))
            .first()
        )
        if suscripcion:
            suscripcion.estado = "ACTIVA" if activo else "SUSPENDIDA"

        db.commit()
        db.refresh(tenant)

        accion_str = "ACTIVAR" if activo else "SUSPENDER"
        BitacoraController.registrar_evento(
            db=db,
            accion=accion_str,
            modulo="TENANTS_SAAS",
            usuario_id=usuario_id,
            detalle=f"Tenant '{tenant.nombre}' {'activado' if activo else 'suspendido'}. Motivo: {motivo or 'N/A'}",
            datos_previos={"activo": estado_anterior},
            datos_nuevos={"activo": activo}
        )
        return tenant

    @staticmethod
    def renovar_suscripcion(
        db: Session,
        tenant_id: int,
        meses: int = 12,
        metodo_pago: str = "TRANSFERENCIA_BANCARIA",
        usuario_id: Optional[int] = None
    ) -> TenantSuscripcion:
        """Extiende la vigencia de la suscripción de un tenant."""
        tenant = db.query(Tenant).options(joinedload(Tenant.plan)).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant con ID {tenant_id} no encontrado.")

        plan = tenant.plan
        if not plan:
            raise ValueError("El tenant no tiene un plan comercial asignado para renovar.")

        susc_actual = (
            db.query(TenantSuscripcion)
            .filter(TenantSuscripcion.tenant_id == tenant.id)
            .order_by(desc(TenantSuscripcion.fecha_fin))
            .first()
        )

        base_date = datetime.utcnow()
        if susc_actual and susc_actual.fecha_fin > base_date:
            base_date = susc_actual.fecha_fin

        nueva_fecha_fin = base_date + timedelta(days=meses * 30)
        monto = Decimal(str(plan.precio_mensual)) * Decimal(str(meses))

        nueva_susc = TenantSuscripcion(
            tenant_id=tenant.id,
            plan_id=plan.id,
            fecha_inicio=datetime.utcnow(),
            fecha_fin=nueva_fecha_fin,
            estado="ACTIVA",
            monto_pagado=monto,
            metodo_pago=metodo_pago
        )
        tenant.activo = True
        db.add(nueva_susc)
        db.commit()
        db.refresh(nueva_susc)

        BitacoraController.registrar_evento(
            db=db,
            accion="RENOVAR",
            modulo="TENANTS_SAAS",
            usuario_id=usuario_id,
            detalle=f"Suscripción renovada para Tenant '{tenant.nombre}' por {meses} meses hasta {nueva_fecha_fin.strftime('%Y-%m-%d')}.",
            datos_nuevos={"monto": float(monto), "nueva_fecha_fin": nueva_fecha_fin.isoformat()}
        )
        return nueva_susc

    @staticmethod
    def asignar_administrador_tenant(
        db: Session,
        tenant_id: int,
        nombre: str,
        apellido: Optional[str],
        email: str,
        password: str,
        usuario_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Crea o actualiza el usuario Administrador de un Tenant específico."""
        from app.core.security import get_password_hash
        from app.models.cu1_gestionar_autenticacion.usuario_rol_model import RolModel

        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant con ID {tenant_id} no encontrado.")

        clean_email = email.strip().lower()
        clean_pass = (password or "Admin123.").strip()

        admin_rol = db.query(RolModel).filter(RolModel.nombre == "ADMIN").first()
        rol_admin_id = admin_rol.id if admin_rol else 1

        usuario = db.query(UsuarioModel).filter(func.lower(UsuarioModel.email) == clean_email).first()
        if usuario:
            usuario.tenant_id = tenant.id
            usuario.nombre = nombre.strip()
            usuario.apellido = (apellido or "").strip()
            usuario.passwordhash = get_password_hash(clean_pass)
            usuario.rolid = rol_admin_id
            usuario.activo = True
            usuario.verificado = True
        else:
            sucursal = db.query(SucursalModel).filter(SucursalModel.tenant_id == tenant.id).first()
            usuario = UsuarioModel(
                tenant_id=tenant.id,
                nombre=nombre.strip(),
                apellido=(apellido or "").strip(),
                email=clean_email,
                passwordhash=get_password_hash(clean_pass),
                rolid=rol_admin_id,
                sucursalid=sucursal.id if sucursal else None,
                activo=True,
                verificado=True
            )
            db.add(usuario)

        tenant.email_contacto = clean_email
        db.commit()
        db.refresh(usuario)

        BitacoraController.registrar_evento(
            db=db,
            accion="ASIGNAR_ADMIN",
            modulo="TENANTS_SAAS",
            usuario_id=usuario_id,
            detalle=f"Administrador '{usuario.email}' asignado a la empresa '{tenant.nombre}' (Tenant #{tenant.id}).",
            datos_nuevos={"tenant_id": tenant.id, "admin_email": usuario.email, "admin_nombre": usuario.nombre}
        )

        return {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "email": usuario.email,
            "tenant_id": tenant.id,
            "tenant_nombre": tenant.nombre
        }

    @staticmethod
    def obtener_kpis_saas(db: Session) -> Dict[str, Any]:
        """Calcula los indicadores globales de la plataforma SaaS."""
        total_tenants = db.query(Tenant).count()
        activos = db.query(Tenant).filter(Tenant.activo == True).count()
        suspendidos = total_tenants - activos

        # MRR (Monthly Recurring Revenue) estimado sumando precio_mensual de tenants activos
        tenants_activos = db.query(Tenant).options(joinedload(Tenant.plan)).filter(Tenant.activo == True).all()
        mrr = sum([float(t.plan.precio_mensual) for t in tenants_activos if t.plan])

        planes = db.query(PlanSuscripcion).all()
        total_planes = len(planes)
        distribucion = {}
        for p in planes:
            c = db.query(Tenant).filter(Tenant.plan_id == p.id, Tenant.activo == True).count()
            distribucion[p.nombre] = c

        return {
            "total_tenants": total_tenants,
            "tenants_activos": activos,
            "tenants_suspendidos": suspendidos,
            "mrr_estimado": round(mrr, 2),
            "total_planes": total_planes,
            "distribucion_planes": distribucion
        }
