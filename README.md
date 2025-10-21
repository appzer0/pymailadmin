# pymailadmin

## English (see below for French)

This repo is a work-in-progress for pymailadmin, an Dovecot-based mail server web admin for users
Python3/gunicorn systemd-compliant app, listening on 127.0.0.1:8686 by default.

It aims at being compatible with any mail server setups, given they are based on Dovecot interfaced with MySQL lookups and using a functional mail_crypt plugin setup.

NOT TO USE IN PRODUCTION

### Features

  * Supports registering as a user, supplies a moderation interface for admins.
  * Users manage their mailboxes and aliases.
  * When password change for a mailbox, a rekey is pending and mailbox is disabled for 15 minutes for storag to  be reencrypted.
  * Mailboxes deletions requests are in pending state, deletions actually occur after 48 hours (via a crontask).
  * Uses the same MySQL/MariaDB database as Dovecot but in separate tables.
  * Supports separate web frontend admin server.

### Requirements

  * A Debian-based system (tested on Debian 13 "trixie" only).
  * A fully functional mail server running Dovecot 2.4.1+ for auth and mail management.
  * A fully functional Dovecot, talking to a MySQL/MariaDB database.
  * A fully functional Dovecot ``mail_crypt`` plugin setup for mail storage encryption.
  * An acceptable hash algorithm for mail passwords. pymailadmin supports the following algorithms ONLY:
    * ``argon2id``
    * ``argon2i``
    * ``bcrypt``
    * ``sha512-crypt``
    * ``sha256-crypt``
    * ``pbkdf2``
  * A bit of patience and easy-going on the Python code quality.

### Installation

#### Import tables schema into you mail database
``mysql -udbuser -p dbname < schema.sql``

#### Install Python and pip
```
apt update
apt install python3 python3-pip python3-venv python3-dev
```

#### Create unprivileged user
``adduser --system --group --no-create-home --disabled-login pymailadmin``

#### Create "venv" virtual environment
Copy/clone repository somewhere, e.g. /var/www/pymailadmin, then:

```python3 -m venv /var/www/pymailadmin/venv
source /var/www/pymailadmin/venv/bin/activate```

#### Install dependencies
``cd /var/www/pymailadmin && pip3 install -r requirements.txt``

#### Install systemd service
``cp pymailadmin.service /etc/systemd/system/``

### Configuration

#### Customize .env environment file, READ IT AND EDIT IT CAREFULLY
```cd /var/www/pymailadmin && cp .env.example .env
vim .env``

#### Fix permissions:
```chown -R pymailadmin:pymailadmin /var/www/pymailadmin
chmod -R 750 /var/www/pymailadmin``

#### Customize systemd service file``
``vim /etc/systemd/system/pymailadmin.service
``systemctl daemon-reload``

#### Copy nginx config file , enable and edit
```cp pymailadmin.nginx.conf /etc/nginx/sites-available/pymailadmin.conf
ln -s /etc/nginx/sites-available/pymailadmin.conf /etc/nginx/sites-enabled/
vim /etc/nginx/sites-enabled/pymailadmin.conf
systemctl reload nginx```

### Start the service
``systemctl enable --nox pymailadmin.service``

#### Installez le connecteur pour gérer les suppressions et rekey
Install the pymailadmin connector for Dovecot **ON THE DOVECOT HOST** to
process pending deletions & expired rekey requests:

Install the needed packages:

``apt install python3 python3-mysqldb``

Install ``scripts/mail-delete-cron.py`` somewhere, e.g.: ``/opt/pymailadmin/scripts``

Édit the script:
``vim /opt/pymailadmin/scripts/mail-delete-cron.py``

READ IT AND EDIT IT CAREFULLY.
You'll have to modify:
  * your database connection parameters
  * Adapat 2 SQL requests to your database (that you've already done before in .env)

Install the crontask :
``*/2 * * * * root /usr/bin/python3 /opt/pymailadmin/scripts/mail-delete-cron.py``

#### Create a superadmin
  * Register as simple user on ``https://mydopemailadmin.domain.tld/register``
  * Confirm email by clicking the confirmation link sent
  * Update your role in database:
    * ``UPDATE `pymailadmin_admin_users` SET `role = 'super_admin' WHERE email = your-registered-address@domain.tld``
  
#### Acces web admin
  * Go to ``https://mydopemailadmin.domain.tld/login``
  * Enjoy new incoming bugs and problems.

## French / Français

Ce dépôt est un travail en cours pour pymailadmin, une interface web d'admin de serveur mail Dovecot pour les utilisateur⋅ices et admins.
Application Python3/gunicorn compatible systemd, écoutant sur 127.0.0.1:8686 par défaut.

Le but est d'être compatible avec toute installation de serveur mail, basée sur Dovecot interfacé à MySQL et avec le plugin mail_crypt fonctionnel.

A NE PAS UTILISER EN PRODUCTION

### Fonctionnalités

  * Prend en charge l'inscription utilisateur⋅ice et fournit une interface de modération pour les admins.
  * Les utilisateur⋅ices gèrent leurs boites mails et leur alias.
  * Quand le mot de passe de la boite mail change, un rechiffrement en attente est créé et la boite est désactivée 15 minutes pour le rechiffrement.
  * Les demande de suppression de boites mail sont placées en attente et la suppression se fait après 48 hours (via cron).
  * Utilise la même base de données MySQL/MariaDB database que Dovecot mais dans des tables séparées.
  * Prend en charge un serveur serveur web frontal séparé du serveur mail.

### Pré-requis

  * Un seveur basé sur Debian (testé uniquement sur Debian 13 "trixie").
  * Un serveur mail fonctionnel basé sur Dovecot 2.4.1+ pour l'authentification et la gestion des boites mail.
  * Dovecot fonctionnel, interfacé à une base de données MySQL/MariaDB.
  * Le greffon ``mail_crypt`` fonctionnel pour le chiffrement du stockage des mails.
  * Un algorithme de hashage acceptable pour les mots de passe mail. pymailadmin prend en charge UNIQUEMENT :
    * ``argon2id``
    * ``argon2i``
    * ``bcrypt``
    * ``sha512-crypt``
    * ``sha256-crypt``
    * ``pbkdf2``
  * Un peu de patience et d'indulgence sur la qualité du code Python.

### Installation

#### Importez le schéma des tables dans votre base
``mysql -udbuser -p dbname < schema.sql``

#### Installez Python and pip
```apt update
apt install python3 python3-pip python3-venv python3-dev```

#### Créez un utilisateuir non-privilégié
``adduser --system --group --no-create-home --disabled-login pymailadmin``

#### Créez l'environnement virtuel "venv"
Copy/clone repository somewhere, e.g. /var/www/pymailadmin, then:
```python3 -m venv /var/www/pymailadmin/venv
source /var/www/pymailadmin/venv/bin/activate```

#### Installez les dépendances
``cd /var/www/pymailadmin && pip3 install -r requirements.txt``

#### Installez le service systemd
``cp pymailadmin.service /etc/systemd/system/``

### Configuration

#### Personnliasez le fichier .env, LISEZ-LE ET ÉDITEZ-LE MINUTIEUSEMENT
```cd /var/www/pymailadmin && cp .env.example .env
vim .env```

#### Corrigez les permissions:
```chown -R pymailadmin:pymailadmin /var/www/pymailadmin
chmod -R 750 /var/www/pymailadmin```

#### Personnalisez le fichier du service systemd``
```vim /etc/systemd/system/pymailadmin.service
systemctl daemon-reload```

#### Copiez le fichier de configuration pour nginx, activez-le et éditez-le
```cp pymailadmin.nginx.conf /etc/nginx/sites-available/pymailadmin.conf
ln -s /etc/nginx/sites-available/pymailadmin.conf /etc/nginx/sites-enabled/
vim /etc/nginx/sites-enabled/pymailadmin.conf
systemctl reload nginx```

### Démarrez le service
``systemctl enable --nox pymailadmin.service``

#### Installez la tâche planifiée des suppressions de boites en attente
``0 */2 * * * pymailadmin /usr/bin/python3 /var/www/pymailadmin/scripts/mail-delete-cron.py``

#### Installez le connecteur pour gérer les suppressions et rekey
Installez le connector pymailadmin pour Dovecot **SUR LE SERVEUR DOVECOT**
pour traiter les suppressions d eboites mail et le nettoyage des demandes de
et des rekey ayant expiré:

Installez les paquets nécessaires:

``apt install python3 python3-mysqldb``

Installez ``scripts/mail-delete-cron.py`` quelque part, ex. : ``/opt/pymailadmin/scripts``

Éditez le script:
``vim /opt/pymailadmin/scripts/mail-delete-cron.py``

LISEZ-LE ET ÉDITEZ-LE MINUTIEUSEMENT.
Vous devrez modifier :
  * vos paramètres de connexion à la base de données
  * 2 requêtes SQL pour les adapter à votre base (que vous avez déjà fait dans .env)

Installez la tâche planifié cron :
``*/2 * * * * root /usr/bin/python3 /opt/pymailadmin/scripts/mail-delete-cron.py``

#### Créez un⋅e super-administrateur⋅ice
  * Inscrivez-vous comme simple utilisateur⋅ice sur ``https://mydopemailadmin.domain.tld/register``
  * Confirmez votre adresse email en cliquant sur le lien de confirmation reçu
  * Mettez à jour votre rôle dans la base :
    * ``UPDATE `pymailadmin_admin_users` SET `role = 'super_admin' WHERE email = votre-adresse-a-linscription@domain.tld``
  
#### Accédez à l'interface web d'admin
  * Allez sur ``https://mydopemailadmin.domain.tld/login``
  * Appréciez les nouveaux bogues et problèmes qui s'annoncent.
