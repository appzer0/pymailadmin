#!/usr/bin/env python3
# scripts/mail-delete-cron.py
# Dovecot connector for pymailadmin
# To be installed on the ** DOVECOT HOST! **

import mysql.connector
import subprocess
import logging
import sys
from datetime import datetime

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/var/log/mail-delete-cron.log"),
        logging.StreamHandler()
    ]
)

### CHANGEME:

# DATABASE
DB_CONFIG = {
    'host': '',  # MySQL IP
    'user': '', #MySQL db user
    'password': '', # MySql db password
    'database': '', # MySQL db name
    'charset': 'utf8mb4' # charset
}

# SQL REQUESTS

# Customize the following request with your Dovecot users and mailboxes
# field names. Change "users" and "email":
SQL_DELETE_USER_FROM_DOVECOT = "DELETE FROM users WHERE email = %s"

# Now Change "users", "users_enabled" and "users.email" ONLY (do not touch
# the "email" field inside the INNER JOIN!):
SQL_REACTIVATE_USER_TIMEOUT = """
    UPDATE users
    INNER JOIN (
        SELECT email FROM pymailadmin_rekey_pending
        WHERE created_at < NOW() - INTERVAL 15 MINUTE
    ) AS expired ON users.email = expired.email
    SET users.enabled = 1
"""

### END OF CHANGEME

# Do not touch the following ones:
SQL_SELECT_PENDING_DELETION = "SELECT email FROM pymailadmin_deletion_pending WHERE created_at < NOW() - INTERVAL 48 HOUR"
SQL_DELETE_PENDING_ENTRY = "DELETE FROM pymailadmin_deletion_pending WHERE email = %s"
SQL_CLEANUP_EXPIRED_REKEY = "DELETE FROM pymailadmin_rekey_pending WHERE created_at < NOW() - INTERVAL 15 MINUTE"

# DELETIONS WITH DOVEADM
def delete_mailbox_with_doveadm(email):
    try:
        # Delete user (files, indexes, etc.)
        subprocess.run(
            ["doveadm", "user", "delete", email],
            capture_output=True,
            check=True,
            timeout=60
        )
        # Delete related mailboxes
        subprocess.run(
            ["doveadm", "mailbox", "delete", "-A", "-u", email],
            capture_output=True,
            check=True,
            timeout=60
        )
        logging.info(f"[DOVEADM] Deleted mailbox for: {email}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"[DOVEADM] Deletion failed for {email}: {e.stderr.decode()}")
        return False
    except Exception as e:
        logging.error(f"[DOVEADM] Unexpected error for {email}: {e}")
        return False

# MAIN FUNCTION
def run_cron():
    logging.info("Démarrage du cron de suppression des boîtes mail")

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Deletions pending
        cursor.execute(SQL_SELECT_PENDING_DELETION)
        pending = cursor.fetchall()

        if not pending:
            logging.info("Aucune boîte à supprimer.")
        else:
			# Deletions occur HERE
            logging.info(f"{len(pending)} boîte(s) trouvée(s) pour suppression")

            for record in pending:
                email = record['email']
                if delete_mailbox_with_doveadm(email):
                    # Delete account/user/mailbox from Dovecot database
                    cursor.execute(SQL_DELETE_USER_FROM_DOVECOT, (email,))
                    # Cleanup pending deletion
                    cursor.execute(SQL_DELETE_PENDING_ENTRY, (email,))
                    logging.info(f"[DB] Deletion pending cleaned for: {email}")

        # Expired rekeys pending
        cursor.execute(SQL_CLEANUP_EXPIRED_REKEY)
        logging.info("Cleanup of expired rekey_pending (> 15 min)")

        # Reactivate mailbox after rekey time has expired
        cursor.execute(SQL_REACTIVATE_USER_TIMEOUT)
        logging.info("Reactivating users after rekey_pending have expired")

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        logging.error(f"Critical error: {e}")
        sys.exit(1)

    logging.info("Done.")

# RUN
if __name__ == "__main__":
    run_cron()
