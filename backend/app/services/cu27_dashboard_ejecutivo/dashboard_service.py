# ==============================================================================
# CU27 - DASHBOARD EJECUTIVO Y REPORTES -> SERVICIO (MVC - SERVICE)
# Ubicación: backend/app/services/cu27_dashboard_ejecutivo/dashboard_service.py
# ==============================================================================

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import io
import csv

from app.models.cu14_registrar_ventas_presenciales.venta_presencial_model import (
    VentaModel, DetalleVentaModel, PagoModel, MetodoPagoModel
)
from app.models.cu10_gestionar_reservas_prendas.reserva_model import ReservaModel
from app.models.cu13_gestionar_inventario_movimientos.inventario_model import InventarioModel
from app.models.cu5_gestionar_productos.producto_model import ProductoModel, VarianteProductoModel
from app.models.cu4_gestionar_sucursales.sucursal_model import SucursalModel
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import UsuarioModel
from app.models.saas_tenant.tenant_model import TenantModel, PlanSuscripcionModel, TenantConfiguracionModel
from app.models.cu25_gestionar_cambios_devoluciones.devolucion_model import DevolucionModel
from app.models.cu23_sincronizar_operaciones_offline.sincronizacion_offline_model import OperacionOfflineSyncModel
from app.core.timezone import get_bolivia_now


class DashboardService:
    """
    Servicio Ejecutivo Senior para consolidación de métricas financieras, 
    omnicanalidad, operaciones de contingencia y analítica multi-tenant SaaS.
    """

    @staticmethod
    def _calcular_rango_fechas(dias: Optional[int]) -> Optional[datetime]:
        if dias and dias > 0:
            return get_bolivia_now() - timedelta(days=dias)
        return None

    @classmethod
    def obtener_kpis(cls, db: Session, dias: Optional[int] = None, tenant_id: int = 1) -> Dict[str, Any]:
        """
        Calcula los KPIs primarios y secundarios para el C-Level del Tenant.
        """
        tenant_id = tenant_id or 1
        query_ventas = db.query(VentaModel).filter(
            VentaModel.tenant_id == tenant_id,
            VentaModel.estado.ilike("%Completad%")
        )

        fecha_limite = cls._calcular_rango_fechas(dias)
        if fecha_limite:
            query_ventas = query_ventas.filter(VentaModel.fecha >= fecha_limite)

        ventas = query_ventas.all()
        total_ingresos = sum([float(v.total or 0) for v in ventas])
        total_transacciones = len(ventas)
        ticket_promedio = (total_ingresos / total_transacciones) if total_transacciones > 0 else 0.0

        # Prendas vendidas en el periodo
        venta_ids = [v.id for v in ventas]
        prendas_vendidas = 0
        if venta_ids:
            res_cant = db.query(func.sum(DetalleVentaModel.cantidad)).filter(
                DetalleVentaModel.ventaid.in_(venta_ids)
            ).scalar()
            prendas_vendidas = int(res_cant or 0)

        # Reservas activas (independientes del filtro de tiempo)
        reservas_activas = db.query(ReservaModel).filter(
            ReservaModel.tenant_id == tenant_id,
            ReservaModel.estado.in_(["Pendiente", "PENDIENTE", "Confirmada", "CONFIRMADA"])
        ).count()

        # Stock físico total y stock crítico
        stock_total = db.query(func.sum(InventarioModel.stockfisico)).filter(
            InventarioModel.tenant_id == tenant_id
        ).scalar() or 0

        stock_critico = db.query(InventarioModel).filter(
            InventarioModel.tenant_id == tenant_id,
            InventarioModel.stockfisico <= InventarioModel.stockminimo
        ).count()

        # Devoluciones / Cambios (CU25)
        query_devs = db.query(DevolucionModel).filter(DevolucionModel.tenant_id == tenant_id)
        if fecha_limite:
            query_devs = query_devs.filter(DevolucionModel.fecha_solicitud >= fecha_limite)
        devoluciones = query_devs.all()
        total_devoluciones = len(devoluciones)
        monto_devoluciones = sum([float(d.monto_reembolso or 0) for d in devoluciones])
        ingresos_netos = max(0.0, total_ingresos - monto_devoluciones)

        # Operaciones sincronizadas de contingencia offline (CU23)
        query_sync = db.query(OperacionOfflineSyncModel).filter(
            OperacionOfflineSyncModel.tenant_id == tenant_id,
            OperacionOfflineSyncModel.estado == "SINCRONIZADO"
        )
        if fecha_limite:
            query_sync = query_sync.filter(OperacionOfflineSyncModel.fecha_recibido >= fecha_limite)
        operaciones_offline = query_sync.count()

        return {
            "total_ingresos_bs": round(total_ingresos, 2),
            "ingresos_totales": round(total_ingresos, 2),
            "ingresos_netos_bs": round(ingresos_netos, 2),
            "total_transacciones": total_transacciones,
            "ticket_promedio_bs": round(ticket_promedio, 2),
            "prendas_vendidas": prendas_vendidas,
            "reservas_activas": reservas_activas,
            "stock_total_fisico": int(stock_total),
            "articulos_stock_critico": stock_critico,
            "total_devoluciones": total_devoluciones,
            "monto_devoluciones_bs": round(monto_devoluciones, 2),
            "operaciones_offline_sincronizadas": operaciones_offline,
            "fecha_calculo": get_bolivia_now().strftime("%d/%m/%Y %H:%M:%S")
        }

    @classmethod
    def obtener_ventas_sucursal(cls, db: Session, dias: Optional[int] = None, tenant_id: int = 1) -> List[Dict[str, Any]]:
        """
        Retorna la comparativa y participación (%) de ingresos por sucursal física.
        """
        tenant_id = tenant_id or 1
        query_suc = db.query(SucursalModel).filter(SucursalModel.activo == True)
        if hasattr(SucursalModel, 'tenant_id'):
            query_suc = query_suc.filter(SucursalModel.tenant_id == tenant_id)

        sucursales = query_suc.all()
        fecha_limite = cls._calcular_rango_fechas(dias)

        resultado = []
        total_general = 0.0

        for suc in sucursales:
            q = db.query(VentaModel).filter(
                VentaModel.tenant_id == tenant_id,
                VentaModel.sucursalid == suc.id,
                VentaModel.estado.ilike("%Completad%")
            )
            if fecha_limite:
                q = q.filter(VentaModel.fecha >= fecha_limite)
            ventas_suc = q.all()

            total_monto = sum([float(v.total or 0) for v in ventas_suc])
            total_general += total_monto

            resultado.append({
                "sucursal_id": suc.id,
                "sucursal_nombre": suc.nombre,
                "ciudad": suc.ciudad or "Santa Cruz",
                "total_bs": round(total_monto, 2),
                "transacciones": len(ventas_suc),
                "porcentaje": 0.0
            })

        for item in resultado:
            if total_general > 0:
                item["porcentaje"] = round((item["total_bs"] / total_general) * 100, 1)

        return sorted(resultado, key=lambda x: x["total_bs"], reverse=True)

    @classmethod
    def obtener_ventas_canal(cls, db: Session, dias: Optional[int] = None, tenant_id: int = 1) -> List[Dict[str, Any]]:
        """
        Retorna la distribución omnicanal: Presencial POS, Digital E-commerce y Contingencia Offline.
        """
        tenant_id = tenant_id or 1
        fecha_limite = cls._calcular_rango_fechas(dias)

        canales_def = [
            ("Presencial", "Presencial (Boutique POS)"),
            ("Digital", "Digital (E-commerce Web/App)"),
            ("Offline", "Offline (Contingencia Sincronizada)")
        ]

        resultado = []
        total_global = 0.0

        for key, label in canales_def:
            q = db.query(VentaModel).filter(
                VentaModel.tenant_id == tenant_id,
                VentaModel.tipoventa.ilike(f"%{key}%"),
                VentaModel.estado.ilike("%Completad%")
            )
            if fecha_limite:
                q = q.filter(VentaModel.fecha >= fecha_limite)
            ventas_canal = q.all()

            total_monto = sum([float(v.total or 0) for v in ventas_canal])
            total_global += total_monto
            resultado.append({
                "canal": label,
                "total_bs": round(total_monto, 2),
                "transacciones": len(ventas_canal),
                "porcentaje": 0.0
            })

        for item in resultado:
            if total_global > 0:
                item["porcentaje"] = round((item["total_bs"] / total_global) * 100, 1)

        return resultado

    @classmethod
    def obtener_ventas_metodo_pago(cls, db: Session, dias: Optional[int] = None, tenant_id: int = 1) -> List[Dict[str, Any]]:
        """
        Retorna la participación de pagos por pasarelas (QR, Efectivo, Tarjeta, PayPal).
        """
        tenant_id = tenant_id or 1
        metodos = db.query(MetodoPagoModel).all()
        fecha_limite = cls._calcular_rango_fechas(dias)

        resultado = []
        total_recaudado = 0.0

        for m in metodos:
            q = db.query(PagoModel).join(VentaModel, PagoModel.ventaid == VentaModel.id).filter(
                VentaModel.tenant_id == tenant_id,
                PagoModel.metodoid == m.id,
                PagoModel.estado.ilike("%Aprobad%")
            )
            if fecha_limite:
                q = q.filter(PagoModel.fecha >= fecha_limite)
            pagos = q.all()

            total_monto = sum([float(p.monto or 0) for p in pagos])
            total_recaudado += total_monto

            resultado.append({
                "metodo_id": m.id,
                "metodo_nombre": m.nombre,
                "total_bs": round(total_monto, 2),
                "cantidad_pagos": len(pagos),
                "porcentaje": 0.0
            })

        for item in resultado:
            if total_recaudado > 0:
                item["porcentaje"] = round((item["total_bs"] / total_recaudado) * 100, 1)

        return sorted(resultado, key=lambda x: x["total_bs"], reverse=True)

    @classmethod
    def obtener_top_productos(cls, db: Session, limite: int = 5, dias: Optional[int] = None, tenant_id: int = 1) -> List[Dict[str, Any]]:
        """
        Ranking de prendas boutique más vendidas y recaudación generada.
        """
        tenant_id = tenant_id or 1
        fecha_limite = cls._calcular_rango_fechas(dias)

        query = db.query(
            DetalleVentaModel.varianteid,
            func.sum(DetalleVentaModel.cantidad).label("unidades_vendidas"),
            func.sum(DetalleVentaModel.subtotal).label("recaudacion_total")
        ).join(VentaModel, DetalleVentaModel.ventaid == VentaModel.id).filter(
            VentaModel.tenant_id == tenant_id,
            VentaModel.estado.ilike("%Completad%")
        )

        if fecha_limite:
            query = query.filter(VentaModel.fecha >= fecha_limite)

        top_items = query.group_by(DetalleVentaModel.varianteid).order_by(
            func.sum(DetalleVentaModel.cantidad).desc()
        ).limit(limite).all()

        resultado = []
        for item in top_items:
            variante = db.query(VarianteProductoModel).filter(VarianteProductoModel.id == item.varianteid).first()
            nombre = "Prenda Boutique"
            sku = "SKU-GENERICO"
            precio = 100.0

            if variante:
                sku = variante.sku or sku
                prod = db.query(ProductoModel).filter(ProductoModel.id == variante.productoid).first()
                if prod:
                    nombre = prod.nombre
                    precio = float(prod.preciobase or 100.0)

            resultado.append({
                "variante_id": item.varianteid,
                "sku": sku,
                "nombre_producto": nombre,
                "precio_unitario": precio,
                "unidades_vendidas": int(item.unidades_vendidas or 0),
                "recaudacion_bs": round(float(item.recaudacion_total or 0), 2)
            })

        return resultado

    @classmethod
    def obtener_resumen_saas_tenant(cls, db: Session, tenant_id: int = 1) -> Dict[str, Any]:
        """
        Calcula la utilización de recursos de la empresa SaaS actual vs los límites de su suscripción.
        """
        tenant_id = tenant_id or 1
        tenant_obj = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()

        tenant_nombre = tenant_obj.nombre if tenant_obj else "Shopyn Golden Store"
        plan = tenant_obj.plan if (tenant_obj and tenant_obj.plan) else None

        plan_nombre = plan.nombre if plan else "Plan Boutique Enterprise"
        limite_sucursales = plan.limite_sucursales if plan else 10
        limite_usuarios = plan.limite_usuarios if plan else 50
        vestidor_ia = plan.habilitar_vestidor_ia if plan else True

        # Recursos activos
        query_suc = db.query(SucursalModel).filter(SucursalModel.activo == True)
        if hasattr(SucursalModel, 'tenant_id'):
            query_suc = query_suc.filter(SucursalModel.tenant_id == tenant_id)
        sucursales_activas = query_suc.count()

        query_usr = db.query(UsuarioModel).filter(UsuarioModel.activo == True)
        if hasattr(UsuarioModel, 'tenant_id'):
            query_usr = query_usr.filter(UsuarioModel.tenant_id == tenant_id)
        usuarios_activos = query_usr.count()

        # Configuración del tenant
        config = db.query(TenantConfiguracionModel).filter(TenantConfiguracionModel.tenant_id == tenant_id).first()
        moneda = config.moneda_simbolo if config else "Bs."

        return {
            "tenant_id": tenant_id,
            "tenant_nombre": tenant_nombre,
            "plan_nombre": plan_nombre,
            "sucursales_activas": sucursales_activas,
            "limite_sucursales": limite_sucursales,
            "usuarios_activos": usuarios_activos,
            "limite_usuarios": limite_usuarios,
            "vestidor_ia_habilitado": vestidor_ia,
            "suscripcion_estado": "ACTIVA",
            "moneda_simbolo": moneda
        }

    @classmethod
    def obtener_dashboard_completo(cls, db: Session, dias: Optional[int] = None, tenant_id: int = 1) -> Dict[str, Any]:
        """
        Retorna el payload consolidado completo para renderizado instantáneo del Dashboard Ejecutivo.
        """
        periodo_etiqueta = "HISTÓRICO_COMPLETO"
        if dias == 1:
            periodo_etiqueta = "HOY"
        elif dias == 7:
            periodo_etiqueta = "ÚLTIMOS_7_DÍAS"
        elif dias == 30:
            periodo_etiqueta = "ESTE_MES"
        elif dias == 365:
            periodo_etiqueta = "ESTE_AÑO"

        kpis = cls.obtener_kpis(db=db, dias=dias, tenant_id=tenant_id)
        ventas_canal = cls.obtener_ventas_canal(db=db, dias=dias, tenant_id=tenant_id)
        ventas_sucursal = cls.obtener_ventas_sucursal(db=db, dias=dias, tenant_id=tenant_id)
        ventas_metodo = cls.obtener_ventas_metodo_pago(db=db, dias=dias, tenant_id=tenant_id)
        top_prendas = cls.obtener_top_productos(db=db, limite=5, dias=dias, tenant_id=tenant_id)
        saas_tenant = cls.obtener_resumen_saas_tenant(db=db, tenant_id=tenant_id)

        return {
            "periodo": periodo_etiqueta,
            "kpis": kpis,
            "ventas_canal": ventas_canal,
            "ventas_sucursal": ventas_sucursal,
            "ventas_metodo": ventas_metodo,
            "top_prendas": top_prendas,
            "saas_tenant": saas_tenant
        }

    @classmethod
    def exportar_resumen_csv(cls, db: Session, dias: Optional[int] = None, tenant_id: int = 1) -> str:
        """
        Genera informe CSV ejecutivo multitenant para el Directorio y C-Level.
        """
        dashboard = cls.obtener_dashboard_completo(db=db, dias=dias, tenant_id=tenant_id)
        kpis = dashboard["kpis"]
        saas = dashboard["saas_tenant"]

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")

        writer.writerow(["INFORME EJECUTIVO MULTITENANT - SHOPYN GOLDEN STORE"])
        writer.writerow(["EMPRESA", saas["tenant_nombre"]])
        writer.writerow(["PLAN SAAS", saas["plan_nombre"]])
        writer.writerow(["PERIODO", dashboard["periodo"]])
        writer.writerow(["FECHA GENERACION", kpis["fecha_calculo"]])
        writer.writerow([])

        writer.writerow(["METRICA PRINCIPAL", "VALOR"])
        writer.writerow(["Ingresos Brutos (BOB)", f"{kpis['total_ingresos_bs']:.2f}"])
        writer.writerow(["Devoluciones y Reembolsos (BOB)", f"{kpis['monto_devoluciones_bs']:.2f}"])
        writer.writerow(["Ingresos Netos (BOB)", f"{kpis['ingresos_netos_bs']:.2f}"])
        writer.writerow(["Total Transacciones", kpis["total_transacciones"]])
        writer.writerow(["Ticket Promedio (BOB)", f"{kpis['ticket_promedio_bs']:.2f}"])
        writer.writerow(["Prendas Físicas Vendidas", kpis["prendas_vendidas"]])
        writer.writerow(["Reservas Activas en Boutique", kpis["reservas_activas"]])
        writer.writerow(["Stock Físico en Existencias", kpis["stock_total_fisico"]])
        writer.writerow(["Prendas con Stock Crítico", kpis["articulos_stock_critico"]])
        writer.writerow(["Operaciones Offline Sincronizadas", kpis["operaciones_offline_sincronizadas"]])
        writer.writerow([])

        writer.writerow(["DESGLOSE POR SUCURSAL FISICA", "CIUDAD", "INGRESOS (BOB)", "TRANSACCIONES", "% PARTICIPACION"])
        for suc in dashboard["ventas_sucursal"]:
            writer.writerow([
                suc["sucursal_nombre"],
                suc["ciudad"],
                f"{suc['total_bs']:.2f}",
                suc["transacciones"],
                f"{suc['porcentaje']}%"
            ])
        writer.writerow([])

        writer.writerow(["CANAL DE VENTA", "INGRESOS (BOB)", "TRANSACCIONES", "% PARTICIPACION"])
        for c in dashboard["ventas_canal"]:
            writer.writerow([
                c["canal"],
                f"{c['total_bs']:.2f}",
                c["transacciones"],
                f"{c['porcentaje']}%"
            ])
        writer.writerow([])

        writer.writerow(["TOP PRENDA BOUTIQUE", "SKU", "PRECIO UNIT.", "UNID. VENDIDAS", "RECAUDACION (BOB)"])
        for p in dashboard["top_prendas"]:
            writer.writerow([
                p["nombre_producto"],
                p["sku"],
                f"{p['precio_unitario']:.2f}",
                p["unidades_vendidas"],
                f"{p['recaudacion_bs']:.2f}"
            ])

        return output.getvalue()
