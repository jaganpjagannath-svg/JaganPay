/**
 * JaganPay Core Interactive Scripts & PWA Management
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Theme Management (Dark / Light)
    const currentTheme = localStorage.getItem("jaganpay_theme") || "dark";
    document.documentElement.setAttribute("data-theme", currentTheme);
    updateThemeIcon(currentTheme);

    const themeToggleBtn = document.getElementById("themeToggle");
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", () => {
            const active = document.documentElement.getAttribute("data-theme");
            const newTheme = active === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", newTheme);
            localStorage.setItem("jaganpay_theme", newTheme);
            updateThemeIcon(newTheme);
        });
    }

    function updateThemeIcon(theme) {
        const icon = document.getElementById("themeIcon");
        if (!icon) return;
        if (theme === "light") {
            icon.className = "fas fa-moon text-indigo-400";
        } else {
            icon.className = "fas fa-sun text-yellow-400";
        }
    }

    // 2. Auto Dismiss Flash Alerts after 6 seconds
    const alerts = document.querySelectorAll(".auto-dismiss-alert");
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 500);
        }, 6000);
    });

    // 3. Global Copy To Clipboard Helper
    window.copyToClipboard = function(text, label = "Copied!") {
        navigator.clipboard.writeText(text).then(() => {
            showToast(label, "success");
        }).catch(err => {
            console.error("Failed to copy:", err);
        });
    };

    // 4. Simple Toast Notification System
    window.showToast = function(message, type = "info") {
        let container = document.getElementById("toastContainer");
        if (!container) {
            container = document.createElement("div");
            container.id = "toastContainer";
            container.className = "fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none";
            document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        const bgColors = {
            success: "bg-emerald-600 border-emerald-400",
            warning: "bg-amber-600 border-amber-400",
            danger: "bg-rose-600 border-rose-400",
            info: "bg-cyan-600 border-cyan-400"
        };
        const colorClass = bgColors[type] || bgColors.info;

        toast.className = `${colorClass} text-white px-4 py-3 rounded-xl shadow-xl border text-sm font-medium transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto`;
        toast.innerText = message;

        container.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.classList.remove("translate-y-2", "opacity-0");
        }, 10);

        // Animate out
        setTimeout(() => {
            toast.classList.add("translate-y-2", "opacity-0");
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    };

    // 5. Debounced Search Functionality
    window.debounce = function(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    };
});

// =====================================================================
// PWA INSTALLATION & SERVICE WORKER LOGIC
// =====================================================================

let deferredPrompt = null;

if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw.js").then((reg) => {
            console.log("[PWA] Service Worker active with scope:", reg.scope);
        }).catch((err) => {
            console.warn("[PWA] Service Worker registration failed:", err);
        });
    });
}

window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;

    // Show navbar install buttons
    const headerBtns = document.querySelectorAll(".pwa-install-trigger");
    headerBtns.forEach(btn => btn.classList.remove("hidden"));

    // Show floating bottom banner if not dismissed this session
    const banner = document.getElementById("pwaInstallBanner");
    const dismissed = sessionStorage.getItem("pwa_install_dismissed");
    if (banner && !dismissed) {
        banner.classList.remove("hidden");
        banner.classList.add("flex");
    }
});

window.triggerPwaInstall = function() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === "accepted") {
                showToast("Installing JaganPay App...", "success");
            }
            deferredPrompt = null;
            dismissPwaBanner();
        });
    } else {
        // Fallback for iOS or already triggered browsers
        const isIos = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
        if (isIos) {
            const modal = document.getElementById("iosInstallModal");
            if (modal) modal.classList.remove("hidden");
        } else {
            // Check standalone mode
            if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone) {
                showToast("JaganPay is already installed and running!", "success");
            } else {
                showToast("Click your browser menu (⋮ or Share) and select 'Install' or 'Add to Home Screen'.", "info");
            }
        }
    }
};

window.dismissPwaBanner = function() {
    const banner = document.getElementById("pwaInstallBanner");
    if (banner) {
        banner.classList.add("hidden");
        banner.classList.remove("flex");
    }
    sessionStorage.setItem("pwa_install_dismissed", "true");
};

window.closeIosModal = function() {
    const modal = document.getElementById("iosInstallModal");
    if (modal) modal.classList.add("hidden");
};

window.addEventListener("appinstalled", () => {
    showToast("JaganPay app installed successfully!", "success");
    dismissPwaBanner();
    const headerBtns = document.querySelectorAll(".pwa-install-trigger");
    headerBtns.forEach(btn => btn.classList.add("hidden"));
});
