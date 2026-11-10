#!/usr/bin/env python3
# ==============================================================================
# SHOPYN GOLDEN STORE - SCRIPT DE RESTAURACIÓN AUTOMÁTICA DE BASE DE DATOS
# Ubicación: backend/database/restaurar_base_datos.py
#
# Este script restaura toda la estructura de la base de datos PostgreSQL,
# tablas, roles, usuarios, categorías, sucursales, prendas con fotos/links,
# inventario multitienda, pasarelas de pago y bitácora del sistema.
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
    print("=" * 65)
    print("      [*] SHOPYN GOLDEN STORE - RESTAURADOR DE BASE DE DATOS")
    print("   PostgreSQL | Modelos MVC | Datos Reales | Catalogo de Prendas")
    print("=" * 65)

def cargar_configuracion():
    config = {
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "ecommerce_db",
    }
    
    rutas_env = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path(".env"),
        Path("backend/.env"),
    ]
    
    for r in rutas_env:
        if r.exists():
            print(f"📄 Leyendo configuración desde: {r}")
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

    # Detectar si se pasó una URL directa por argumento (--url) o variable DATABASE_URL
    db_url = None
    for i, arg in enumerate(sys.argv):
        if arg == "--url" and i + 1 < len(sys.argv):
            db_url = sys.argv[i + 1]
    if not db_url and os.environ.get("DATABASE_URL"):
        db_url = os.environ.get("DATABASE_URL")

    if db_url:
        print(f"\n🌐 Modo Cloud Detectado: Conectando a base de datos remota...")
        # Normalizar postgres:// a postgresql:// si es necesario
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
    else:
        print(f"\n🔌 Conectando a PostgreSQL local ({user}@{host}:{port})...")
    
    try:
        import psycopg2
    except ImportError:
        print("\n❌ Error: La librería 'psycopg2' no está instalada.")
        print("💡 Ejecuta en tu terminal:")
        print("   pip install psycopg2-binary")
        sys.exit(1)

    backup_sql_path = Path(__file__).resolve().parent / "seeder.sql"
    if not backup_sql_path.exists():
        backup_sql_path = Path(__file__).resolve().parent / "backup_completo.sql"
    if not backup_sql_path.exists():
        backup_sql_path = Path("backend/database/seeder.sql")
    if not backup_sql_path.exists():
        backup_sql_path = Path("backend/database/backup_completo.sql")
    if not backup_sql_path.exists():
        backup_sql_path = Path("database/seeder.sql")

    if not backup_sql_path.exists():
        print(f"\n❌ Error: No se encontró el archivo de datos 'seeder.sql'.")
        print(f"Buscado en: {backup_sql_path}")
        sys.exit(1)

    if not db_url:
        # 1. Crear base de datos local si no existe conectándose a 'postgres'
        try:
            conn_root = psycopg2.connect(
                dbname="postgres",
                user=user,
                password=password,
                host=host,
                port=port
            )
            conn_root.autocommit = True
            cur_root = conn_root.cursor()
            
            cur_root.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
            if not cur_root.fetchone():
                print(f"📦 Creando base de datos '{db_name}'...")
                cur_root.execute(f'CREATE DATABASE "{db_name}" ENCODING \'UTF8\';')
                print(f"✅ Base de datos '{db_name}' creada exitosamente.")
            else:
                print(f"ℹ️  La base de datos '{db_name}' ya existe. Se sobreescribirá con los datos actuales.")
                
            cur_root.close()
            conn_root.close()
        except Exception as e:
            print(f"⚠️ Aviso al verificar base de datos 'postgres': {e}")
            print(f"Intentando conectar directamente a '{db_name}'...")

    # 2. Conectar a la base de datos de destino y ejecutar backup_completo.sql
    try:
        print(f"\n🚀 Restaurando tablas y datos desde '{backup_sql_path.name}'...")
        if db_url:
            conn_target = psycopg2.connect(db_url)
        else:
            conn_target = psycopg2.connect(
                dbname=db_name,
                user=user,
                password=password,
                host=host,
                port=port
            )
        conn_target.autocommit = True
        cur_target = conn_target.cursor()
        
        print("[*] Limpiando esquema public previo para evitar conflictos de dependencias...")
        cur_target.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres; GRANT ALL ON SCHEMA public TO public;")
        
        print("[*] Ejecutando script SQL (tablas, constraints, prendas con imágenes y stock)...")
        t0 = time.time()
        
        with open(backup_sql_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        cur_target.execute(sql_content)
        duracion = round(time.time() - t0, 2)
        print(f"[OK] Script ejecutado en {duracion} segundos.")

        # 3. Validar contenido cargado
        print("\n" + "=" * 65)
        print("      RESUMEN DE DATOS CARGADOS EN SHOPYN GOLDEN STORE")
        print("=" * 65)

        tablas_clave = [
            ("rol", "Roles de Usuario"),
            ("usuario", "Cuentas de Usuario / Operadores"),
            ("cliente", "Clientes Registrados"),
            ("sucursal", "Sucursales Físicas"),
            ("categoria", "Categorías de Prendas"),
            ("producto", "Poleras / Prendas con Imágenes"),
            ("variante_producto", "Variantes (Tallas y Colores)"),
            ("inventario", "Stock en Sucursales"),
            ("metodo_pago", "Métodos de Pago (Efectivo, Visa, QR, PayPal)"),
            ("bitacora", "Registros de Auditoría y Bitácora"),
        ]

        for tabla, desc in tablas_clave:
            try:
                cur_target.execute(f'SELECT count(*) FROM public."{tabla}";')
                total = cur_target.fetchone()[0]
                print(f"  [OK] {desc.ljust(38)}: {str(total).rjust(4)} registros")
            except Exception:
                print(f"  [--] {desc.ljust(38)}: [No disponible]")

        # Muestra de productos con imagen
        cur_target.execute('SELECT nombre, imagenprincipal FROM public.producto WHERE imagenprincipal IS NOT NULL LIMIT 2;')
        muestras = cur_target.fetchall()
        if muestras:
            print("\n[*] Muestras de fotos y links verificados en el catálogo:")
            for m in muestras:
                print(f"   • {m[0]}: {m[1]}")

        cur_target.close()
        conn_target.close()

        print("\n" + "=" * 65)
        print("[EXITO] ¡RESTAURACIÓN COMPLETADA CON ÉXITO!")
        print("   Tu equipo ya tiene todos los datos sincronizados y listos.")
        print("   Para iniciar el backend: uvicorn app.main:app --reload")
        print("=" * 65 + "\n")

    except Exception as e:
        print(f"\n❌ Error durante la restauración: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
