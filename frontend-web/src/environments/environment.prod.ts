// ==============================================================================
// CONFIGURACIÓN DE PRODUCCIÓN - SHOPYN GOLDEN STORE
// Proyecto: ECOMMERCE_TIENDA (Angular SPA)
// Conectado al backend en Railway y base de datos en Supabase
// ==============================================================================

export const environment = {
  production: true,
  get apiUrl(): string {
    if (typeof window !== 'undefined') {
      const customApi = localStorage.getItem('API_URL') || (window as any).__API_URL__;
      if (customApi) return customApi;
    }
    return 'https://tienda20-production.up.railway.app/api/v1';
  }
};
