/**
 * script.js - JavaScript principal
 * ================================
 * Funcionalidad común para toda la aplicación
 */

// ============================================================
// MENÚ RESPONSIVE (móviles)
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
        
        // Cerrar menú al hacer clic en un enlace
        const navLinks = navMenu.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                navMenu.classList.remove('active');
            });
        });
    }
});

// ============================================================
// AUTO-CERRAR MENSAJES FLASH
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.alert');
    
    flashMessages.forEach(alert => {
        // Auto-cerrar después de 5 segundos
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100%)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// ============================================================
// CONFIRMACIÓN DE ELIMINACIÓN
// ============================================================

function confirmarEliminar(id, nombre) {
    return confirm(`¿Estás seguro de eliminar "${nombre}"?\n\nEsta acción no se puede deshacer.`);
}

// ============================================================
// VALIDACIÓN DE FORMULARIOS
// ============================================================

function validarFormulario(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('[required]');
    let valido = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = 'var(--danger-color)';
            valido = false;
        } else {
            input.style.borderColor = 'var(--border-color)';
        }
    });
    
    return valido;
}

// ============================================================
// FORMATEAR NÚMEROS (para mostrar precios)
// ============================================================

function formatearPrecio(numero) {
    return Number(numero).toFixed(2) + '€';
}

// ============================================================
// COPIAR AL PORTAPAPELES
// ============================================================

function copiarAlPortapapeles(texto) {
    navigator.clipboard.writeText(texto).then(() => {
        mostrarNotificacion('✅ Copiado al portapapeles', 'success');
    }).catch(() => {
        mostrarNotificacion('❌ Error al copiar', 'error');
    });
}

// ============================================================
// MOSTRAR NOTIFICACIONES PERSONALIZADAS
// ============================================================

function mostrarNotificacion(mensaje, tipo = 'info') {
    const notificacion = document.createElement('div');
    notificacion.className = `alert alert-${tipo}`;
    notificacion.innerHTML = `
        <span class="alert-icon">
            <i class="fas fa-${tipo === 'success' ? 'check' : tipo === 'error' ? 'times' : 'info'}-circle"></i>
        </span>
        ${mensaje}
        <button class="alert-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    // Buscar o crear contenedor de notificaciones
    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    container.appendChild(notificacion);
    
    // Auto-cerrar después de 3 segundos
    setTimeout(() => {
        notificacion.style.opacity = '0';
        notificacion.style.transform = 'translateX(100%)';
        setTimeout(() => notificacion.remove(), 300);
    }, 3000);
}

// ============================================================
// UTILIDADES PARA FECHAS
// ============================================================

function formatearFecha(fechaString) {
    const fecha = new Date(fechaString);
    const opciones = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return fecha.toLocaleDateString('es-ES', opciones);
}

function obtenerFechaActual() {
    const ahora = new Date();
    const year = ahora.getFullYear();
    const month = String(ahora.getMonth() + 1).padStart(2, '0');
    const day = String(ahora.getDate()).padStart(2, '0');
    const hours = String(ahora.getHours()).padStart(2, '0');
    const minutes = String(ahora.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// ============================================================
// SCROLL SUAVE
// ============================================================

function scrollSuave(elementId) {
    const elemento = document.getElementById(elementId);
    if (elemento) {
        elemento.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// ============================================================
// BÚSQUEDA EN TABLAS (filtrado en tiempo real)
// ============================================================

function filtrarTabla(inputId, tablaId) {
    const input = document.getElementById(inputId);
    const tabla = document.getElementById(tablaId);
    
    if (!input || !tabla) return;
    
    input.addEventListener('keyup', function() {
        const filtro = this.value.toLowerCase();
        const filas = tabla.getElementsByTagName('tr');
        
        for (let i = 1; i < filas.length; i++) {  // Empezar en 1 para saltar header
            const fila = filas[i];
            const texto = fila.textContent.toLowerCase();
            
            if (texto.includes(filtro)) {
                fila.style.display = '';
            } else {
                fila.style.display = 'none';
            }
        }
    });
}

// ============================================================
// LOADING SPINNER (para operaciones asíncronas)
// ============================================================

function mostrarLoading(mensaje = 'Cargando...') {
    const loading = document.createElement('div');
    loading.id = 'loadingOverlay';
    loading.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                    background: rgba(0,0,0,0.7); display: flex; align-items: center; 
                    justify-content: center; z-index: 9999; color: white; font-size: 1.5rem;">
            <div style="text-align: center;">
                <i class="fas fa-spinner fa-spin" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <p>${mensaje}</p>
            </div>
        </div>
    `;
    document.body.appendChild(loading);
}

function ocultarLoading() {
    const loading = document.getElementById('loadingOverlay');
    if (loading) {
        loading.remove();
    }
}

// ============================================================
// ANIMACIONES DE ENTRADA (para elementos que aparecen)
// ============================================================

function animarEntrada() {
    const elementos = document.querySelectorAll('.animate-on-scroll');
    
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    });
    
    elementos.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'all 0.5s ease';
        observer.observe(el);
    });
}

// Ejecutar al cargar la página
document.addEventListener('DOMContentLoaded', animarEntrada);

// ============================================================
// EXPORTAR FUNCIONES GLOBALES
// ============================================================

window.confirmarEliminar = confirmarEliminar;
window.validarFormulario = validarFormulario;
window.formatearPrecio = formatearPrecio;
window.copiarAlPortapapeles = copiarAlPortapapeles;
window.mostrarNotificacion = mostrarNotificacion;
window.formatearFecha = formatearFecha;
window.obtenerFechaActual = obtenerFechaActual;
window.scrollSuave = scrollSuave;
window.filtrarTabla = filtrarTabla;
window.mostrarLoading = mostrarLoading;
window.ocultarLoading = ocultarLoading;

console.log('✅ Script.js cargado correctamente');

// ============================================================
// CSRF + BORRADO DE TICKETS (unificado)
// ============================================================

/**
 * Lee el token CSRF de la etiqueta <meta name="csrf-token"> de base.html.
 */
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

/**
 * Envuelve fetch() añadiendo automáticamente la cabecera X-CSRFToken
 * y el Content-Type JSON. Se usa para las llamadas a la API.
 */
async function fetchJSON(url, body) {
    const respuesta = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(body),
    });
    return respuesta;
}

/**
 * Elimina un ticket creando y enviando un formulario POST con token CSRF.
 * Una sola implementación para todas las páginas (antes estaba duplicada).
 */
function eliminarTicket(ticketId, tienda) {
    if (!confirm(`¿Eliminar el ticket de "${tienda}"? Esta acción no se puede deshacer.`)) {
        return;
    }
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/eliminar_ticket/${encodeURIComponent(ticketId)}`;

    const token = document.createElement('input');
    token.type = 'hidden';
    token.name = 'csrf_token';
    token.value = getCsrfToken();
    form.appendChild(token);

    document.body.appendChild(form);
    form.submit();
}

// Listener delegado: cualquier elemento con data-eliminar borra su ticket.
// Los datos viajan en atributos data-* (Jinja los escapa), no en cadenas JS,
// así que nombres con comillas o caracteres raros no rompen nada.
document.addEventListener('click', function (e) {
    const boton = e.target.closest('[data-eliminar]');
    if (boton) {
        e.preventDefault();
        eliminarTicket(boton.dataset.id, boton.dataset.tienda);
    }
});

window.getCsrfToken = getCsrfToken;
window.fetchJSON = fetchJSON;
window.eliminarTicket = eliminarTicket;

// ============================================================
// FAVORITOS (corazón)
// ============================================================

async function alternarFavorito(boton) {
    const nombre = boton.dataset.nombre;
    if (!nombre) return;
    boton.disabled = true;
    try {
        const resp = await fetchJSON('/api/favoritos/alternar', { nombre });
        const data = await resp.json();
        if (data.success) {
            // Actualiza TODOS los corazones de ese mismo producto en la página.
            document.querySelectorAll('[data-favorito]').forEach(b => {
                if (b.dataset.nombre === nombre) marcarCorazon(b, data.favorito);
            });
        }
    } catch (e) {
        console.error('Error al alternar favorito:', e);
    } finally {
        boton.disabled = false;
    }
}

function marcarCorazon(boton, activo) {
    boton.classList.toggle('activo', activo);
    boton.setAttribute('aria-pressed', activo ? 'true' : 'false');
    boton.title = activo ? 'Quitar de favoritos' : 'Añadir a favoritos';
    const icono = boton.querySelector('i');
    if (icono) {
        icono.classList.toggle('fas', activo);    // corazón lleno
        icono.classList.toggle('far', !activo);   // corazón vacío
    }
}

// Listener delegado: cualquier elemento con data-favorito alterna al pulsarlo.
document.addEventListener('click', function (e) {
    const boton = e.target.closest('[data-favorito]');
    if (boton) {
        e.preventDefault();
        alternarFavorito(boton);
    }
});

window.alternarFavorito = alternarFavorito;

// ============================================================
// FAVORITO EN EL FORMULARIO (marca local, se confirma al guardar)
// ============================================================

// Alterna la marca de favorito de una fila del formulario de ticket.
// No llama a la API: solo cambia el input oculto y el icono; el favorito
// se confirma en el backend cuando se guarda el ticket.
function alternarFavForm(boton) {
    const fila = boton.closest('.producto-item');
    const oculto = fila.querySelector('input[name="producto_favorito[]"]');
    const activo = oculto.value !== '1';
    oculto.value = activo ? '1' : '0';
    boton.classList.toggle('activo', activo);
    boton.setAttribute('aria-pressed', activo ? 'true' : 'false');
    boton.title = activo ? 'Se guardará como favorito' : 'Marcar como favorito';
    const icono = boton.querySelector('i');
    if (icono) {
        icono.classList.toggle('fas', activo);
        icono.classList.toggle('far', !activo);
    }
}

window.alternarFavForm = alternarFavForm;
