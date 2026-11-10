// ==============================================================================
// CAPA MODELO (MVC - MODEL EN ANGULAR)
// Módulo: CU09 - Gestionar Carrito de Compras
// Ubicación: frontend-web/src/app/models/cu9_gestionar_carrito_compras/carrito.model.ts
// ==============================================================================

export interface CarritoItem {
  item_id?: number;
  variante_id: number;
  producto_id: number;
  producto_nombre: string;
  imagen_url?: string;
  sku?: string;
  talla?: string;
  color?: string;
  codigohex?: string;
  precio_unitario: number;
  cantidad: number;
  subtotal: number;
  stock_disponible: number;
  stock_suficiente: boolean;
}

export interface Carrito {
  id?: number;
  carrito_id?: number;
  estado?: string;
  cliente_id?: number;
  sucursal_id?: number | null;
  sucursal_nombre?: string | null;
  items: CarritoItem[];
  total_items: number;
  total_precio: number;
  tiene_alertas_stock: boolean;
  fecha_actualizacion?: string;
}

export interface AgregarItemCarritoDTO {
  variante_id: number;
  cantidad?: number;
  sucursal_id?: number | null;
}

export interface ActualizarCantidadItemDTO {
  cantidad: number;
}

export interface AsignarSucursalCarritoDTO {
  sucursal_id: number;
}
