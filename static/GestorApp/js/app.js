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

    // ---- Toasts (feedback inmediato) ----
    const initToasts = () => {
        const stack = document.getElementById("toast-stack");
        if (!stack) {
            return;
        }

        const dismiss = (toast) => {
            if (!toast || toast.classList.contains("is-leaving")) {
                return;
            }
            toast.classList.add("is-leaving");
            window.setTimeout(() => toast.remove(), 200);
        };

        Array.from(stack.querySelectorAll(".app-toast")).forEach((toast) => {
            const closeBtn = toast.querySelector(".app-toast__close");
            if (closeBtn) {
                closeBtn.addEventListener("click", () => dismiss(toast));
            }
            if (toast.dataset.autohide === "1") {
                window.setTimeout(() => dismiss(toast), 5200);
            }
        });
    };

    // ---- Confirmacion destructiva ----
    const showConfirm = ({ title, message, confirmLabel }) =>
        new Promise((resolve) => {
            const overlay = document.createElement("div");
            overlay.className = "confirm-overlay";
            overlay.innerHTML = `
                <div class="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
                    <h2 id="confirm-title">${title}</h2>
                    <p>${message}</p>
                    <div class="confirm-dialog__actions">
                        <button type="button" class="btn btn-outline-secondary" data-confirm-cancel>Cancelar</button>
                        <button type="button" class="btn btn-danger" data-confirm-ok>${confirmLabel}</button>
                    </div>
                </div>
            `;
            const finish = (value) => {
                overlay.remove();
                document.removeEventListener("keydown", onKey);
                resolve(value);
            };
            const onKey = (event) => {
                if (event.key === "Escape") {
                    finish(false);
                }
            };
            overlay.addEventListener("click", (event) => {
                if (event.target === overlay || event.target.matches("[data-confirm-cancel]")) {
                    finish(false);
                }
                if (event.target.matches("[data-confirm-ok]")) {
                    finish(true);
                }
            });
            document.addEventListener("keydown", onKey);
            document.body.appendChild(overlay);
            overlay.querySelector("[data-confirm-ok]")?.focus();
        });

    document.addEventListener("click", async (event) => {
        const link = event.target.closest("a[href*='/eliminar/'], a[href*='/delete/']");
        if (!link) {
            return;
        }
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
            return;
        }

        event.preventDefault();
        const confirmed = await showConfirm({
            title: "Eliminar registro",
            message:
                "Esta accion no se puede deshacer. El registro se eliminara de forma permanente. " +
                "Si solo quieres ocultarlo del historial, usa Archivar en Admin.",
            confirmLabel: "Si, eliminar",
        });
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

    // Confirmacion en formularios de borrado (paginas confirm_delete)
    document.addEventListener("submit", async (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) {
            return;
        }
        if (!form.matches("form[data-confirm-delete], .confirm-delete-form")) {
            const submitter = event.submitter;
            const isDeletePage =
                /\/delete\//i.test(window.location.pathname) &&
                submitter &&
                (submitter.classList.contains("btn-danger") || /eliminar/i.test(submitter.textContent || ""));
            if (!isDeletePage) {
                return;
            }
        }
        if (form.dataset.confirmAccepted === "1") {
            return;
        }
        event.preventDefault();
        const confirmed = await showConfirm({
            title: "Confirmar eliminacion",
            message: "Se eliminara el registro de forma permanente. Esta accion no se puede deshacer.",
            confirmLabel: "Si, eliminar",
        });
        if (!confirmed) {
            return;
        }
        form.dataset.confirmAccepted = "1";
        form.requestSubmit();
    });

    // ---- Filas clicables ----
    document.addEventListener("click", (event) => {
        const row = event.target.closest("tr.table-row-click[data-href]");
        if (!row) {
            return;
        }
        if (event.target.closest("a, button, input, select, textarea, .dropdown, .row-actions")) {
            return;
        }
        window.location = row.dataset.href;
    });

    // ---- Sidebar ----
    const appShell = document.querySelector(".app-shell");
    const toggle = document.querySelector(".sidebar-toggle");
    const sidebar = document.querySelector(".sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    const MOBILE_MQ = window.matchMedia("(max-width: 1100px)");
    const COLLAPSE_KEY = "sidebar-collapsed";
    const FAV_KEY = "sidebar-favorites";
    const RECENT_KEY = "sidebar-recents";
    const DEFAULT_FAVS = ["tickets", "equipos", "ordenes", "mantenimientos"];
    const RECENT_SKIP = new Set(["home", "calendario"]);


    const isMobile = () => MOBILE_MQ.matches;

    const setSidebarCollapsed = (isCollapsed) => {
        if (!appShell) {
            return;
        }
        appShell.classList.toggle("sidebar-collapsed", isCollapsed);
        if (sidebar) {
            sidebar.setAttribute("aria-hidden", isCollapsed && isMobile() ? "true" : "false");
        }
        if (toggle) {
            toggle.setAttribute("aria-expanded", (!isCollapsed).toString());
        }
        if (backdrop) {
            backdrop.hidden = isCollapsed || !isMobile();
        }
        document.body.classList.toggle("sidebar-drawer-open", !isCollapsed && isMobile());
        if (!isMobile()) {
            localStorage.setItem(COLLAPSE_KEY, isCollapsed ? "1" : "0");
        }
    };

    if (appShell && toggle && sidebar) {
        const initialCollapsed = isMobile() ? true : localStorage.getItem(COLLAPSE_KEY) === "1";
        setSidebarCollapsed(initialCollapsed);

        toggle.addEventListener("click", () => {
            const nextState = !appShell.classList.contains("sidebar-collapsed");
            setSidebarCollapsed(nextState);
        });

        if (backdrop) {
            backdrop.addEventListener("click", () => setSidebarCollapsed(true));
        }

        MOBILE_MQ.addEventListener("change", () => {
            setSidebarCollapsed(isMobile() ? true : localStorage.getItem(COLLAPSE_KEY) === "1");
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && isMobile() && !appShell.classList.contains("sidebar-collapsed")) {
                setSidebarCollapsed(true);
            }
        });
    }

    // Acordeon: solo una seccion abierta (siempre la del item activo al cargar)
    const sections = Array.from(document.querySelectorAll(".sidebar-section"));
    const setSectionCollapsed = (section, isCollapsed) => {
        const sectionToggle = section.querySelector(".sidebar-section-toggle");
        section.classList.toggle("collapsed", isCollapsed);
        if (sectionToggle) {
            sectionToggle.setAttribute("aria-expanded", (!isCollapsed).toString());
        }
    };

    sections.forEach((section) => {
        const hasActive = Boolean(section.querySelector(".sidebar-link.active"));
        setSectionCollapsed(section, !hasActive);

        const sectionToggle = section.querySelector(".sidebar-section-toggle");
        if (!sectionToggle) {
            return;
        }
        sectionToggle.addEventListener("click", () => {
            const willOpen = section.classList.contains("collapsed");
            sections.forEach((other) => setSectionCollapsed(other, true));
            if (willOpen) {
                setSectionCollapsed(section, false);
            }
        });
    });

    if (sections.length && !sections.some((section) => !section.classList.contains("collapsed"))) {
        setSectionCollapsed(sections[0], false);
    }

    // Favoritos
    const favHost = document.getElementById("sidebar-favorites");
    const favList = document.getElementById("sidebar-favorites-list");
    const navLinks = Array.from(document.querySelectorAll("#sidebar-nav .sidebar-link[data-nav-id]"));

    const readFavorites = () => {
        try {
            const raw = localStorage.getItem(FAV_KEY);
            if (raw === null) {
                return DEFAULT_FAVS.filter((id) => navLinks.some((link) => link.dataset.navId === id));
            }
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed.filter((id) => typeof id === "string") : [];
        } catch (error) {
            return [];
        }
    };

    let favoriteIds = readFavorites();

    const saveFavorites = () => {
        localStorage.setItem(FAV_KEY, JSON.stringify(favoriteIds));
    };

    const renderFavorites = () => {
        if (!favHost || !favList) {
            return;
        }
        favList.innerHTML = "";
        const items = favoriteIds
            .map((id) => navLinks.find((link) => link.dataset.navId === id))
            .filter(Boolean);

        navLinks.forEach((link) => {
            const isFav = favoriteIds.includes(link.dataset.navId);
            link.classList.toggle("is-favorite", isFav);
            const pin = link.querySelector("[data-fav-pin]");
            if (pin) {
                pin.setAttribute("aria-label", isFav ? "Quitar de favoritos" : "Fijar en favoritos");
                pin.title = isFav ? "Quitar de favoritos" : "Fijar en favoritos";
            }
        });

        if (!items.length) {
            favHost.hidden = true;
        } else {
            favHost.hidden = false;
            items.forEach((link) => {
                const clone = link.cloneNode(true);
                clone.classList.add("sidebar-link--favorite");
                const pin = clone.querySelector("[data-fav-pin]");
                if (pin) {
                    pin.remove();
                }
                favList.appendChild(clone);
            });
        }
        renderRecents();
    };

    const toggleFavorite = (navId) => {
        if (!navId) {
            return;
        }
        if (favoriteIds.includes(navId)) {
            favoriteIds = favoriteIds.filter((id) => id !== navId);
        } else {
            favoriteIds = [...favoriteIds, navId].slice(0, 8);
        }
        saveFavorites();
        renderFavorites();
    };

    // Recientes
    const recentHost = document.getElementById("sidebar-recents");
    const recentList = document.getElementById("sidebar-recents-list");

    const readRecents = () => {
        try {
            const parsed = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
            return Array.isArray(parsed) ? parsed.filter((id) => typeof id === "string") : [];
        } catch (error) {
            return [];
        }
    };

    let recentIds = readRecents();

    const saveRecents = () => {
        localStorage.setItem(RECENT_KEY, JSON.stringify(recentIds));
    };

    const renderRecents = () => {
        if (!recentHost || !recentList) {
            return;
        }
        recentList.innerHTML = "";
        const items = recentIds
            .filter((id) => !favoriteIds.includes(id) && !RECENT_SKIP.has(id))
            .map((id) => navLinks.find((link) => link.dataset.navId === id))
            .filter(Boolean)
            .slice(0, 5);

        if (!items.length) {
            recentHost.hidden = true;
            return;
        }

        recentHost.hidden = false;
        items.forEach((link) => {
            const clone = link.cloneNode(true);
            clone.classList.add("sidebar-link--recent");
            const pin = clone.querySelector("[data-fav-pin]");
            if (pin) {
                pin.remove();
            }
            recentList.appendChild(clone);
        });
    };

    const pushRecent = (navId) => {
        if (!navId || RECENT_SKIP.has(navId)) {
            return;
        }
        recentIds = [navId, ...recentIds.filter((id) => id !== navId)].slice(0, 8);
        saveRecents();
        renderRecents();
    };

    document.addEventListener("click", (event) => {
        const pin = event.target.closest("[data-fav-pin]");
        if (!pin) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        const link = pin.closest(".sidebar-link");
        if (link) {
            toggleFavorite(link.dataset.navId);
        }
    });

    document.addEventListener("keydown", (event) => {
        const pin = event.target.closest?.("[data-fav-pin]");
        if (!pin) {
            return;
        }
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            event.stopPropagation();
            const link = pin.closest(".sidebar-link");
            if (link) {
                toggleFavorite(link.dataset.navId);
            }
        }
    });

    // Cerrar drawer móvil al navegar
    if (sidebar) {
        sidebar.addEventListener("click", (event) => {
            const link = event.target.closest("a.sidebar-link, a.sidebar-search__item");
            if (link && isMobile() && !event.target.closest("[data-fav-pin]")) {
                setSidebarCollapsed(true);
            }
        });
    }

    renderFavorites();
    const activeNav = document.querySelector("#sidebar-nav .sidebar-link.active[data-nav-id]");
    if (activeNav) {
        pushRecent(activeNav.dataset.navId);
    } else {
        renderRecents();
    }

    // Busqueda Ir a... + Ctrl/Cmd+K
    const gotoInput = document.getElementById("sidebar-goto");
    const gotoResults = document.getElementById("sidebar-goto-results");
    const railSearch = document.getElementById("sidebar-rail-search");

    if (gotoInput && gotoResults) {
        const searchable = Array.from(document.querySelectorAll("#sidebar-nav .sidebar-link[href]")).map((link) => ({
            href: link.getAttribute("href"),
            label: (link.querySelector(".sidebar-link__text")?.textContent || link.textContent || "")
                .replace(/\s+/g, " ")
                .trim(),
            icon: link.querySelector(".sidebar-link__icon")?.innerHTML || "",
            haystack: `${link.dataset.navLabel || ""} ${link.textContent || ""}`.toLowerCase(),
        }));

        const hideResults = () => {
            gotoResults.hidden = true;
            gotoResults.innerHTML = "";
        };

        const renderResults = (query) => {
            const q = query.trim().toLowerCase();
            if (!q) {
                hideResults();
                return;
            }
            const matches = searchable.filter((item) => item.haystack.includes(q)).slice(0, 8);
            if (!matches.length) {
                gotoResults.innerHTML = `<div class="sidebar-search__empty">Sin coincidencias</div>`;
                gotoResults.hidden = false;
                return;
            }
            gotoResults.innerHTML = matches
                .map(
                    (item) =>
                        `<a class="sidebar-search__item" href="${item.href}"><span class="sidebar-link__icon">${item.icon}</span><span>${item.label}</span></a>`
                )
                .join("");
            gotoResults.hidden = false;
        };

        const focusSearch = () => {
            if (appShell && appShell.classList.contains("sidebar-collapsed")) {
                setSidebarCollapsed(false);
            }
            window.setTimeout(() => {
                gotoInput.focus();
                gotoInput.select();
            }, 50);
        };

        gotoInput.addEventListener("input", () => renderResults(gotoInput.value));
        gotoInput.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                gotoInput.value = "";
                hideResults();
                gotoInput.blur();
            }
            if (event.key === "Enter") {
                const first = gotoResults.querySelector(".sidebar-search__item");
                if (first) {
                    event.preventDefault();
                    window.location = first.getAttribute("href");
                }
            }
            if (event.key === "ArrowDown") {
                const first = gotoResults.querySelector(".sidebar-search__item");
                if (first) {
                    event.preventDefault();
                    first.focus();
                }
            }
        });

        gotoResults.addEventListener("keydown", (event) => {
            const items = Array.from(gotoResults.querySelectorAll(".sidebar-search__item"));
            const current = document.activeElement;
            const index = items.indexOf(current);
            if (event.key === "ArrowDown" && index < items.length - 1) {
                event.preventDefault();
                items[index + 1].focus();
            }
            if (event.key === "ArrowUp") {
                event.preventDefault();
                if (index <= 0) {
                    gotoInput.focus();
                } else {
                    items[index - 1].focus();
                }
            }
            if (event.key === "Escape") {
                hideResults();
                gotoInput.focus();
            }
        });

        document.addEventListener("click", (event) => {
            if (!event.target.closest(".sidebar-search, #sidebar-goto-results, #sidebar-rail-search")) {
                hideResults();
            }
        });

        document.addEventListener("keydown", (event) => {
            const isK = event.key.toLowerCase() === "k";
            const isSlash = event.key === "/";
            const meta = event.ctrlKey || event.metaKey;
            const target = event.target;
            const inField =
                target &&
                (target.tagName === "INPUT" ||
                    target.tagName === "TEXTAREA" ||
                    target.tagName === "SELECT" ||
                    target.isContentEditable);

            if ((meta && isK) || (isSlash && !inField && !meta && !event.altKey)) {
                event.preventDefault();
                focusSearch();
            }
        });

        if (railSearch) {
            railSearch.addEventListener("click", () => focusSearch());
        }
    }

    // ---- Chips de filtros activos ----
    const initFilterChips = () => {
        Array.from(document.querySelectorAll("form.filters")).forEach((form) => {
            if (form.dataset.chipsReady === "1") {
                return;
            }
            form.dataset.chipsReady = "1";

            const fields = Array.from(
                form.querySelectorAll("input[name], select[name], textarea[name]")
            ).filter((el) => el.type !== "hidden" && el.type !== "submit" && el.type !== "button");

            const chips = [];
            fields.forEach((field) => {
                const name = field.name;
                if (!name) {
                    return;
                }
                let rawValue = "";
                let displayValue = "";
                if (field.tagName === "SELECT") {
                    rawValue = field.value || "";
                    const opt = field.selectedOptions && field.selectedOptions[0];
                    displayValue = (opt && opt.textContent ? opt.textContent : rawValue).trim();
                    const placeholderTexts = ["todos", "todas", "cualquier", "cualquiera", ""];
                    if (!rawValue || placeholderTexts.includes(displayValue.toLowerCase())) {
                        // Si tiene default distinto de vacio (ej. estado=activo), igual mostramos chip
                        const defaultValue = field.dataset.chipDefault;
                        if (defaultValue !== undefined && rawValue === defaultValue) {
                            return;
                        }
                        if (!rawValue) {
                            return;
                        }
                    }
                    const defaultValue = field.dataset.chipDefault;
                    if (defaultValue !== undefined && rawValue === defaultValue) {
                        return;
                    }
                } else {
                    rawValue = (field.value || "").trim();
                    if (!rawValue) {
                        return;
                    }
                    displayValue = rawValue;
                }

                const labelEl = form.querySelector(`label[for="${field.id}"]`);
                const label =
                    field.dataset.chipLabel ||
                    (labelEl ? labelEl.textContent.trim() : name);

                chips.push({ name, label, displayValue });
            });

            if (!chips.length) {
                return;
            }

            const clearLink =
                form.querySelector(".filters-actions a[href]") ||
                form.querySelector("a[href]");
            const clearHref = clearLink ? clearLink.getAttribute("href") : window.location.pathname;

            const host = document.createElement("div");
            host.className = "filter-chips";
            host.setAttribute("aria-label", "Filtros activos");

            const label = document.createElement("span");
            label.className = "filter-chips__label";
            label.textContent = "Filtros activos";
            host.appendChild(label);

            chips.forEach((chip) => {
                const url = new URL(window.location.href);
                url.searchParams.delete(chip.name);
                const anchor = document.createElement("a");
                anchor.className = "filter-chip";
                anchor.href = `${url.pathname}${url.search}${url.hash}`;
                anchor.title = `Quitar filtro ${chip.label}`;
                anchor.innerHTML = `<span>${chip.label}: ${chip.displayValue}</span><span class="filter-chip__x" aria-hidden="true">×</span>`;
                host.appendChild(anchor);
            });

            const clearAll = document.createElement("a");
            clearAll.className = "filter-chips__clear";
            clearAll.href = clearHref;
            clearAll.textContent = "Limpiar todo";
            host.appendChild(clearAll);

            form.insertAdjacentElement("afterend", host);

            // Resaltar boton Limpiar cuando hay filtros
            const clearBtn = form.querySelector(".filters-actions a");
            if (clearBtn) {
                clearBtn.classList.add("btn-outline-danger");
                clearBtn.classList.remove("btn-outline-secondary");
            }
        });
    };

    initToasts();
    initFilterChips();
})();
