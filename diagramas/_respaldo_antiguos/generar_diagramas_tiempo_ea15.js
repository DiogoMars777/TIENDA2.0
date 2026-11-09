!INC Local Scripts.EAConstants-JScript

// =====================================================================
// Script: Generar Diagramas de Tiempo (UML Timing Diagram)
// Proyecto: T-Shirt Boutique ERP & E-Commerce (ECOMMERCE_TIENDA)
// Herramienta: Enterprise Architect 15 / 16 (Versión JavaScript / JScript)
// =====================================================================

function OnDiagramScript() {
    var currentPackage = Repository.GetTreeSelectedPackage();
    if (!currentPackage) {
        Session.Prompt("Por favor selecciona un Paquete en el Project Browser.", promptOK);
        return;
    }

    // 1. Diagrama de Tiempo: Proceso de Compra Digital y Pasarela de Pago (CU15)
    crearDiagramaTiempoCompraDigital(currentPackage);

    // 2. Diagrama de Tiempo: Proceso de Reserva de Prendas (CU10 - CU11)
    crearDiagramaTiempoReserva(currentPackage);

    Repository.RefreshModelView(0);
    Session.Prompt("¡Se generaron con éxito los 2 Diagramas de Tiempo adaptados a la arquitectura de tu proyecto!", promptOK);
}

// 1. TIEMPO: COMPRA DIGITAL Y PASARELA (CU15)
function crearDiagramaTiempoCompraDigital(pkg) {
    var diag = crearDiagramaLimpio(pkg, "sd Compra Digital y Pasarela (CU15)", "Timing");

    var llBackend    = crearTimeLine(pkg, ":Backend_CompraDigitalController", "Estados: Idle | ValidandoStock | EsperandoWebhook | ConfirmandoVenta");
    var llInventario = crearTimeLine(pkg, ":Inventario_Kardex",               "Estados: StockDisponible | RetenidoTemporal | DescontadoKardex");
    var llFrontend   = crearTimeLine(pkg, ":Frontend_UI_Checkout",             "Estados: Idle | EnviandoOrden | MostrandoPagoQR | MostrandoRecibo");
    var llCliente    = crearTimeLine(pkg, ":Cliente_WebUser",                  "Estados: Idle | EnCheckout | PagandoBancoQR | ViendoRecibo");

    colocarElemento(diag, llBackend,    50, 850, -30,  -110);
    colocarElemento(diag, llInventario, 50, 850, -130, -210);
    colocarElemento(diag, llFrontend,   50, 850, -230, -310);
    colocarElemento(diag, llCliente,    50, 850, -330, -410);

    crearMensajeEstimulo(llCliente,    llFrontend,   "1. clicIniciarCheckout()");
    crearMensajeEstimulo(llFrontend,   llBackend,    "2. POST /api/v1/compras/procesar");
    crearMensajeEstimulo(llBackend,    llInventario, "3. retenerStockTemporal()");
    crearMensajeEstimulo(llBackend,    llFrontend,   "4. sesionPagoCreada(QR/Stripe)");
    crearMensajeEstimulo(llFrontend,   llCliente,    "5. escanearQR_o_Pagar()");
    crearMensajeEstimulo(llBackend,    llInventario, "6. webhookExito() / rebajarKardex()");
    crearMensajeEstimulo(llBackend,    llFrontend,   "7. ventaConfirmada(VentaModel)");
    crearMensajeEstimulo(llFrontend,   llCliente,    "8. renderizarComprobanteDigital()");

    var notaRestricciones = crearNota(pkg, "RESTRICCIONES TEMPORALES UML (CU15):\n--------------------------------------------------\n• {50..200 ms}: Latencia HTTP Frontend -> Backend\n• {100..400 ms}: Validacion y Bloqueo atomico en BD\n• {0..15 min}: Ventana maxima para pago QR / Stripe\n• {< 3 s}: Webhook de confirmacion de pasarela\n--------------------------------------------------\nRegla de negocio: Si pasan 15 min sin respuesta del\nWebhook, el Backend libera el stock retenido y anula la orden.");
    colocarElemento(diag, notaRestricciones, 880, 1260, -30, -270);

    Repository.SaveDiagram(diag.DiagramID);
    Repository.ReloadDiagram(diag.DiagramID);
    Repository.OpenDiagram(diag.DiagramID);
}

// 2. TIEMPO: RESERVA DE PRENDAS (CU10 - CU11)
function crearDiagramaTiempoReserva(pkg) {
    var diag = crearDiagramaLimpio(pkg, "sd Reserva de Prendas (CU10-CU11)", "Timing");

    var llCronJob = crearTimeLine(pkg, ":CronJob_Expirador",           "Estados: Idle | Monitoreando(t < 48h) | DisparoTimeout(t = 48h)");
    var llBackend = crearTimeLine(pkg, ":Backend_ReservaController",   "Estados: Idle | GenerandoCodigo | AtendiendoEnSucursal | Cancelando");
    var llStock   = crearTimeLine(pkg, ":InventarioSucursal_Model",    "Estados: StockDisponible | StockReservado | DescontadoFisico");
    var llCliente = crearTimeLine(pkg, ":Cliente_Comprador",           "Estados: CarritoActivo | EsperandoRetiro | RetirandoEnSucursal");

    colocarElemento(diag, llCronJob, 50, 850, -30,  -110);
    colocarElemento(diag, llBackend, 50, 850, -130, -210);
    colocarElemento(diag, llStock,   50, 850, -230, -310);
    colocarElemento(diag, llCliente, 50, 850, -330, -410);

    crearMensajeEstimulo(llCliente, llBackend, "1. POST /api/v1/reservas/desde-carrito");
    crearMensajeEstimulo(llBackend, llStock,   "2. incrementar stockreservado");
    crearMensajeEstimulo(llBackend, llCronJob, "3. iniciarTemporizador(48h)");
    crearMensajeEstimulo(llCliente, llBackend, "4. CU11: presentarCodigo(RES-XXXX)");
    crearMensajeEstimulo(llBackend, llStock,   "5. rebajar stockfisico y stockreservado");

    var notaReserva = crearNota(pkg, "RESTRICCIONES TEMPORALES UML (CU10 / CU11):\n--------------------------------------------------\n• {0..48 horas}: Vigencia maxima para retiro en sucursal\n• A t = 0h: Se reserva stock e inicia cuenta regresiva.\n• Si t <= 48h y cliente asiste: Se atiende y descuenta stock.\n• Si t > 48h sin atencion: CronJob ejecuta liberacion de stock.");
    colocarElemento(diag, notaReserva, 880, 1260, -30, -250);

    Repository.SaveDiagram(diag.DiagramID);
    Repository.ReloadDiagram(diag.DiagramID);
    Repository.OpenDiagram(diag.DiagramID);
}

// AUXILIARES
function crearDiagramaLimpio(package, name, tipo) {
    for (var i = package.Diagrams.Count - 1; i >= 0; i--) {
        var d = package.Diagrams.GetAt(i);
        if (d.Name == name) {
            for (var j = d.DiagramObjects.Count - 1; j >= 0; j--) d.DiagramObjects.Delete(j);
            for (var k = d.DiagramLinks.Count - 1; k >= 0; k--) d.DiagramLinks.Delete(k);
            d.DiagramObjects.Refresh();
            d.DiagramLinks.Refresh();
            d.Update();
            return d;
        }
    }
    var diag = package.Diagrams.AddNew(name, tipo);
    diag.Update();
    package.Diagrams.Refresh();
    return diag;
}

function crearTimeLine(package, nombre, notas) {
    var deleteIndex = -1;
    for (var i = 0; i < package.Elements.Count; i++) {
        var el = package.Elements.GetAt(i);
        if (el.Name == nombre) {
            if (el.Type == "TimeLine") {
                el.Notes = notas;
                el.Update();
                return el;
            } else {
                deleteIndex = i;
                break;
            }
        }
    }
    if (deleteIndex >= 0) {
        package.Elements.Delete(deleteIndex);
        package.Elements.Refresh();
    }
    var newEl = null;
    try {
        newEl = package.Elements.AddNew(nombre, "TimeLine");
        newEl.Subtype = 0; // 0 = State Lifeline horizontal
    } catch(e) {
        newEl = package.Elements.AddNew(nombre, "Sequence");
    }
    if (newEl) {
        newEl.Notes = notas;
        newEl.Update();
        package.Elements.Refresh();
    }
    return newEl;
}

function crearMensajeEstimulo(origen, destino, nombreMensaje) {
    try {
        var con = origen.Connectors.AddNew(nombreMensaje, "TimingMessage");
        con.SupplierID = destino.ElementID;
        con.Update();
        origen.Connectors.Refresh();
    } catch(e) {
        try {
            var con2 = origen.Connectors.AddNew(nombreMensaje, "Message");
            con2.SupplierID = destino.ElementID;
            con2.Update();
            origen.Connectors.Refresh();
        } catch(e2) {}
    }
}

function crearNota(package, contenido) {
    var el = package.Elements.AddNew("", "Note");
    el.Notes = contenido;
    el.Update();
    package.Elements.Refresh();
    return el;
}

function colocarElemento(diagram, elemento, left, right, top, bottom) {
    var diagObj = diagram.DiagramObjects.AddNew("l=" + left + ";r=" + right + ";t=" + top + ";b=" + bottom + ";", "");
    diagObj.ElementID = elemento.ElementID;
    diagObj.Update();
}

OnDiagramScript();
