# ==============================================================================
# CU20 - GENERAR REPORTES GENERATIVOS CON IA -> CAPA MODELO (MVC - MODEL)
# Ubicación: backend/app/models/cu20_generar_reportes_generativos_ia/reporte_generativo_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now


class ReporteGenerativoIA(Base):
    """
    Entidad de persistencia para consultas analíticas generadas mediante
    procesamiento de lenguaje natural (Gemini AI) y exportación de reportes.
    """
    __tablename__ = "reporte_generativo_ia"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    prompt_consulta = Column(Text, nullable=False)
    titulo_reporte = Column(String(200), nullable=False)
    resumen_ejecutivo = Column(Text, nullable=False)
    datos_resultado_json = Column(Text, nullable=True)
    tipo_grafico_sugerido = Column(String(50), default="BAR")  # BAR, LINE, PIE, KPIS
    filtros_aplicados = Column(String(255), nullable=True)
    modelo_ia_utilizado = Column(String(100), default="Google Gemini 2.0 Flash")
    es_favorito = Column(Boolean, default=False)
    fecha_generacion = Column(DateTime, default=get_bolivia_now, index=True)


ReporteGenerativoModel = ReporteGenerativoIA
ReporteGenerativo = ReporteGenerativoIA
reporte_generativo = ReporteGenerativoIA
