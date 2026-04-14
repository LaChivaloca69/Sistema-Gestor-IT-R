/*
Seed de Ticket Priority Matrix (3x3).
Idempotente: usa ON CONFLICT para evitar duplicados.
*/

BEGIN;

INSERT INTO ticket_priority_matrix (impact, urgency, priority, active) VALUES
  ('high',   'high',   'critical', true),
  ('high',   'medium', 'high',     true),
  ('high',   'low',    'medium',   true),

  ('medium', 'high',   'high',     true),
  ('medium', 'medium', 'medium',   true),
  ('medium', 'low',    'low',      true),

  ('low',    'high',   'medium',   true),
  ('low',    'medium', 'low',      true),
  ('low',    'low',    'low',      true)
ON CONFLICT (impact, urgency)
DO UPDATE SET
  priority = EXCLUDED.priority,
  active   = EXCLUDED.active;

COMMIT;