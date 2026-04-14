/*
Seed de catálogos iniciales (recomendado para arrancar):

- department: Producción, Calidad, RH, Mantenimiento, Almacén, IT, Compras
- ticket_category: categorías base IT (con parent-child si quieres crecer después)
- support_group: grupos de soporte
- asset_category: categorías base de inventario

Este script usa ON CONFLICT DO NOTHING para que sea idempotente.
*/

BEGIN;

-- -------------------------
-- Departments
-- -------------------------
INSERT INTO department (name, cost_center, active) VALUES
  ('PRODUCCION',   NULL, true),
  ('CALIDAD',      NULL, true),
  ('RH',           NULL, true),
  ('MANTENIMIENTO',NULL, true),
  ('ALMACEN',      NULL, true),
  ('IT',           NULL, true),
  ('COMPRAS',      NULL, true)
ON CONFLICT (name) DO NOTHING;

-- -------------------------
-- Ticket Categories (root-level)
-- Nota: si quieres jerarquía (parent/child), se puede extender.
-- -------------------------
INSERT INTO ticket_category (name, parent_id, active) VALUES
  ('HARDWARE',   NULL, true),
  ('SOFTWARE',   NULL, true),
  ('RED',        NULL, true),
  ('ACCESOS',    NULL, true),
  ('CORREO',     NULL, true),
  ('IMPRESORAS', NULL, true),
  ('SOLICITUD',  NULL, true),
  ('OTRO',       NULL, true)
ON CONFLICT (name) DO NOTHING;

-- -------------------------
-- Support Groups
-- -------------------------
INSERT INTO support_group (name, active) VALUES
  ('IT-HELPDESK', true),
  ('IT-INFRA',    true),
  ('IT-APPS',     true)
ON CONFLICT (name) DO NOTHING;

-- -------------------------
-- Asset Categories (inventory)
-- -------------------------
INSERT INTO asset_category (name, parent_category_id, active) VALUES
  ('LAPTOP',        NULL, true),
  ('PC',            NULL, true),
  ('MONITOR',       NULL, true),
  ('TECLADO',       NULL, true),
  ('MOUSE',         NULL, true),
  ('CABLE',         NULL, true),
  ('ROUTER',        NULL, true),
  ('SWITCH',        NULL, true),
  ('ACCESSPOINT',   NULL, true),
  ('UPS',           NULL, true),
  ('IMPRESORA',     NULL, true),
  ('GABINETE',      NULL, true),
  ('HERRAMIENTA',   NULL, true)
ON CONFLICT (name) DO NOTHING;

COMMIT;