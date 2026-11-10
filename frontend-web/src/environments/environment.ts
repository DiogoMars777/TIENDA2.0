// ==============================================================================
// CONFIGURACIÓN DE DESARROLLO / NUBE FLEXIBLE - SHOPYN GOLDEN STORE
// Proyecto: ECOMMERCE_TIENDA (Angular SPA)
// ==============================================================================

export const environment = {
  production: false,
  get apiUrl(): string {
    if (typeof window !== 'undefined' && window.location) {
      // 1. Si el usuario definió una URL manual en localStorage o en la consola
      const customApi = localStorage.getItem('API_URL') || (window as any).__API_URL__;
      if (customApi) return customApi;

      const host = window.location.hostname;
      // 2. Si corre desplegado en Vercel (*.vercel.app) u otro dominio público sin backend local
      if (host.includes('vercel.app') || (host !== 'localhost' && host !== '127.0.0.1' && !host.startsWith('192.168.'))) {
        return 'https://tienda20-production.up.railway.app/api/v1';
      }

      // 3. Si corre en desarrollo local
      return `http://${host}:8000/api/v1`;
    }
    return 'http://localhost:8000/api/v1';
  }
};
