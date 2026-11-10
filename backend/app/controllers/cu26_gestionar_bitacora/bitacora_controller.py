# ==============================================================================
# CU26 - GESTIONAR BITACORA Y AUDITORIA -> CAPA CONTROLADOR (MVC - CONTROLLER)
# Ubicación: backend/app/controllers/cu26_gestionar_bitacora/bitacora_controller.py
# ==============================================================================

import json
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_

from app.models.cu26_gestionar_bitacora.bitacora_model import BitacoraModel, get_bolivia_now
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel, RolModel
from app.models.models import Bitacora, Usuario, Rol, Tenant
from app.schemas.cu26_gestionar_bitacora.bitacora_schema import BitacoraCreate


class BitacoraController:
    """
    Controlador de negocio para la gestión y consulta de la bitácora de auditoría (CU26).
    Implementa registro seguro, consultas multi-criterio, estadísticas de seguridad y exportación.
    """

    @staticmethod
    def _serializar_json(datos: Any) -> Optional[str]:
        if datos is None:
            return None
        if isinstance(datos, str):
            return datos
        try:
            return json.dumps(datos, ensure_ascii=False, default=str)
        except Exception:
            return str(datos)

    @staticmethod
    def registrar_evento(
        db: Session,
        accion: str,
        modulo: str,
        usuario_id: Optional[int] = None,
        detalle: Optional[str] = None,
        ip: Optional[str] = None,
        datos_previos: Optional[Any] = None,
        datos_nuevos: Optional[Any] = None,
        fechahora: Optional[datetime] = None,
        tenant_id: int = 1
    ) -> Optional[BitacoraModel]:
        """
        Registra una nueva entrada de auditoría de forma atómica y protegida en hora boliviana.
        Un fallo en el registro de bitácora no interrumpe la transacción principal.
        """
        try:
            previos_str = BitacoraController._serializar_json(datos_previos)
            nuevos_str = BitacoraController._serializar_json(datos_nuevos)
            fecha_efectiva = fechahora or get_bolivia_now()

            registro = BitacoraModel(
                tenant_id=tenant_id,
                usuarioid=usuario_id,
                accion=accion.strip().upper(),
                modulo=modulo.strip().upper(),
                detalle=detalle,
                ip=ip,
                fechahora=fecha_efectiva,
                datosprevios=previos_str,
                datosnuevos=nuevos_str
            )
            db.add(registro)
            db.commit()
            db.refresh(registro)
            return registro
        except Exception as e:
            db.rollback()
            print(f"[AUDIT WARN] Error al registrar evento en bitácora: {e}")
            return None

    @classmethod
    def registrar_accion(
        cls,
        db: Session,
        usuario_id: Optional[int],
        accion: str,
        detalle: Optional[str] = None,
        modulo: str = "INVENTARIO",
        ip_origen: Optional[str] = None,
        tenant_id: int = 1,
        datos_previos: Optional[Any] = None,
        datos_nuevos: Optional[Any] = None,
    ) -> Optional[BitacoraModel]:
        """Alias simplificado para registrar acciones auditadas por módulo"""
        return cls.registrar_evento(
            db=db,
            accion=accion,
            modulo=modulo,
            usuario_id=usuario_id,
            detalle=detalle,
            ip=ip_origen,
            datos_previos=datos_previos,
            datos_nuevos=datos_nuevos,
            tenant_id=tenant_id,
        )

    @classmethod
    def consultar_bitacora(
        cls,
        db: Session,
        tenant_id: int = 1,
        usuario_id: Optional[int] = None,
        modulo: Optional[str] = None,
        accion: Optional[str] = None,
        limite: int = 50,
        pagina: int = 1
    ) -> Dict[str, Any]:
        """Consulta directa de bitácora para interoperabilidad y auditoría interna"""
        offset = max(0, (pagina - 1) * limite)
        return cls.listar(
            db=db,
            modulo=modulo,
            accion=accion,
            usuario_id=usuario_id,
            limit=limite,
            offset=offset,
            tenant_id=tenant_id
        )

    @staticmethod
    def listar(
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        modulo: Optional[str] = None,
        accion: Optional[str] = None,
        usuario_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Recupera eventos de bitácora con filtros combinados y paginación eficiente.
        """
        query = db.query(BitacoraModel).options(
            joinedload(BitacoraModel.usuario).joinedload(UsuarioModel.rol)
        )

        if tenant_id:
            query = query.filter(BitacoraModel.tenant_id == tenant_id)
        if fecha_inicio:
            query = query.filter(BitacoraModel.fechahora >= fecha_inicio)
        if fecha_fin:
            query = query.filter(BitacoraModel.fechahora <= fecha_fin)
        if modulo and modulo.upper() != "TODOS":
            query = query.filter(BitacoraModel.modulo == modulo.upper())
        if accion and accion.upper() != "TODAS":
            query = query.filter(BitacoraModel.accion == accion.upper())
        if usuario_id:
            query = query.filter(BitacoraModel.usuarioid == usuario_id)

        if search and search.strip():
            filtro_search = f"%{search.strip()}%"
            query = query.outerjoin(UsuarioModel, BitacoraModel.usuarioid == UsuarioModel.id).filter(
                or_(
                    BitacoraModel.detalle.ilike(filtro_search),
                    BitacoraModel.ip.ilike(filtro_search),
                    UsuarioModel.nombre.ilike(filtro_search),
                    UsuarioModel.apellido.ilike(filtro_search),
                    UsuarioModel.email.ilike(filtro_search)
                )
            )

        total = query.count()
        registros = query.order_by(desc(BitacoraModel.fechahora)).offset(offset).limit(limit).all()

        items = []
        for r in registros:
            user_info = None
            if r.usuario:
                user_info = {
                    "id": r.usuario.id,
                    "nombre": r.usuario.nombre,
                    "apellido": r.usuario.apellido,
                    "email": r.usuario.email,
                    "rol_nombre": r.usuario.rol.nombre if r.usuario.rol else "SIN ROL"
                }

            items.append({
                "id": r.id,
                "usuarioid": r.usuarioid,
                "accion": r.accion,
                "modulo": r.modulo,
                "detalle": r.detalle,
                "ip": r.ip,
                "fechahora": r.fechahora,
                "datosprevios": r.datosprevios,
                "datosnuevos": r.datosnuevos,
                "usuario": user_info
            })

        return {
            "total": total,
            "items": items,
            "limit": limit,
            "offset": offset
        }

    @staticmethod
    def obtener_estadisticas(db: Session, tenant_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calcula indicadores clave de seguridad y actividad para la cabecera del módulo.
        Si tenant_id es None (vista SUPERADMIN), calcula las métricas globales de toda la plataforma.
        """
        ahora = get_bolivia_now()
        inicio_hoy = datetime(ahora.year, ahora.month, ahora.day)
        hace_7_dias = ahora - timedelta(days=7)
        hace_30_dias = ahora - timedelta(days=30)

        q_hoy = db.query(func.count(BitacoraModel.id)).filter(BitacoraModel.fechahora >= inicio_hoy)
        q_sem = db.query(func.count(BitacoraModel.id)).filter(BitacoraModel.fechahora >= hace_7_dias)
        q_mes = db.query(func.count(BitacoraModel.id)).filter(BitacoraModel.fechahora >= hace_30_dias)
        q_mod = db.query(BitacoraModel.modulo, func.count(BitacoraModel.id)).filter(BitacoraModel.fechahora >= hace_30_dias)
        q_acc = db.query(BitacoraModel.accion, func.count(BitacoraModel.id)).filter(BitacoraModel.fechahora >= hace_30_dias)

        if tenant_id is not None:
            q_hoy = q_hoy.filter(BitacoraModel.tenant_id == tenant_id)
            q_sem = q_sem.filter(BitacoraModel.tenant_id == tenant_id)
            q_mes = q_mes.filter(BitacoraModel.tenant_id == tenant_id)
            q_mod = q_mod.filter(BitacoraModel.tenant_id == tenant_id)
            q_acc = q_acc.filter(BitacoraModel.tenant_id == tenant_id)

        total_hoy = q_hoy.scalar() or 0
        total_semana = q_sem.scalar() or 0
        total_mes = q_mes.scalar() or 0
        modulos_dist = {row[0]: row[1] for row in q_mod.group_by(BitacoraModel.modulo).all()}
        acciones_dist = {row[0]: row[1] for row in q_acc.group_by(BitacoraModel.accion).all()}

        return {
            "total_hoy": total_hoy,
            "total_semana": total_semana,
            "total_mes": total_mes,
            "modulos_distribucion": modulos_dist,
            "acciones_distribucion": acciones_dist
        }

    @staticmethod
    def exportar_csv(
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        modulo: Optional[str] = None,
        accion: Optional[str] = None,
        usuario_id: Optional[int] = None,
        search: Optional[str] = None,
        tenant_id: Optional[int] = None
    ) -> str:
        """
        Genera el contenido CSV delimitado por comas con encoding compatible para Excel.
        """
        resultado = BitacoraController.listar(
            db=db,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            modulo=modulo,
            accion=accion,
            usuario_id=usuario_id,
            search=search,
            limit=5000,
            offset=0,
            tenant_id=tenant_id
        )

        output = io.StringIO()
        output.write("\ufeff")

        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "ID",
            "Fecha y Hora (Hora Bolivia - BOT)",
            "Módulo",
            "Acción",
            "Usuario",
            "Email",
            "Rol",
            "IP Origen",
            "Detalle del Evento"
        ])

        for item in resultado["items"]:
            user = item["usuario"]
            nom_usuario = f"{user['nombre']} {user.get('apellido') or ''}".strip() if user else "Sistema / Anónimo"
            email_usuario = user["email"] if user else "N/A"
            rol_usuario = user["rol_nombre"] if user else "N/A"

            writer.writerow([
                item["id"],
                item["fechahora"].strftime("%Y-%m-%d %H:%M:%S") if item["fechahora"] else "",
                item["modulo"],
                item["accion"],
                nom_usuario,
                email_usuario,
                rol_usuario,
                item.get("ip") or "Localhost",
                item.get("detalle") or ""
            ])

        return output.getvalue()
