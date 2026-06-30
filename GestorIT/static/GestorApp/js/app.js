(function () {
    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    };

    const tokenInput = document.querySelector("#csrf-token input[name=csrfmiddlewaretoken]");
    const csrfToken = tokenInput ? tokenInput.value : getCookie("csrftoken");

    document.addEventListener("click", (event) => {
        const link = event.target.closest("a[href*='/eliminar/']");
        if (!link) {
            return;
        }
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
            return;
        }

        event.preventDefault();
        const confirmed = window.confirm("Esta accion no se puede deshacer. Deseas eliminar el registro?");
        if (!confirmed) {
            return;
        }

        fetch(link.href, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest",
            },
        })
            .then((response) => {
                if (response.redirected) {
                    window.location = response.url;
                    return;
                }
                window.location.reload();
            })
            .catch(() => {
                window.location = link.href;
            });
    });

    const appShell = document.querySelector(".app-shell");
    const toggle = document.querySelector(".sidebar-toggle");
    const sidebar = document.querySelector(".sidebar");
    if (appShell && toggle) {
        const storageKey = "sidebar-collapsed";
        const setCollapsed = (isCollapsed) => {
            appShell.classList.toggle("sidebar-collapsed", isCollapsed);
            if (sidebar) {
                sidebar.hidden = isCollapsed;
                sidebar.setAttribute("aria-hidden", isCollapsed.toString());
            }
            toggle.setAttribute("aria-expanded", (!isCollapsed).toString());
        };

        const defaultCollapsed = appShell.dataset.sidebarDefault === "collapsed";
        const storedValue = localStorage.getItem(storageKey);
        const shouldUseStored = !defaultCollapsed && storedValue !== null;
        setCollapsed(shouldUseStored ? storedValue === "1" : defaultCollapsed);

        toggle.addEventListener("click", () => {
            const nextState = !appShell.classList.contains("sidebar-collapsed");
            setCollapsed(nextState);
            localStorage.setItem(storageKey, nextState ? "1" : "0");
        });
    }

    Array.from(document.querySelectorAll(".sidebar-section")).forEach((section, index) => {
        const sectionToggle = section.querySelector(".sidebar-section-toggle");
        if (!sectionToggle) {
            return;
        }

        const key = section.dataset.section || `section-${index}`;
        const storageKey = `sidebar-section-${key}`;
        const hasActive = Boolean(section.querySelector(".sidebar-link.active"));
        const stored = localStorage.getItem(storageKey);
        const initialCollapsed = stored === null ? !hasActive : stored === "1";

        const setCollapsed = (isCollapsed) => {
            section.classList.toggle("collapsed", isCollapsed);
            sectionToggle.setAttribute("aria-expanded", (!isCollapsed).toString());
        };

        setCollapsed(initialCollapsed);

        sectionToggle.addEventListener("click", () => {
            const nextCollapsed = !section.classList.contains("collapsed");
            setCollapsed(nextCollapsed);
            localStorage.setItem(storageKey, nextCollapsed ? "1" : "0");
        });
    });
})();