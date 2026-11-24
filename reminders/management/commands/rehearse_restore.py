"""Create a local backup and restore into a NEW isolated database; never overwrite one."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import psycopg
from psycopg import sql

class Command(BaseCommand):
    help="Rehearse backup/restore on the loopback development server only."
    def handle(self,*args,**kwargs):
        config=settings.DATABASES["default"]
        if not settings.DEBUG or settings.EMAIL_BACKEND_MODE!="fake" or config["HOST"] not in ["127.0.0.1","localhost","::1"]:
            raise CommandError("Restore rehearsal requires the local fake-email development database.")
        stamp=timezone.now().strftime("%Y%m%d%H%M%S")
        target="restore_rehearsal_"+stamp
        folder=settings.BASE_DIR/".runtime"/"backups"
        folder.mkdir(parents=True,exist_ok=True)
        backup=folder/(target+".dump")
        bindir=settings.BASE_DIR/".runtime"/"postgresql"/"pgsql"/"bin"
        def binary(name):
            bundled=bindir/(name+(".exe" if os.name=="nt" else ""))
            return str(bundled) if bundled.exists() else shutil.which(name)
        params={"host":config["HOST"],"port":config["PORT"],"user":config["USER"],"password":config["PASSWORD"]}
        environment=os.environ.copy()
        environment["PGPASSWORD"]=config["PASSWORD"]
        common=["-h",config["HOST"],"-p",str(config["PORT"]),"-U",config["USER"]]
        if not binary("pg_dump") or not binary("pg_restore"):
            raise CommandError("PostgreSQL client tools are required.")
        subprocess.run([binary("pg_dump"),*common,"-Fc","--no-owner","--no-acl","-f",str(backup),config["NAME"]],
            env=environment,check=True,capture_output=True)
        with psycopg.connect(dbname="postgres",autocommit=True,**params) as control:
            control.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))
        subprocess.run([binary("pg_restore"),*common,"--no-owner","--no-acl","-d",target,str(backup)],
            env=environment,check=True,capture_output=True)
        tables=["projects_project","projects_membership","projects_group","projects_groupmembership","tasks_task",
                "reminders_emailoccurrence","reminders_outboundmessage","reminders_deliveryevent"]
        def fingerprint(database):
            result={}
            with psycopg.connect(dbname=database,**params) as conn:
                for table in tables:
                    rows=conn.execute(sql.SQL("SELECT row_to_json(t)::text FROM {} t ORDER BY id").format(sql.Identifier(table))).fetchall() if table!="reminders_deliveryevent" else conn.execute("SELECT row_to_json(t)::text FROM reminders_deliveryevent t ORDER BY event_id").fetchall()
                    result[table]={"count":len(rows),"sha256":hashlib.sha256("\n".join(row[0] for row in rows).encode()).hexdigest()}
            return result
        original=fingerprint(config["NAME"]); restored=fingerprint(target)
        report={"passed":original==restored,"database":target,"backup":str(backup),"tables":original,
                "note":"Local snapshot only. Daily production backup scheduling remains deployment-specific."}
        out=settings.BASE_DIR/"artifacts"/"restore-results.json";out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(report,indent=2))
        if not report["passed"]: raise CommandError("Restored identities differ; inspect restore-results.json.")
        self.stdout.write(f"Restore verified: {target}; {len(tables)} tables matched.")
