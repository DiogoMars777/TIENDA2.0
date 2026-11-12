# ==============================================================================
# CU19 - GESTIONAR NOTIFICACIONES -> SERVICIO (MVC - SERVICE LAYER)
# Ubicación: backend/app/services/cu19_gestionar_notificaciones/notificacion_service.py
# ==============================================================================

from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.models.cu19_gestionar_notificaciones.notificacion_model import NotificacionModel
from app.models.cu10_gestionar_reservas_prendas.reserva_model import ReservaModel
from app.models.cu13_gestionar_inventario_movimientos.inventario_model import InventarioModel
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.models.cu3_gestionar_clientes.cliente_model import ClienteModel
from app.core.timezone import get_bolivia_now


class NotificacionService:

    @staticmethod
    def crear_notificacion(
        db: Session,
        titulo: str,
        mensaje: str,
        tipo: str = "INFO",
        usuario_id: Optional[int] = None,
        enlace: Optional[str] = None,
        tenant_id: int = 1
    ) -> NotificacionModel:
        """Helper para registrar una notificación en el sistema con soporte multi-inquilino."""
        notif = NotificacionModel(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            enlace=enlace,
            leido=False,
            fecha_creacion=get_bolivia_now()
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def _verificar_alertas_automaticas(
        db: Session,
        current_user: UsuarioModel,
        tenant_id: int = 1
    ) -> None:
        """Genera notificaciones proactivas según eventos del negocio (expiración de reservas, stock bajo)."""
        ahora = get_bolivia_now()

        # 1. Alertas de reservas próximas a vencer (< 6 horas antes de 48h)
        cliente = db.query(ClienteModel).filter(
            ClienteModel.usuarioid == current_user.id,
            ClienteModel.tenant_id == tenant_id
        ).first()

        if not cliente:
            cliente = db.query(ClienteModel).filter(ClienteModel.usuarioid == current_user.id).first()

        if cliente:
            reservas_pendientes = db.query(ReservaModel).filter(
                ReservaModel.clienteid == cliente.id,
                ReservaModel.tenant_id == tenant_id,
                ReservaModel.estado.in_(["Pendiente", "PENDIENTE", "Confirmada", "CONFIRMADA"])
            ).all()

            for res in reservas_pendientes:
                fecha_res = res.fechareserva or ahora
                fecha_limite = fecha_res + timedelta(hours=48)
                diff_horas = (fecha_limite - ahora).total_seconds() / 3600.0

                if 0 < diff_horas <= 12.0:
                    ya_existe = db.query(NotificacionModel).filter(
                        NotificacionModel.tenant_id == tenant_id,
                        NotificacionModel.usuario_id == current_user.id,
                        NotificacionModel.tipo == "RESERVA_EXPIRANDO",
                        NotificacionModel.mensaje.ilike(f"%{res.codigoreserva}%")
                    ).first()

                    if not ya_existe:
                        horas_display = max(1, round(diff_horas))
                        notif = NotificacionModel(
                            tenant_id=tenant_id,
                            usuario_id=current_user.id,
                            titulo=f"⏱️ Reserva {res.codigoreserva} por expirar",
                            mensaje=f"Te quedan menos de {horas_display} horas para retirar tu reserva de poleras en sucursal antes de su cancelación automática.",
                            tipo="RESERVA_EXPIRANDO",
                            enlace="/historial",
                            fecha_creacion=ahora
                        )
                        db.add(notif)

        # 2. Alertas de inventario crítico (para administradores / staff)
        rol_nombre = getattr(current_user.rol, 'nombre', '').upper() if getattr(current_user, 'rol', None) else ''
        if any(r in rol_nombre for r in ["ADMIN", "GERENTE", "INVENTARIO", "ENCARGADO"]):
            items_criticos = db.query(InventarioModel).filter(
                InventarioModel.tenant_id == tenant_id,
                InventarioModel.stockfisico <= InventarioModel.stockminimo
            ).limit(3).all()

            for item in items_criticos:
                ya_existe_stock = db.query(NotificacionModel).filter(
                    NotificacionModel.tenant_id == tenant_id,
                    NotificacionModel.usuario_id == current_user.id,
                    NotificacionModel.tipo == "STOCK_CRITICO",
                    NotificacionModel.mensaje.ilike(f"%variante #{item.varianteid}%")
                ).first()

                if not ya_existe_stock:
                    notif = NotificacionModel(
                        tenant_id=tenant_id,
                        usuario_id=current_user.id,
                        titulo="⚠️ Alerta de Inventario Crítico",
                        mensaje=f"La variante #{item.varianteid} tiene stock de {item.stockfisico} unidades (mínimo: {item.stockminimo}). Requiere reabastecimiento.",
                        tipo="STOCK_CRITICO",
                        enlace="/inventario",
                        fecha_creacion=ahora
                    )
                    db.add(notif)

        try:
            db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def listar_notificaciones(
        db: Session,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """CU19: Retorna lista de notificaciones activas para el usuario conectado."""
        tenant_id = tenant_id or current_user.tenant_id or 1
        NotificacionService._verificar_alertas_automaticas(db, current_user, tenant_id=tenant_id)

        notificaciones = db.query(NotificacionModel).filter(
            NotificacionModel.tenant_id == tenant_id,
            or_(
                NotificacionModel.usuario_id == current_user.id,
                NotificacionModel.usuario_id.is_(None)
            )
        ).order_by(NotificacionModel.id.desc()).limit(30).all()

        return [
            {
                "id": n.id,
                "titulo": n.titulo,
                "mensaje": n.mensaje,
                "tipo": n.tipo,
                "leido": n.leido,
                "enlace": n.enlace,
                "fecha": n.fecha_creacion.strftime("%d/%m/%Y %H:%M") if n.fecha_creacion else ""
            }
            for n in notificaciones
        ]

    @staticmethod
    def contar_no_leidas(
        db: Session,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> int:
        """CU19: Retorna la cantidad de notificaciones pendientes de lectura."""
        tenant_id = tenant_id or current_user.tenant_id or 1
        return db.query(NotificacionModel).filter(
            NotificacionModel.tenant_id == tenant_id,
            or_(
                NotificacionModel.usuario_id == current_user.id,
                NotificacionModel.usuario_id.is_(None)
            ),
            NotificacionModel.leido == False
        ).count()

    @staticmethod
    def marcar_como_leida(
        db: Session,
        current_user: UsuarioModel,
        notificacion_id: int,
        tenant_id: Optional[int] = None
    ) -> bool:
        """CU19: Marca una notificación específica como leída."""
        tenant_id = tenant_id or current_user.tenant_id or 1
        notif = db.query(NotificacionModel).filter(
            NotificacionModel.id == notificacion_id,
            NotificacionModel.tenant_id == tenant_id,
            or_(
                NotificacionModel.usuario_id == current_user.id,
                NotificacionModel.usuario_id.is_(None)
            )
        ).first()

        if notif:
            notif.leido = True
            db.commit()
            return True
        return False

    @staticmethod
    def marcar_todas_leidas(
        db: Session,
        current_user: UsuarioModel,
        tenant_id: Optional[int] = None
    ) -> bool:
        """CU19: Marca todas las notificaciones pendientes del usuario como leídas."""
        tenant_id = tenant_id or current_user.tenant_id or 1
        db.query(NotificacionModel).filter(
            NotificacionModel.tenant_id == tenant_id,
            or_(
                NotificacionModel.usuario_id == current_user.id,
                NotificacionModel.usuario_id.is_(None)
            ),
            NotificacionModel.leido == False
        ).update({"leido": True}, synchronize_session=False)

        db.commit()
        return True
