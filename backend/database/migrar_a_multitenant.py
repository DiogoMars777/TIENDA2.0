#!/usr/bin/env python3
# ==============================================================================
# SCRIPT DE MIGRACIÓN: BASE DE DATOS SINGLE-TENANT A MULTI-TENANT (SAAS)
# Proyecto: Shopyn Golden Store
# Archivo: backend/database/migrar_a_multitenant.py
# ==============================================================================

import sys
import os
import psycopg2
from pathlib import Path

# Añadir backend al path para cargar settings
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import settings

def print_step(msg):
    print(f"[*] {msg}")

def ejecutar_migracion():
    print("=" * 65)
    print("   MIGRACIÓN DE BASE DE DATOS A ARQUITECTURA MULTI-TENANT (SAAS)")
    print("=" * 65)
    
    conn = psycopg2.connect(
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # 1. Extensiones
        print_step("Habilitando extensiones UUID...")
        cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        cur.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

        # 2. Crear Tablas SaaS Plataforma
        print_step("Creando tablas de plataforma SaaS (plan, tenant, configuracion, suscripcion)...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.plan_suscripcion (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(50) NOT NULL UNIQUE,
                descripcion TEXT,
                precio_mensual NUMERIC(10, 2) NOT NULL,
                limite_sucursales INTEGER NOT NULL DEFAULT 1,
                limite_usuarios INTEGER NOT NULL DEFAULT 3,
                limite_productos INTEGER NOT NULL DEFAULT 100,
                habilitar_vestidor_ia BOOLEAN DEFAULT FALSE,
                activo BOOLEAN DEFAULT TRUE,
                fechacreacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS public.tenant (
                id SERIAL PRIMARY KEY,
                uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
                nombre VARCHAR(150) NOT NULL,
                slug VARCHAR(60) UNIQUE NOT NULL,
                dominio_personalizado VARCHAR(150) UNIQUE,
                nit_ruc VARCHAR(30),
                email_contacto VARCHAR(120) NOT NULL,
                telefono_contacto VARCHAR(30),
                direccion_fiscal TEXT,
                logo_url TEXT,
                plan_id INTEGER REFERENCES public.plan_suscripcion(id) ON UPDATE CASCADE,
                activo BOOLEAN DEFAULT TRUE,
                fechacreacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS public.tenant_configuracion (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER UNIQUE NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
                moneda_simbolo VARCHAR(10) DEFAULT 'Bs.',
                moneda_iso VARCHAR(5) DEFAULT 'BOB',
                zona_horaria VARCHAR(50) DEFAULT 'America/La_Paz',
                tiempo_expiracion_reserva_horas INTEGER DEFAULT 48,
                color_primario_hex VARCHAR(10) DEFAULT '#0d1b2a',
                color_secundario_hex VARCHAR(10) DEFAULT '#d4af37',
                paypal_client_id TEXT,
                paypal_client_secret TEXT,
                qr_banco_cuenta VARCHAR(60),
                whatsapp_notificaciones VARCHAR(30)
            );

            CREATE TABLE IF NOT EXISTS public.tenant_suscripcion (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
                plan_id INTEGER NOT NULL REFERENCES public.plan_suscripcion(id),
                fecha_inicio TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_fin TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                estado VARCHAR(20) DEFAULT 'ACTIVA',
                monto_pagado NUMERIC(10, 2) NOT NULL,
                metodo_pago VARCHAR(50)
            );
        """)

        # 3. Crear Nuevas Tablas del Diagrama UML (DireccionCliente, EventoCliente, PruebaVirtual, ProductoColeccion)
        print_step("Creando tablas complementarias del diagrama UML...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.direccioncliente (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER REFERENCES public.tenant(id) ON DELETE CASCADE,
                cliente_id INTEGER REFERENCES public.cliente(id) ON DELETE CASCADE,
                nombre VARCHAR(100),
                direccion VARCHAR(255) NOT NULL,
                referencia VARCHAR(255),
                ciudad VARCHAR(80),
                departamento VARCHAR(80),
                telefono VARCHAR(30),
                esprincipal BOOLEAN DEFAULT FALSE,
                activo BOOLEAN DEFAULT TRUE
            );

            CREATE TABLE IF NOT EXISTS public.evento_cliente (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER REFERENCES public.tenant(id) ON DELETE CASCADE,
                cliente_id INTEGER REFERENCES public.cliente(id) ON DELETE CASCADE,
                tipoevento VARCHAR(80) NOT NULL,
                fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS public.prueba_virtual (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER REFERENCES public.tenant(id) ON DELETE CASCADE,
                cliente_id INTEGER REFERENCES public.cliente(id) ON DELETE SET NULL,
                variante_id INTEGER REFERENCES public.variante_producto(id) ON DELETE SET NULL,
                imagenresultadourl TEXT NOT NULL,
                dispositivo VARCHAR(50),
                fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS public.producto_coleccion (
                id SERIAL PRIMARY KEY,
                producto_id INTEGER NOT NULL REFERENCES public.producto(id) ON DELETE CASCADE,
                coleccion_id INTEGER NOT NULL REFERENCES public.coleccion(id) ON DELETE CASCADE,
                cantidad INTEGER DEFAULT 1,
                CONSTRAINT uq_producto_coleccion UNIQUE (producto_id, coleccion_id)
            );
        """)

        # 4. Insertar Planes Oficiales (Sección 9.4: Básico y Profesional) y Tenants
        print_step("Configurando Planes Oficiales (Básico y Profesional) y Tenants...")
        cur.execute("""
            ALTER TABLE public.plan_suscripcion ADD COLUMN IF NOT EXISTS habilitar_reportes_ia BOOLEAN DEFAULT FALSE;

            INSERT INTO public.plan_suscripcion (id, nombre, descripcion, precio_mensual, limite_sucursales, limite_usuarios, limite_productos, habilitar_reportes_ia, habilitar_vestidor_ia, activo)
            VALUES (
                1,
                'Profesional',
                'Plan Profesional: Hasta 10 sucursales activas, gestión de productos, ventas, reservas, operación offline, reportes convencionales y Reportes Generativos con IA.',
                250.00,
                10,
                25,
                1000,
                TRUE,
                TRUE,
                TRUE
            )
            ON CONFLICT (id) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                descripcion = EXCLUDED.descripcion,
                precio_mensual = EXCLUDED.precio_mensual,
                limite_sucursales = EXCLUDED.limite_sucursales,
                limite_usuarios = EXCLUDED.limite_usuarios,
                limite_productos = EXCLUDED.limite_productos,
                habilitar_reportes_ia = EXCLUDED.habilitar_reportes_ia,
                habilitar_vestidor_ia = EXCLUDED.habilitar_vestidor_ia,
                activo = TRUE;

            INSERT INTO public.plan_suscripcion (id, nombre, descripcion, precio_mensual, limite_sucursales, limite_usuarios, limite_productos, habilitar_reportes_ia, habilitar_vestidor_ia, activo)
            VALUES (
                2,
                'Básico',
                'Plan Básico: Hasta 2 sucursales activas, gestión de productos, ventas, reservas, operación offline y reportes convencionales (sin Reportes Generativos con IA).',
                120.00,
                2,
                5,
                200,
                FALSE,
                FALSE,
                TRUE
            )
            ON CONFLICT (id) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                descripcion = EXCLUDED.descripcion,
                precio_mensual = EXCLUDED.precio_mensual,
                limite_sucursales = EXCLUDED.limite_sucursales,
                limite_usuarios = EXCLUDED.limite_usuarios,
                limite_productos = EXCLUDED.limite_productos,
                habilitar_reportes_ia = EXCLUDED.habilitar_reportes_ia,
                habilitar_vestidor_ia = EXCLUDED.habilitar_vestidor_ia,
                activo = TRUE;

            INSERT INTO public.tenant (id, nombre, slug, email_contacto, telefono_contacto, plan_id, activo)
            VALUES (1, 'Shopyn Golden Store', 'goldenstore', 'admin@goldenstore.com', '70000001', 1, TRUE)
            ON CONFLICT (id) DO UPDATE SET plan_id = 1, email_contacto = 'admin@goldenstore.com';

            INSERT INTO public.tenant_configuracion (tenant_id, moneda_simbolo, tiempo_expiracion_reserva_horas, color_primario_hex)
            VALUES (1, 'Bs.', 48, '#0d1b2a')
            ON CONFLICT (tenant_id) DO NOTHING;

            SELECT setval('public.plan_suscripcion_id_seq', (SELECT MAX(id) FROM public.plan_suscripcion));
            SELECT setval('public.tenant_id_seq', (SELECT MAX(id) FROM public.tenant));
        """)

        # 5. Agregar tenant_id a las tablas existentes
        tablas_negocio = [
            'sucursal', 'usuario', 'cliente', 'categoria', 'temporada', 'coleccion',
            'producto', 'proveedor', 'inventario', 'inventario_sucursal', 'movimiento_inventario',
            'carrito', 'reserva', 'venta', 'pago', 'recibo', 'bitacora', 'notificacion'
        ]

        print_step("Agregando columna tenant_id a las tablas de negocio existentes...")
        for t in tablas_negocio:
            # Comprobar si la tabla existe
            cur.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{t}');")
            if not cur.fetchone()[0]:
                continue
            
            # Comprobar si la columna tenant_id ya existe
            cur.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '{t}' AND column_name = 'tenant_id');")
            col_exists = cur.fetchone()[0]
            if not col_exists:
                cur.execute(f"ALTER TABLE public.{t} ADD COLUMN tenant_id INTEGER REFERENCES public.tenant(id) ON DELETE CASCADE;")
                print(f"   [+] Columna tenant_id agregada a '{t}'")
            
            # Asignar tenant_id = 1 a datos existentes
            cur.execute(f"UPDATE public.{t} SET tenant_id = 1 WHERE tenant_id IS NULL;")
            # Forzar NOT NULL
            cur.execute(f"ALTER TABLE public.{t} ALTER COLUMN tenant_id SET NOT NULL;")

        # 6. Crear índices compuestos multi-tenant para máxima velocidad
        print_step("Creando índices B-Tree optimizados para multi-tenancy...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tenant_slug ON public.tenant(slug);
            CREATE INDEX IF NOT EXISTS idx_usuario_tenant ON public.usuario(tenant_id, activo);
            CREATE INDEX IF NOT EXISTS idx_cliente_tenant ON public.cliente(tenant_id, activo);
            CREATE INDEX IF NOT EXISTS idx_producto_tenant ON public.producto(tenant_id, activo);
            CREATE INDEX IF NOT EXISTS idx_inventario_tenant ON public.inventario(tenant_id, sucursalid);
            CREATE INDEX IF NOT EXISTS idx_venta_tenant ON public.venta(tenant_id, fecha);
            CREATE INDEX IF NOT EXISTS idx_reserva_tenant ON public.reserva(tenant_id, estado);
        """)

        # 7. Resumen de validación
        print("\n" + "=" * 65)
        print("          RESUMEN DE MIGRACIÓN MULTI-TENANT EXITOSA")
        print("=" * 65)
        cur.execute("SELECT count(*) FROM public.tenant;")
        total_tenants = cur.fetchone()[0]
        print(f"  • Tenants registrados             : {total_tenants}")

        for t in ['usuario', 'cliente', 'sucursal', 'producto', 'inventario', 'venta']:
            cur.execute(f"SELECT count(*) FROM public.{t} WHERE tenant_id = 1;")
            cnt = cur.fetchone()[0]
            print(f"  • Registros migrados en '{t.ljust(12)}': {cnt} asignados a Tenant #1")

        print("=" * 65)
        print("[EXITO] Base de datos migrada a Multi-Tenant sin pérdida de datos.")
        print("=" * 65 + "\n")

    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        conn.close()
        sys.exit(1)

    conn.close()

if __name__ == "__main__":
    ejecutar_migracion()
