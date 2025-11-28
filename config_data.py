# config_data.py

config = {
    # pymaildmin SQL requests (web admin only, NOT the actual mail server ones, do not modify the following)
    'sql': {
        # Sessions
        'insert_session': "INSERT INTO pymailadmin_sessions (id, data, expires_at) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE data = VALUES(data), expires_at = VALUES(expires_at)",
        'select_session_by_id': "SELECT data, expires_at FROM pymailadmin_sessions WHERE id = %s AND expires_at > NOW()",
        'delete_session_by_id': "DELETE FROM pymailadmin_sessions WHERE id = %s",
        'delete_expired_sessions': "DELETE FROM pymailadmin_sessions WHERE expires_at <= NOW()",
        
        # Rate limiting
        'get_rate_limit': "SELECT * FROM pymailadmin_rate_limits WHERE `key` = %s",
        'upsert_rate_limit': """
            INSERT INTO pymailadmin_rate_limits (`key`, `attempts`, `last_attempt`, `blocked_until`)
            VALUES (%s, 1, NOW(), NULL)
            ON DUPLICATE KEY UPDATE
                `attempts` = CASE WHEN `attempts` IS NULL THEN 1 ELSE `attempts` + 1 END,
                `last_attempt` = NOW(),
                `blocked_until` = IF(`attempts` + 1 >= %s, DATE_ADD(NOW(), INTERVAL %s MINUTE), NULL)
        """,
        
        'reset_rate_limit': "UPDATE pymailadmin_rate_limits SET `attempts` = 0, `blocked_until` = NULL WHERE `key` = %s",
        'delete_expired_rate_limits': "DELETE FROM pymailadmin_rate_limits WHERE `blocked_until` IS NOT NULL AND `blocked_until` < NOW()",
        
        # Admin user utilities
        'count_admin_users': "SELECT COUNT(*) as count FROM pymailadmin_admin_users",
        'count_super_admins': "SELECT COUNT(*) as count FROM pymailadmin_admin_users WHERE role = 'super_admin'",
        'update_admin_role_and_activate': "UPDATE pymailadmin_admin_users SET role = %s, active = 1 WHERE email = %s",
                
        # Admin users for web admin
        'insert_admin_user': "INSERT INTO pymailadmin_admin_users (email, password_hash) VALUES (%s, %s)",
        'select_admin_user_by_email': "SELECT * FROM pymailadmin_admin_users WHERE email = %s",
        'update_admin_password': "UPDATE pymailadmin_admin_users SET password_hash = %s WHERE id = %s",
        'update_admin_user_role': "UPDATE pymailadmin_admin_users SET role = %s WHERE id = %s",
        
        #  Mailboxes owners
        'select_user_ids_by_owner': "SELECT user_id FROM pymailadmin_ownerships WHERE admin_user_id = %s",
        'is_owner': "SELECT 1 FROM pymailadmin_ownerships WHERE admin_user_id = %s AND user_id = %s",
        'add_ownership': "INSERT INTO pymailadmin_ownerships (admin_user_id, user_id, is_primary) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE is_primary = VALUES(is_primary)",
        'remove_ownership': "DELETE FROM pymailadmin_ownerships WHERE admin_user_id = %s AND user_id = %s",
        
        # Registrations
        'insert_admin_registration': "INSERT INTO pymailadmin_admin_registrations (email, password_hash, confirmation_hash, expires_at, reason) VALUES (%s, %s, %s, %s, %s)",
        'delete_admin_registration_by_email': "DELETE FROM pymailadmin_admin_registrations WHERE email = %s",
        'select_admin_registration_by_email_unconfirmed': "SELECT * FROM pymailadmin_admin_registrations WHERE email = %s AND confirmed = 1 AND expires_at > NOW()",
        'select_admin_registration_by_hash_unconfirmed': "SELECT * FROM pymailadmin_admin_registrations WHERE confirmation_hash = %s AND expires_at > NOW() AND confirmed = 0",
        'confirm_admin_registration': "UPDATE pymailadmin_admin_registrations SET confirmed = 1 WHERE id = %s",
        'select_pending_registrations': "SELECT email, reason FROM pymailadmin_admin_registrations WHERE confirmed = 1 AND expires_at > NOW()",
        'insert_user_from_registration': "INSERT INTO pymailadmin_admin_users (email, password_hash, role, active) VALUES (%s, %s, %s, 1)",
        'select_admin_registration_by_hash_unconfirmed': "SELECT * FROM pymailadmin_admin_registrations WHERE confirmation_hash = %s AND expires_at > NOW() AND confirmed = 0",
        'delete_registration_by_email': "DELETE FROM pymailadmin_admin_registrations WHERE email = %s",
        'select_superadmins_for_moderation': "SELECT email FROM pymailadmin_admin_users WHERE role = 'super_admin' AND active = 1",
        
        # Allowed domains for users
        'insert_allowed_domains_for_user': "INSERT IGNORE INTO pymailadmin_domains_ownerships (admin_user_id, domain_id) VALUES (%s, %s)",
        'select_domains_by_admin_user': "SELECT domain_id FROM pymailadmin_domains_ownerships WHERE admin_user_id = %s",
        'select_allowed_domains_by_admin': """
            SELECT d.{field_domain_id} AS id, d.{field_domain_name} AS domain
            FROM {table_domains} d
            JOIN pymailadmin_domains_ownerships o ON o.domain_id = d.{field_domain_id}
            WHERE o.admin_user_id = %s
            ORDER BY d.{field_domain_name}
        """,

    },   
}
