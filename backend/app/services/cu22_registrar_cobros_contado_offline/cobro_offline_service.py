# ==============================================================================
# CU22 - REGISTRAR COBROS DE CONTADO SIN CONEXIÓN -> SERVICIO (MVC - SERVICE)
# Ubicación: backend/app/services/cu22_registrar_cobros_contado_offline/cobro_offline_service.py
# ==============================================================================

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import json
import uuid

from app.models.cu22_registrar_cobros_contado_offline.cobro_offline_model import CobroOffline
from app.models.cu4_gestionar_sucursales.sucursal_model import SucursalModel
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.controllers.cu26_gestionar_bitacora.bitacora_controller import BitacoraController
from app.schemas.cu22_registrar_cobros_contado_offline.cobro_offline_schema import (
    CobroOfflineCreate, ItemCobroOffline
)
from app.core.timezone import get_bolivia_now, to_bolivia_time


class CobroOfflineService:
    """
    Servicio de Contingencia y Cobro de Contado Offline (CU22).
    Permite registrar pagos en efectivo cuando la tienda/POS pierde conexión a Internet,
    generando folios provisionales inmutables y trazabilidad de caja auditada.
    """

    @staticmethod
    def _parsear_payload_observaciones(cobro: CobroOffline) -> Dict[str, Any]:
        """Extrae el desglose de prendas y datos de cambio desde las observaciones JSON."""
        res = {
            "items": [],
            "efectivo_recibido": None,
            "cambio": None,
            "nota": cobro.observaciones or ""
        }
        if not cobro.observaciones:
            return res

        try:
            parsed = json.loads(cobro.observaciones)
            if isinstance(parsed, dict) and "items" in parsed:
                res["items"] = parsed.get("items", [])
                res["efectivo_recibido"] = parsed.get("efectivo_recibido")
                res["cambio"] = parsed.get("cambio")
                res["nota"] = parsed.get("nota", "")
        except Exception:
            res["nota"] = cobro.observaciones

        return res

    @staticmethod
    def _enriquecer_cobro(db: Session, cobro: CobroOffline) -> Dict[str, Any]:
        """Agrega nombres de sucursal, cajero y desglose de items al cobro offline."""
        sucursal = db.query(SucursalModel).filter(SucursalModel.id == cobro.sucursal_id).first()
        cajero = db.query(UsuarioModel).filter(UsuarioModel.id == cobro.cajero_id).first() if cobro.cajero_id else None
        desglose = CobroOfflineService._parsear_payload_observaciones(cobro)

        return {
            "id": cobro.id,
            "tenant_id": cobro.tenant_id,
            "cajero_id": cobro.cajero_id,
            "cajero_nombre": f"{cajero.nombre} {cajero.apellido or ''}".strip() if cajero else "Cajero Contingencia",
            "sucursal_id": cobro.sucursal_id,
            "sucursal_nombre": sucursal.nombre if sucursal else f"Sucursal #{cobro.sucursal_id}",
            "monto": float(cobro.monto),
            "moneda": cobro.moneda or "BOB",
            "nro_recibo_provisional": cobro.nro_recibo_provisional,
            "uuid_operacion": cobro.uuid_operacion,
            "cliente_nombre": cobro.cliente_nombre or "Cliente Ocasional",
            "cliente_nit": cobro.cliente_nit or "0",
            "observaciones": desglose["nota"],
            "fecha_cobro": cobro.fecha_cobro,
            "sincronizado": cobro.sincronizado,
            "fecha_sincronizacion": cobro.fecha_sincronizacion,
            "venta_id": cobro.venta_id,
            "items": desglose["items"],
            "efectivo_recibido": desglose["efectivo_recibido"],
            "cambio": desglose["cambio"]
        }

    @staticmethod
    def registrar_cobro_offline(
        db: Session,
        tenant_id: int,
        cajero_id: Optional[int],
        data: CobroOfflineCreate
    ) -> Dict[str, Any]:
        """
        Registra un cobro en efectivo generado en modo contingencia offline con protección de idempotencia.
        """
        op_uuid = data.uuid_operacion or str(uuid.uuid4())

        # 1. Verificar idempotencia por UUID
        existente = db.query(CobroOffline).filter(
            CobroOffline.tenant_id == tenant_id,
            CobroOffline.uuid_operacion == op_uuid
        ).first()
        if existente:
            return CobroOfflineService._enriquecer_cobro(db, existente)

        # 2. Empaquetar desglose de items y cambio en estructura JSON
        payload_items = [item.dict() for item in data.items] if data.items else []
        obs_dict = {
            "nota": data.observaciones or "",
            "items": payload_items,
            "efectivo_recibido": float(data.efectivo_recibido) if data.efectivo_recibido is not None else None,
            "cambio": float(data.cambio) if data.cambio is not None else None
        }
        obs_json = json.dumps(obs_dict, ensure_ascii=False, default=str)

        # 3. Validar folio provisional único
        folio = data.nro_recibo_provisional.strip().upper()
        folio_existente = db.query(CobroOffline).filter(
            CobroOffline.tenant_id == tenant_id,
            CobroOffline.nro_recibo_provisional == folio
        ).first()
        if folio_existente:
            folio = f"{folio}-{str(uuid.uuid4())[:4].upper()}"

        fecha_efectiva = to_bolivia_time(getattr(data, "fecha_cobro", None)) or get_bolivia_now()

        nuevo_cobro = CobroOffline(
            tenant_id=tenant_id,
            cajero_id=cajero_id,
            sucursal_id=data.sucursal_id,
            monto=data.monto,
            moneda=data.moneda or "BOB",
            nro_recibo_provisional=folio,
            uuid_operacion=op_uuid,
            cliente_nombre=data.cliente_nombre.strip() if data.cliente_nombre else "Cliente Ocasional",
            cliente_nit=data.cliente_nit.strip() if data.cliente_nit else "0",
            observaciones=obs_json,
            fecha_cobro=fecha_efectiva,
            sincronizado=False
        )
        db.add(nuevo_cobro)
        db.commit()
        db.refresh(nuevo_cobro)

        # 4. Auditoría en Bitácora (CU26)
        BitacoraController.registrar_evento(
            db=db,
            accion="CREAR",
            modulo="COBROS_OFFLINE",
            usuario_id=cajero_id,
            detalle=f"Cobro contado offline registrado: Recibo {nuevo_cobro.nro_recibo_provisional} por Bs. {nuevo_cobro.monto} en Sucursal #{nuevo_cobro.sucursal_id}.",
            datos_nuevos={
                "recibo": nuevo_cobro.nro_recibo_provisional,
                "monto": float(nuevo_cobro.monto),
                "cliente": nuevo_cobro.cliente_nombre,
                "sucursal_id": nuevo_cobro.sucursal_id,
                "items_count": len(payload_items)
            },
            tenant_id=tenant_id
        )

        return CobroOfflineService._enriquecer_cobro(db, nuevo_cobro)

    @staticmethod
    def listar_cobros(
        db: Session,
        tenant_id: int,
        sucursal_id: Optional[int] = None,
        solo_pendientes: bool = False
    ) -> List[Dict[str, Any]]:
        """Retorna la lista de cobros offline registrados con todos sus detalles para la vista."""
        query = db.query(CobroOffline).filter(CobroOffline.tenant_id == tenant_id)
        if sucursal_id:
            query = query.filter(CobroOffline.sucursal_id == sucursal_id)
        if solo_pendientes:
            query = query.filter(CobroOffline.sincronizado == False)

        cobros = query.order_by(desc(CobroOffline.id)).all()
        return [CobroOfflineService._enriquecer_cobro(db, c) for c in cobros]

    @staticmethod
    def listar_pendientes(db: Session, tenant_id: int, sucursal_id: Optional[int] = None) -> List[CobroOffline]:
        """Método de compatibilidad para consultas directas de pendientes."""
        q = db.query(CobroOffline).filter(
            CobroOffline.tenant_id == tenant_id,
            CobroOffline.sincronizado == False
        )
        if sucursal_id:
            q = q.filter(CobroOffline.sucursal_id == sucursal_id)
        return q.order_by(desc(CobroOffline.id)).all()

    @staticmethod
    def obtener_cobro_por_id(db: Session, cobro_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un cobro offline específico para impresión de ticket térmico de contingencia."""
        cobro = db.query(CobroOffline).filter(
            CobroOffline.id == cobro_id,
            CobroOffline.tenant_id == tenant_id
        ).first()
        if not cobro:
            return None
        return CobroOfflineService._enriquecer_cobro(db, cobro)

    @staticmethod
    def registrar_lote_offline(
        db: Session,
        tenant_id: int,
        cajero_id: Optional[int],
        lote: List[CobroOfflineCreate]
    ) -> List[Dict[str, Any]]:
        """Registra un lote de cobros acumulados en el navegador."""
        resultados = []
        for item in lote:
            res = CobroOfflineService.registrar_cobro_offline(db, tenant_id, cajero_id, item)
            resultados.append(res)
        return resultados

    @staticmethod
    def obtener_kpis(db: Session, tenant_id: int, sucursal_id: Optional[int] = None) -> Dict[str, Any]:
        """Calcula métricas clave de recaudación en contingencia para el dashboard de caja."""
        query = db.query(CobroOffline).filter(CobroOffline.tenant_id == tenant_id)
        if sucursal_id:
            query = query.filter(CobroOffline.sucursal_id == sucursal_id)

        todos = query.all()
        total_cobros = len(todos)
        monto_total = sum([float(c.monto) for c in todos])

        pendientes = [c for c in todos if not c.sincronizado]
        pendientes_count = len(pendientes)
        monto_pendiente = sum([float(c.monto) for c in pendientes])

        sincronizados = [c for c in todos if c.sincronizado]
        sincronizados_count = len(sincronizados)
        monto_sincronizado = sum([float(c.monto) for c in sincronizados])

        return {
            "total_cobros": total_cobros,
            "monto_total_offline": round(monto_total, 2),
            "pendientes_sync": pendientes_count,
            "monto_pendiente": round(monto_pendiente, 2),
            "sincronizados": sincronizados_count,
            "monto_sincronizado": round(monto_sincronizado, 2),
            "sucursal_activa_id": sucursal_id
        }

    @staticmethod
    def marcar_sincronizado(db: Session, cobro_id: int, venta_id: Optional[int] = None) -> Optional[CobroOffline]:
        """Marca un cobro offline como sincronizado al consolidarse en una Venta (CU23)."""
        cobro = db.query(CobroOffline).filter(CobroOffline.id == cobro_id).first()
        if not cobro:
            return None
        cobro.sincronizado = True
        cobro.fecha_sincronizacion = get_bolivia_now()
        if venta_id:
            cobro.venta_id = venta_id
        db.commit()
        db.refresh(cobro)
        return cobro
