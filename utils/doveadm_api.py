# utils/doveadm_api.py

import os
import requests
import logging

class DoveadmAPIError(Exception):
    pass

def doveadm_post(commands):
    """Sends a command list JSON to doveadm HTTP API"""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": DOVEADM_HTTP_API_SECRET_KEY,
    }
    
    try:
        resp = requests.post(DOVEADM_HTTP_API_URL, json={"commands": commands}, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        if not result or "error" in result:
            error_msg = result.get("error", "Unknown error from doveadm API")
            raise DoveadmAPIError(f"Doveadm API error: {error_msg}")
        
        return result
    
    except requests.RequestException as e:
        logging.error(f"HTTP error calling doveadm API: {e}")
        raise DoveadmAPIError(f"HTTP error calling doveadm API: {e}")
    
def doveadm_create_mailbox(email, mailbox="INBOX"):
    commands = [{
        "command": "mailboxCreate",
        "parameters": {
            "socketPath": DOVEADM_HTTP_API_SOCKET,
            "user": email,
            "mailbox": mailbox,
            "allUsers": False
        },
        "tag": "create-mailbox"
    }]
    
    return doveadm_post(commands)
    
def doveadm_delete_mailbox(email):
    commands = [{
        "command": "mailboxDelete",
        "parameters": {
            "socketPath": DOVEADM_HTTP_API_SOCKET,
            "user": email,
            "mailbox": "*",
            "allUsers": False
        },
        "tag": "delete-mailbox"
    }]
    return doveadm_post(commands)
    
def doveadm_delete_user(email):
    commands = [{
        "command": "userDelete",
        "parameters": {
            "socketPath": DOVEADM_HTTP_API_SOCKET,
            "user": email
        },
        "tag": "delete-user"
    }]
    return doveadm_post(commands)
    
def doveadm_rekey_mailbox_generate(email, old_password_cleartext=None, force_regen=False):
    """Force regeneration of keys - destructive if force_regen=True"""
    params = {
        "socketPath": DOVEADM_HTTP_API_SOCKET,
        "user": email,
        "userOnly": True,
        "reencrypt": True,
    }
    
    if old_password_cleartext:
        params["settings"] = {"crypt_user_key_password": old_password_cleartext}
    
    if force_regen:
        params["force"] = True

    commands = [{
        "command": "mailboxCryptokeyGenerate",
        "parameters": params,
        "tag": f"rekey-mailbox-generate-{email}"
    }]
    return doveadm_post(commands)

def doveadm_rekey_mailbox_password(email, old_password_cleartext, new_password_cleartext):
    """Change the password protecting the mail crypt private key safely"""
    params = {
        "socketPath": DOVEADM_HTTP_API_SOCKET,
        "user": email,
        "oldPassword": old_password_cleartext,
        "newPassword": new_password_cleartext
    }
    commands = [{
        "command": "mailboxCryptokeyPassword",
        "parameters": params,
        "tag": f"rekey-mailbox-password-{email}"
    }]
    return doveadm_post(commands)
