# config_data.py

config = {
    # pymaildmin SQL requests (web admin only, NOT the actual mail server ones, do not modify the following)
    'sql': {
        # Sessions
        'insert_session': "INSERT INTO pymailadmin_sessions (id, data, expires_at) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE data = VALUES(data), expires_at = VALUES(expires_at)",
        'select_session_by_id': "SELECT data, expires_at FROM pymailadmin_sessions WHERE id = ? AND expires_at > NOW()",
        'delete_session_by_id': "DELETE FROM pymailadmin_sessions WHERE id = ?",
        'delete_expired_sessions': "DELETE FROM pymailadmin_sessions WHERE expires_at <= NOW()", # Pour un cron
        
        # Rate limiting
        'get_rate_limit': "SELECT * FROM pymailadmin_rate_limits WHERE `key` = ?",
        'upsert_rate_limit': """
            INSERT INTO pymailadmin_rate_limits (`key`, `attempts`, `last_attempt`, `blocked_until`)
            VALUES (?, 1, NOW(), NULL)
            ON DUPLICATE KEY UPDATE
                `attempts` = `attempts` + 1,
                `last_attempt` = NOW(),
                `blocked_until` = IF(`attempts` >= ? - 1, DATE_ADD(NOW(), INTERVAL ? MINUTE), `blocked_until`)
        """,
        'reset_rate_limit': "UPDATE pymailadmin_rate_limits SET `attempts` = 0, `blocked_until` = NULL WHERE `key` = ?",
        'delete_expired_rate_limits': "DELETE FROM pymailadmin_rate_limits WHERE `blocked_until` IS NOT NULL AND `blocked_until` < NOW()",

        # Admin users for web admin
        'insert_admin_user': "INSERT INTO pymailadmin_admin_users (email, password_hash) VALUES (?, ?)",
        'select_admin_user_by_email': "SELECT * FROM pymailadmin_admin_users WHERE email = ?",
        'update_admin_password': "UPDATE pymailadmin_admin_users SET password_hash = ? WHERE id = ?",
        'update_admin_user_role': "UPDATE pymailadmin_admin_users SET role = ? WHERE id = ?",
        
        #  Mailboxes owners
        'select_user_ids_by_owner': "SELECT user_id FROM pymailadmin_ownerships WHERE admin_user_id = %s",
        'is_owner': "SELECT 1 FROM pymailadmin_ownerships WHERE admin_user_id = %s AND user_id = %s",
        'add_ownership': "INSERT INTO pymailadmin_ownerships (admin_user_id, user_id, is_primary) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE is_primary = VALUES(is_primary)",
        'remove_ownership': "DELETE FROM pymailadmin_ownerships WHERE admin_user_id = %s AND user_id = %s",

        # Pending registrations
        'insert_admin_registration': "INSERT INTO pymailadmin_admin_registrations (email, password_hash, confirmation_hash, expires_at, reason) VALUES (?, ?, ?, ?, ?)",
        'delete_admin_registration_by_email': "DELETE FROM pymailadmin_admin_registrations WHERE email = ?",
        'select_admin_registration_by_email_unconfirmed': "SELECT * FROM pymailadmin_admin_registrations WHERE email = ? AND confirmed = 0 AND expires_at > NOW()",
        'select_admin_registration_by_hash_unconfirmed': "SELECT * FROM pymailadmin_admin_registrations WHERE confirmation_hash = ? AND expires_at > NOW() AND confirmed = 0",
        'confirm_admin_registration': "UPDATE pymailadmin_admin_registrations SET confirmed = 1 WHERE id = ?",
        'select_pending_registrations': "SELECT email, role, reason FROM pymailadmin_admin_registrations WHERE confirmed = 1 AND expires_at > NOW()",
        'insert_user_from_registration': "INSERT INTO pymailadmin_admin_users (email, password_hash, role, active) VALUES (?, ?, ?, 1)",
        'select_admin_registration_by_hash_unconfirmed': "SELECT * FROM pymailadmin_admin_registrations WHERE confirmation_hash = ? AND expires_at > NOW() AND confirmed = 0",
        'delete_registration_by_email': "DELETE FROM pymailadmin_admin_registrations WHERE email = ?",
        'select_admins_for_moderation': "SELECT email FROM pymailadmin_admin_users WHERE role = 'admin' AND active = 1",
         
        # Pending rekeys for mail_crypt, pendings for mailboxes deletion
        'insert_rekey_pending': 'INSERT INTO pymailadmin_rekey_pending (email, token) VALUES (?, ?) ON DUPLICATE KEY UPDATE token = ?',
        'select_rekey_pending': 'SELECT email FROM pymailadmin_rekey_pending WHERE email = ?',
        'select_all_rekey_pending': 'SELECT email FROM pymailadmin_rekey_pending',
        'deletion_pending': 'SELECT email FROM pymailadmin_deletion_pending WHERE email = ?',
        'select_deletion_pending': 'SELECT email FROM pymailadmin_deletion_pending WHERE email = ?',
        'insert_deletion_pending': 'INSERT INTO pymailadmin_deletion_pending (email, token, confirmed) VALUES (?, ?, 1) ON DUPLICATE KEY UPDATE token = ?, confirmed = 1',
        'select_all_deletion_pending': 'SELECT email FROM pymailadmin_deletion_pending',
        'cleanup_expired_deletion': "DELETE FROM pymailadmin_deletion_pending WHERE created_at < NOW() - INTERVAL %s HOUR",
        
        # Recovery keys (unimplemented for now)
        'insert_recovery_key': "INSERT INTO pymailadmin_recovery_keys (user_id, recovery_key, expiry) VALUES (?, ?, ?)",
        'select_recovery_key': "SELECT * FROM pymailadmin_recovery_keys WHERE user_id = ? AND recovery_key = ? AND expiry > NOW()",
        'delete_recovery_key': "DELETE FROM pymailadmin_recovery_keys WHERE user_id = ?",
        
    },   
}
