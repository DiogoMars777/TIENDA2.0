# ==============================================================================
# CU27 - DASHBOARD EJECUTIVO Y REPORTES -> MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu27_dashboard_ejecutivo/dashboard_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Boolean
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class MetricaDashboard(Base):
    """
    Entidad opcional para consolidación y snapshot de métricas del dashboard ejecutivo.
    """
    __tablename__ = "dashboard_metrica_snapshot"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1, index=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id", ondelete="SET NULL"), nullable=True)
    total_ventas = Column(Numeric(14, 2), default=0.0)
    total_pedidos = Column(Integer, default=0)
    total_reservas_activas = Column(Integer, default=0)
    total_clientes_nuevos = Column(Integer, default=0)
    fecha_corte = Column(DateTime, default=get_bolivia_now, index=True)


DashboardMetricaModel = MetricaDashboard
dashboard_metrica = MetricaDashboard
