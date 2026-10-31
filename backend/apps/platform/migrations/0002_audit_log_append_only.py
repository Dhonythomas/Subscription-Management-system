from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("platform", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log entries are append-only';
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER audit_log_no_update_delete
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_mutation();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log;
            DROP FUNCTION IF EXISTS prevent_audit_log_mutation();
            """,
        ),
    ]
