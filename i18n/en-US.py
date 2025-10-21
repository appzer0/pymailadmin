# i18n/en-US.py
# English (United States) translations for pymailadmin

translations = {
    # === app.py ===
    'page_not_found_title': 'Page Not Found',
    'redirecting_to_login': 'Redirecting...',

    # === handlers/html.py ===
    'html_lang': 'en',

    # === handlers/static.py ===
    'forbidden_access': 'Forbidden access',
    'not_found': 'Not Found',
    'internal_server_error': 'Internal Server Error',

    # === routes/login.py ===
    'login_title': 'Admin Login',
    'email_label': 'Email address:',
    'password_label': 'Password:',
    'btn_login': 'Login',
    'invalid_email': 'Invalid email address.',
    'invalid_credentials': 'Invalid credentials.',
    'too_many_attempts': 'Too Many Requests. Try again later.',
    'csrf_invalid': 'Invalid CSRF token',
    'bad_request': 'Bad Request',

    # === routes/register.py ===
    'register_title': 'Register',
    'reason_label': 'Reason. Why do you want to create an email address? For what kind of usage? Be precise and express like a human. We won\'t tolerate any AI, bot or automatic process. Any doubt from us and your registration will be declined! So be inventive. Thanks!',
    'btn_register': 'Register',
    'registration_saved': 'Registration saved. Check your usual mail inbox.',
    'email_required': 'Valid email required',
    'reason_required': 'Reason is required',
    'ip_rate_limited': 'Too many attempts from this IP. Wait 60 minutes.',
    'email_sent_failed': 'Internal Server Error. Could not send confirmation link by email',
    'registration_processing': 'Please confirm via the link sent to your email.',
    'email_confirm_subject': 'Confirm your registration',
    'email_moderation_subject': 'Register Requests',
    'email_confirm_body': 'Confirm by clicking on: {confirm_url}',
    'email_moderation_body': 'Email: {email}\nRole: {role}\nReason: {reason}\nAccept: {approve_url}\nDecline: {deny_url}',

    # === routes/moderation.py ===
    'moderation_title': 'Registration Moderation',
    'moderation_email_col': 'Email',
    'moderation_role_col': 'Role',
    'moderation_reason_col': 'Reason',
    'moderation_actions_col': 'Actions',
    'approve_btn': 'Accept',
    'deny_btn': 'Decline',
    'pending_confirmation': 'Your registration has been confirmed! It is now pending for review and validation by an admin.',
    'pending_title': 'Registration confirmed, pending for validation',
    'user_not_found': 'User not found.',
    'approval_failed': 'Could not approve registration.',
    'registration_approved': 'User has been approved.',
    'registration_denied': 'Registration has been denied.',
    'forbidden_access': 'Forbidden access',
    'method_not_allowed': 'Method Not Allowed',
    'missing_email': 'Missing email',
    'missing_hash': 'Missing hash',
    'invalid_hash': 'Invalid confirmation or already processed',

    # === routes/user_management.py ===
    'edit_alias_title': 'Modify an alias',
    'alias_id_invalid': 'Invalid alias ID',
    'alias_not_found': 'Alias not found',
    'source_label': 'Source:',
    'destination_label': 'Destination:',
    'btn_modify': 'Modify',
    'btn_cancel': 'Cancel',
    'source_required': 'Source field is required',
    'destination_required': 'Destination field is required',
    'destination_invalid': 'Invalid destination email address',
    'alias_exists': 'An alias with this source already exists.',
    'alias_updated': 'Alias successfully updated.',
    'alias_update_failed': 'Error when updating alias.',
    'add_alias_title': 'Add an Alias',
    'btn_add': 'Create Alias',
    'destination_unknown': 'Destination mailbox unknown',
    'alias_added': 'Alias successfully added.',
    'alias_add_failed': 'Error when adding alias.',
    'edit_user_title': 'Modify a Mailbox',
    'user_id_invalid': 'Invalid user ID',
    'user_not_found': 'User not found',
    'email_field_label': 'Email address:',
    'password_field_label': 'Password (leave empty to keep current password):',
    'btn_modify_mailbox': 'Modify mailbox',
    'ownership_required': 'Forbidden access: you are not the owner of this mailbox.',
    'user_modified': 'Mailbox successfully modified.',
    'user_modify_failed': 'Error when modifying mailbox.',
    'confirm_deletion_title': 'Confirm mailbox deletion',
    'deletion_warning_title': 'ATTENTION: MAILBOX DELETION INCOMING',
    'deletion_warning_intro': 'We cannot access your mails as they are fully encrypted. We won\'t be able to give them as plain text.',
    'deletion_warning_sync': 'Make sure you obtained your mails as plain text if you plan to keep them locally. By example, in a mail client like Thunderbird, synchronize your mails then quit the client  or switch it offline before confirming mailbox deletion.',
    'deletion_warning_final': 'All stored data related to your mails will be definitely lost!',
    'deletion_confirm_prompt': 'Are you really sure you want to delete the mailbox for',
    'btn_delete_definitely': 'YES, definitely delete mailbox and data NOW',
    'btn_no_cancel': 'NO, cancel now',
    'deletion_blocked_rekey': 'Cannot delete mailbox: a re-encryption is already running. Try again later.',
    'deletion_scheduled': 'Mailbox deletion scheduled.',
    'deletion_failed': 'Error when creating pending deletion',

    # === routes/dashboard.py ===
    'dashboard_title': 'My mailboxes',
    'mailbox_col': 'Mailbox',
    'actions_col': 'Actions',
    'aliases_col': 'Alias',
    'rekey_status': '⚠ RE-ENCRYPTION RUNNING… ⚠',
    'rekey_note': 'Your mailbox is being re-encrypted. It is disabled for 15 minutes while being re-encrypted with your new password.',
    'deletion_status': '⚠ SCHEDULED DELETION… ⚠',
    'deletion_note': 'This mailbox will be definitively deleted in 48h.',
    'change_password_btn': 'Change Password',
    'add_alias_link': 'Add an alias',
    'no_aliases': 'Aucun alias',
    'confirm_delete': 'Are you sure?',

    # Buttons / common
    'btn_yes': 'Yes',
    'btn_no': 'No',
    'btn_cancel': 'Cancel',
    
    # utils/email.py
    'failed_sending_email': 'Failed sending email'

}
