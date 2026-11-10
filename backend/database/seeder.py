#!/usr/bin/env python3
# ==============================================================================
# SHOPYN GOLDEN STORE & SAAS MULTI-TENANT
# SEEDER OFICIAL Y RESTAURADOR DE BASE DE DATOS (POSTGRESQL)
# Ubicación: backend/database/seeder.py
#
# Ejecución:
#   python database/seeder.py             (Siembra todos los datos actuales)
#   python database/seeder.py --fresh     (Limpia y resiembra desde cero)
#   python database/seeder.py --clean-unused (Elimina tablas obsoletas en desuso)
# ==============================================================================

import os
import sys
import time
from pathlib import Path

# Configurar salida segura UTF-8 en consolas Windows
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def print_banner():
    print("=" * 70)
    print("      🌱 SEEDER OFICIAL DE BASE DE DATOS - ERP MULTI-TENANT")
    print("  Empresas: Shopyn Golden Store & Saint Seya | PostgreSQL")
    print("=" * 70)

def cargar_configuracion():
    config = {
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "ecommerce_db",
    }
    
    rutas_env = [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(".env"),
        Path("backend/.env"),
    ]
    
    for r in rutas_env:
        if r.exists():
            print(f"📄 Leyendo credenciales desde: {r}")
            with open(r, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        config[k.strip()] = v.strip().strip('"').strip("'")
            break
            
    for k in config:
        if k in os.environ and os.environ[k]:
            config[k] = os.environ[k]
            
    return config

def main():
    print_banner()
    cfg = cargar_configuracion()
    
    user = cfg["POSTGRES_USER"]
    password = cfg["POSTGRES_PASSWORD"]
    host = cfg["POSTGRES_SERVER"]
    port = cfg["POSTGRES_PORT"]
    db_name = cfg["POSTGRES_DB"]

    try:
        import psycopg2
    except ImportError:
        print("\n❌ Error: La librería 'psycopg2' no está instalada.")
        print("💡 Ejecuta: pip install psycopg2-binary")
        sys.exit(1)

    print(f"\n🔌 Conectando a PostgreSQL: {user}@{host}:{port}/{db_name}...")
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        cur = conn.cursor()
        print("✅ Conexión establecida exitosamente.")
    except Exception as e:
        print(f"\n❌ Error de conexión a la base de datos: {e}")
        sys.exit(1)

    # Revisar si se pasó la bandera --clean-unused
    clean_unused = "--clean-unused" in sys.argv
    if clean_unused:
        print("\n🧹 Depuración de tablas obsoletas solicitada (--clean-unused)...")
        tablas_obsoletas = [
            "producto_coleccion",
            "coleccion",
            "inventario_sucursal",
            "direccioncliente",
            "evento_cliente",
            "prueba_virtual",
            "producto_proveedor",
            "dashboard_metrica_snapshot"
        ]
        for tbl in tablas_obsoletas:
            try:
                cur.execute(f'DROP TABLE IF EXISTS "{tbl}" CASCADE;')
                print(f"  🗑️  Tabla obsoleta eliminada: {tbl}")
            except Exception as e:
                print(f"  ⚠️ No se pudo eliminar {tbl}: {e}")

    # Cargar y ejecutar seeder.sql
    seeder_sql_path = Path(__file__).resolve().parent / "seeder.sql"
    if not seeder_sql_path.exists():
        print(f"\n❌ Error: No se encontró el archivo SQL en: {seeder_sql_path}")
        sys.exit(1)

    print(f"\n🌱 Ejecutando siembra de datos desde: {seeder_sql_path.name}...")
    with open(seeder_sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    try:
        cur.execute(sql_content)
        print("✅ Siembra de datos SQL completada exitosamente!")
    except Exception as e:
        print(f"\n❌ Error al ejecutar el script de siembra: {e}")
        cur.close()
        conn.close()
        sys.exit(1)

    # Resumen y verificación final de conteos
    print("\n" + "=" * 55)
    print("📊 RESUMEN DE DATOS SEMBRADOS EN LA BASE DE DATOS:")
    print("=" * 55)

    tablas_verificar = [
        ("tenant", "Empresas Multi-Tenant (Golden Store, Saint Seya)"),
        ("plan_suscripcion", "Planes de Suscripción"),
        ("tenant_suscripcion", "Suscripciones Activas"),
        ("tenant_configuracion", "Configuraciones Tenant (Moneda, Branding)"),
        ("rol", "Roles de Usuario"),
        ("sucursal", "Sucursales Físicas"),
        ("usuario", "Usuarios y Cuentas de Acceso"),
        ("cliente", "Clientes Registrados"),
        ("categoria", "Categorías de Prendas"),
        ("temporada", "Temporadas"),
        ("talla", "Tallas (XS a XL)"),
        ("color", "Colores con Código Hexadecimal"),
        ("proveedor", "Proveedores Textiles"),
        ("producto", "Catálogo de Prendas"),
        ("variante_producto", "Variantes (Color x Talla x Código)"),
        ("inventario", "Existencias en Sucursales Físicas"),
        ("movimiento_inventario", "Historial de Movimientos"),
        ("metodo_pago", "Métodos de Pago Habilitados"),
        ("venta", "Ventas (POS Presencial, Digital, Offline)"),
        ("detalle_venta", "Detalle de Prendas Facturadas"),
        ("pago", "Comprobantes de Pago Registrados"),
        ("cobro_offline", "Cobros Contado Offline (CU22)"),
        ("sincronizacion_offline", "Sincronizaciones Offline (CU23)"),
        ("reserva", "Reservas y Apartados de Prendas (CU10/CU11)"),
        ("reserva_detalle", "Detalle de Prendas Apartadas"),
        ("devolucion", "Cambios y Devoluciones (CU25)"),
        ("detalle_devolucion", "Detalle de Prendas Devueltas/Cambiadas"),
        ("notificacion", "Notificaciones del Sistema (CU19)"),
        ("bitacora", "Registros de Auditoría y Bitácora (CU26)"),
        ("carrito", "Carritos de Compra Activos"),
        ("carrito_item", "Items en Carrito")
    ]

    for tbl, desc in tablas_verificar:
        try:
            cur.execute(f'SELECT count(*) FROM "{tbl}";')
            cnt = cur.fetchone()[0]
            print(f"  • {desc:<48}: {cnt:>4} registros")
        except Exception:
            pass

    print("=" * 55)
    print("✨ ¡Base de datos lista para pruebas, desarrollo y producción!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
