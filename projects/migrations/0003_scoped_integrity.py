from importlib import import_module
from django.db import migrations

SQL = """
CREATE OR REPLACE FUNCTION task_reminder_integrity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='projects_project' THEN
   IF EXISTS (SELECT 1 FROM projects_project p WHERE p.id=NEW.id AND NOT EXISTS
     (SELECT 1 FROM projects_membership m WHERE m.project_id=p.id AND m.account_id=p.owner_id AND m.left_at IS NULL))
   THEN RAISE EXCEPTION 'Project owner must have active membership'; END IF;
 ELSIF TG_TABLE_NAME='projects_membership' THEN
   IF EXISTS (SELECT 1 FROM projects_project p WHERE p.id IN (NEW.project_id,OLD.project_id) AND NOT EXISTS
     (SELECT 1 FROM projects_membership m WHERE m.project_id=p.id AND m.account_id=p.owner_id AND m.left_at IS NULL))
   THEN RAISE EXCEPTION 'Project owner must have active membership'; END IF;
   IF EXISTS (SELECT 1 FROM tasks_task t JOIN projects_membership m ON m.id=t.assignee_id
     WHERE m.id IN (NEW.id,OLD.id) AND (m.project_id<>t.project_id OR m.left_at IS NOT NULL))
   THEN RAISE EXCEPTION 'Task assignee must be active in the same project'; END IF;
   IF EXISTS (SELECT 1 FROM projects_groupmembership gm JOIN projects_group g ON g.id=gm.group_id
     JOIN projects_membership m ON m.id=gm.membership_id
     WHERE m.id IN (NEW.id,OLD.id) AND (g.project_id<>m.project_id OR m.left_at IS NOT NULL))
   THEN RAISE EXCEPTION 'Group member must be active in the same project'; END IF;
 ELSIF TG_TABLE_NAME='tasks_task' THEN
   IF EXISTS (SELECT 1 FROM tasks_task t JOIN projects_membership m ON m.id=t.assignee_id
     WHERE t.id=NEW.id AND (m.project_id<>t.project_id OR m.left_at IS NOT NULL))
   THEN RAISE EXCEPTION 'Task assignee must be active in the same project'; END IF;
 ELSIF TG_TABLE_NAME='projects_groupmembership' THEN
   IF EXISTS (SELECT 1 FROM projects_groupmembership gm JOIN projects_group g ON g.id=gm.group_id
     JOIN projects_membership m ON m.id=gm.membership_id
     WHERE gm.id=NEW.id AND (g.project_id<>m.project_id OR m.left_at IS NOT NULL))
   THEN RAISE EXCEPTION 'Group member must be active in the same project'; END IF;
 ELSIF TG_TABLE_NAME='projects_group' THEN
   IF EXISTS (SELECT 1 FROM projects_groupmembership gm JOIN projects_group g ON g.id=gm.group_id
     JOIN projects_membership m ON m.id=gm.membership_id
     WHERE g.id=NEW.id AND (g.project_id<>m.project_id OR m.left_at IS NOT NULL))
   THEN RAISE EXCEPTION 'Group member must be active in the same project'; END IF;
 END IF;
 RETURN NULL;
END; $$;
CREATE CONSTRAINT TRIGGER group_integrity AFTER UPDATE ON projects_group
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION task_reminder_integrity();
"""
OLD=import_module("projects.migrations.0002_integrity").SQL.split("CREATE CONSTRAINT TRIGGER")[0].replace("CREATE FUNCTION","CREATE OR REPLACE FUNCTION")
class Migration(migrations.Migration):
    dependencies=[("projects","0002_integrity")]
    operations=[migrations.RunSQL(SQL,"DROP TRIGGER group_integrity ON projects_group;"+OLD)]
