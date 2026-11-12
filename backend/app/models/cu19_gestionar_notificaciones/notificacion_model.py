# ==============================================================================
# CU19 - GESTIONAR NOTIFICACIONES -> CAPA MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu19_gestionar_notificaciones/notificacion_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class Notificacion(Base):
    __tablename__ = "notificacion"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=True, index=True)
    titulo = Column(String(150), nullable=False)
    mensaje = Column(Text, nullable=False)
    tipo = Column(String(50), default="INFO")  # RESERVA_EXPIRANDO, PAGO_EXITOSO, STOCK_CRITICO, INFO
    leido = Column(Boolean, default=False)
    enlace = Column(String(255), nullable=True)
    fecha_creacion = Column(DateTime, default=get_bolivia_now)


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
NotificacionModel = Notificacion
notificacion = Notificacion
