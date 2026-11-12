// ==============================================================================
// CU22 - REGISTRAR COBROS DE CONTADO SIN CONEXIÓN -> MODELOS TYPESCRIPT
// Ubicación: frontend-web/src/app/models/cu22_registrar_cobros_contado_offline/cobro-offline.model.ts
// ==============================================================================

export interface ItemCobroOfflineDTO {
  variante_id?: number;
  producto_nombre: string;
  talla?: string;
  color?: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

export interface CobroOfflineDTO {
  id: number;
  tenant_id: number;
  cajero_id?: number;
  cajero_nombre?: string;
  sucursal_id: number;
  sucursal_nombre?: string;
  monto: number;
  moneda: string;
  nro_recibo_provisional: string;
  uuid_operacion: string;
  cliente_nombre?: string;
  cliente_nit?: string;
  observaciones?: string;
  fecha_cobro: string;
  sincronizado: boolean;
  fecha_sincronizacion?: string;
  venta_id?: number;
  items?: ItemCobroOfflineDTO[];
  efectivo_recibido?: number;
  cambio?: number;
  almacenado_local?: boolean; // Marca si reside en localStorage del navegador
}

export interface RegistroCobroOfflineRequest {
  sucursal_id: number;
  monto: number;
  moneda?: string;
  nro_recibo_provisional: string;
  uuid_operacion?: string;
  cliente_nombre?: string;
  cliente_nit?: string;
  efectivo_recibido?: number;
  cambio?: number;
  observaciones?: string;
  fecha_cobro?: string;
  items?: ItemCobroOfflineDTO[];
}

export interface CobroOfflineKPIsDTO {
  total_cobros: number;
  monto_total_offline: number;
  pendientes_sync: number;
  monto_pendiente: number;
  sincronizados: number;
  monto_sincronizado: number;
  sucursal_activa_id?: number;
}
