#!/usr/bin/env python3
# scripts/pymailadmin-cron.py
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
        logging.FileHandler("/var/log/pymailadmin-cron.log"),
        logging.StreamHandler()
    ]
)

### CHANGEME:

# DATABASE
DB_CONFIG = {
    'host': '',  # MySQL IP
    'user': '',  # MySQL db user
    'password': '',  # MySQL db password
    'database': '',  # MySQL db name
    'charset': 'utf8mb4'  # charset
}

# SQL REQUESTS

# Customize the following requests with your Dovecot users and mailboxes
# field names. Change "users" and "email":
SQL_DELETE_USER_FROM_DOVECOT = "DELETE FROM users WHERE email = %s"

# Change "users", "users.active" and "users.email" ONLY (do NOT touch
# the "email" field inside the INNER JOIN!):
SQL_REACTIVATE_USER_TIMEOUT = """
    UPDATE users
    INNER JOIN (
        SELECT email FROM pymailadmin_rekey_pending
        WHERE created_at < NOW() - INTERVAL 15 MINUTE
    ) AS expired ON users.email = expired.email
    SET users.active = 1
"""

# For mailbox creation - adapt "users", "active", and "email":
SQL_SELECT_PENDING_CREATION = """
    SELECT u.email, u.id as user_id
    FROM users u
    INNER JOIN pymailadmin_ownerships o ON u.id = o.user_id
    LEFT JOIN pymailadmin_creation_pending cp ON u.email = cp.email
    WHERE u.active = 1 
    AND cp.email IS NOT NULL
    AND cp.created_at < NOW() - INTERVAL 2 MINUTE
"""

### END OF CHANGEME

# Do not touch the following ones:
SQL_SELECT_PENDING_DELETION = "SELECT email FROM pymailadmin_deletion_pending WHERE created_at < NOW() - INTERVAL 48 HOUR"
SQL_DELETE_PENDING_ENTRY = "DELETE FROM pymailadmin_deletion_pending WHERE email = %s"
SQL_CLEANUP_EXPIRED_REKEY = "DELETE FROM pymailadmin_rekey_pending WHERE created_at < NOW() - INTERVAL 15 MINUTE"
SQL_DELETE_CREATION_PENDING = "DELETE FROM pymailadmin_creation_pending WHERE email = %s"

# MAILBOX CREATION WITH DOVEADM
def create_mailbox_with_doveadm(email):
    """
    Create mailbox structure with doveadm.
    This initializes the mailbox directories for mail_crypt plugin.
    """
    try:
        # Force mailbox creation by triggering an IMAP login simulation
        # This creates the necessary directory structure
        result = subprocess.run(
            ["doveadm", "mailbox", "create", "-u", email, "INBOX"],
            capture_output=True,
            check=True,
            timeout=30
        )
        logging.info(f"[DOVEADM] Created mailbox for: {email}")
        return True
    except subprocess.CalledProcessError as e:
        # Mailbox might already exist, check stderr
        stderr = e.stderr.decode()
        if "already exists" in stderr.lower():
            logging.warning(f"[DOVEADM] Mailbox already exists for: {email}")
            return True
        logging.error(f"[DOVEADM] Creation failed for {email}: {stderr}")
        return False
    except Exception as e:
        logging.error(f"[DOVEADM] Unexpected error creating {email}: {e}")
        return False

# DELETIONS WITH DOVEADM
def delete_mailbox_with_doveadm(email):
    """
    Delete mailbox with doveadm.
    Removes user data, indexes, and mail_crypt keys.
    """
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
            ["doveadm", "mailbox", "delete", "-A", "-u", email, "*"],
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
    logging.info("=== Starting pymailadmin cron task ===")

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # ============================================
        # 1. PROCESS MAILBOX CREATIONS
        # ============================================
        logging.info("[1/4] Processing pending mailbox creations...")
        
        cursor.execute(SQL_SELECT_PENDING_CREATION)
        pending_creations = cursor.fetchall()

        if not pending_creations:
            logging.info("  → No mailbox to create.")
        else:
            logging.info(f"  → {len(pending_creations)} mailbox(es) pending creation")

            for record in pending_creations:
                email = record['email']
                if create_mailbox_with_doveadm(email):
                    # Cleanup creation pending
                    cursor.execute(SQL_DELETE_CREATION_PENDING, (email,))
                    logging.info(f"  → [DB] Creation pending cleaned for: {email}")
                    conn.commit()

        # ============================================
        # 2. PROCESS MAILBOX DELETIONS
        # ============================================
        logging.info("[2/4] Processing pending mailbox deletions...")
        
        cursor.execute(SQL_SELECT_PENDING_DELETION)
        pending_deletions = cursor.fetchall()

        if not pending_deletions:
            logging.info("  → No mailbox to delete.")
        else:
            logging.info(f"  → {len(pending_deletions)} mailbox(es) marked for deletion")

            for record in pending_deletions:
                email = record['email']
                if delete_mailbox_with_doveadm(email):
                    # Delete account/user/mailbox from Dovecot database
                    cursor.execute(SQL_DELETE_USER_FROM_DOVECOT, (email,))
                    # Cleanup pending deletion
                    cursor.execute(SQL_DELETE_PENDING_ENTRY, (email,))
                    logging.info(f"  → [DB] Deletion pending cleaned for: {email}")
                    conn.commit()

        # ============================================
        # 3. CLEANUP EXPIRED REKEY PENDING
        # ============================================
        logging.info("[3/4] Cleaning up expired rekey_pending (> 15 min)...")
        
        cursor.execute(SQL_CLEANUP_EXPIRED_REKEY)
        deleted_rekeys = cursor.rowcount
        logging.info(f"  → {deleted_rekeys} expired rekey(s) cleaned")
        conn.commit()

        # ============================================
        # 4. REACTIVATE USERS AFTER REKEY TIMEOUT
        # ============================================
        logging.info("[4/4] Reactivating users after rekey timeout...")
        
        cursor.execute(SQL_REACTIVATE_USER_TIMEOUT)
        reactivated = cursor.rowcount
        logging.info(f"  → {reactivated} user(s) reactivated")
        conn.commit()

        cursor.close()
        conn.close()

        logging.info("=== pymailadmin cron task completed successfully ===")

    except mysql.connector.Error as e:
        logging.error(f"[MYSQL ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"[CRITICAL ERROR] {e}")
        sys.exit(1)

# RUN
if __name__ == "__main__":
    run_cron()
