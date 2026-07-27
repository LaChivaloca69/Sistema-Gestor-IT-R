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

        const storedValue = localStorage.getItem(storageKey);
        const isCollapsed = storedValue === "1";
        setCollapsed(isCollapsed);

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
        const initialCollapsed = hasActive ? false : stored === "1";

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

    const gotoInput = document.getElementById("sidebar-goto");
    const gotoResults = document.getElementById("sidebar-goto-results");
    if (gotoInput && gotoResults) {
        const navLinks = Array.from(document.querySelectorAll(".sidebar-link[href]")).map((link) => ({
            href: link.getAttribute("href"),
            label: (link.textContent || "").replace(/\s+/g, " ").trim(),
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
            const matches = navLinks.filter((item) => item.haystack.includes(q)).slice(0, 8);
            if (!matches.length) {
                gotoResults.innerHTML = `<div class="sidebar-search__empty">Sin coincidencias</div>`;
                gotoResults.hidden = false;
                return;
            }
            gotoResults.innerHTML = matches
                .map((item) => `<a class="sidebar-search__item" href="${item.href}">${item.label}</a>`)
                .join("");
            gotoResults.hidden = false;
        };

        gotoInput.addEventListener("input", () => renderResults(gotoInput.value));
        gotoInput.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                gotoInput.value = "";
                hideResults();
            }
            if (event.key === "Enter") {
                const first = gotoResults.querySelector(".sidebar-search__item");
                if (first) {
                    event.preventDefault();
                    window.location = first.getAttribute("href");
                }
            }
        });
        document.addEventListener("click", (event) => {
            if (!event.target.closest(".sidebar-search, #sidebar-goto-results")) {
                hideResults();
            }
        });
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
