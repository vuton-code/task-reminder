from django.db import migrations

SQL = """
CREATE FUNCTION task_reminder_integrity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (
   SELECT 1 FROM projects_project p WHERE NOT EXISTS (
     SELECT 1 FROM projects_membership m
     WHERE m.project_id=p.id AND m.account_id=p.owner_id AND m.left_at IS NULL
   )
 ) THEN RAISE EXCEPTION 'Project owner must have active membership'; END IF;
 IF EXISTS (
   SELECT 1 FROM tasks_task t JOIN projects_membership m ON m.id=t.assignee_id
   WHERE m.project_id<>t.project_id OR m.left_at IS NOT NULL
 ) THEN RAISE EXCEPTION 'Task assignee must be active in the same project'; END IF;
 IF EXISTS (
   SELECT 1 FROM projects_groupmembership gm
   JOIN projects_group g ON g.id=gm.group_id
   JOIN projects_membership m ON m.id=gm.membership_id
   WHERE g.project_id<>m.project_id OR m.left_at IS NOT NULL
 ) THEN RAISE EXCEPTION 'Group member must be active in the same project'; END IF;
 RETURN NULL;
END; $$;
CREATE CONSTRAINT TRIGGER project_integrity AFTER INSERT OR UPDATE OR DELETE ON projects_project
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION task_reminder_integrity();
CREATE CONSTRAINT TRIGGER membership_integrity AFTER INSERT OR UPDATE OR DELETE ON projects_membership
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION task_reminder_integrity();
CREATE CONSTRAINT TRIGGER task_integrity AFTER INSERT OR UPDATE ON tasks_task
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION task_reminder_integrity();
CREATE CONSTRAINT TRIGGER group_member_integrity AFTER INSERT OR UPDATE ON projects_groupmembership
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION task_reminder_integrity();
ALTER TABLE tasks_task ADD CONSTRAINT nonempty_task_title CHECK (length(trim(title)) > 0);
ALTER TABLE tasks_task ADD CONSTRAINT description_length CHECK (length(description) <= 10000);
ALTER TABLE projects_project ADD CONSTRAINT nonempty_project_name CHECK (length(trim(name)) > 0);
ALTER TABLE projects_group ADD CONSTRAINT nonempty_group_name CHECK (length(trim(name)) > 0);
CREATE UNIQUE INDEX one_google_identity_per_account ON socialaccount_socialaccount(user_id) WHERE provider='google';
"""
REVERSE = """
DROP INDEX one_google_identity_per_account;
ALTER TABLE projects_group DROP CONSTRAINT nonempty_group_name;
ALTER TABLE projects_project DROP CONSTRAINT nonempty_project_name;
ALTER TABLE tasks_task DROP CONSTRAINT description_length;
ALTER TABLE tasks_task DROP CONSTRAINT nonempty_task_title;
DROP TRIGGER group_member_integrity ON projects_groupmembership;
DROP TRIGGER task_integrity ON tasks_task;
DROP TRIGGER membership_integrity ON projects_membership;
DROP TRIGGER project_integrity ON projects_project;
DROP FUNCTION task_reminder_integrity();
"""

class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0001_initial"), ("tasks", "0001_initial"),
        ("socialaccount", "0006_alter_socialaccount_extra_data"),
    ]
    operations = [migrations.RunSQL(SQL, REVERSE)]
