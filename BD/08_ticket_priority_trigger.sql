/*
Trigger: calcula ticket.priority automáticamente a partir de ticket_priority_matrix.

Reglas:
- Busca (impact, urgency) activo en ticket_priority_matrix.
- Si existe, asigna NEW.priority.
- Si NO existe, deja la prioridad actual (fallback) para no romper inserts,
  pero lo recomendable es mantener la matriz completa 3x3 activa.
*/

BEGIN;

CREATE OR REPLACE FUNCTION trg_ticket_set_priority()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_priority priority_level;
BEGIN
  -- Solo recalcular si es INSERT o si cambió impact/urgency
  IF (TG_OP = 'INSERT')
     OR (NEW.impact IS DISTINCT FROM OLD.impact)
     OR (NEW.urgency IS DISTINCT FROM OLD.urgency) THEN

    SELECT tpm.priority
      INTO v_priority
    FROM ticket_priority_matrix tpm
    WHERE tpm.impact = NEW.impact
      AND tpm.urgency = NEW.urgency
      AND tpm.active = true
    LIMIT 1;

    IF v_priority IS NOT NULL THEN
      NEW.priority := v_priority;
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS ticket_set_priority ON ticket;
CREATE TRIGGER ticket_set_priority
BEFORE INSERT OR UPDATE OF impact, urgency ON ticket
FOR EACH ROW EXECUTE FUNCTION trg_ticket_set_priority();

COMMIT;