/**
 * FitLife Gym — Scripts del Sistema de Interfaz (UX)
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Alternar Menú de Navegación en Dispositivos Móviles
    const navToggleBtn = document.getElementById('navToggleBtn');
    const navLinksMenu = document.getElementById('navLinksMenu');

    if (navToggleBtn && navLinksMenu) {
        navToggleBtn.addEventListener('click', () => {
            navLinksMenu.classList.toggle('show');
        });
    }

    // 2. Cierre de Alertas (Toasts)
    const toastCloseButtons = document.querySelectorAll('.toast-close-btn');
    toastCloseButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const toast = e.target.closest('.alert-toast');
            if (toast) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-6px)';
                toast.style.transition = 'all 0.2s ease';
                setTimeout(() => toast.remove(), 200);
            }
        });
    });
});