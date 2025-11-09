# pymailadmin

## English (see below for French)

This repo is a work-in-progress for pymailadmin, an Dovecot-based mail server web admin for users
Python3/gunicorn systemd-compliant app, listening on 127.0.0.1:8686 by default.

It aims at being compatible with any mail server setups, given they are based on Dovecot interfaced with MySQL lookups and using a functional mail_crypt plugin setup.

NOT TO USE IN PRODUCTION

### Features

  * Administrate your Dovecot-based encrypted mail server
  * Uses your Dovecot database without altering it.
  * Supports registering as a new mailbox user.
  * Users manage their mailboxes and aliases on their own.
  * Supplies a moderation interface for new registrations.
  * Supports maximum mailboxes number and maximum aliases number per mailbox.
  * When password change for a mailbox, a rekey occurs and mailbox is disabled for 15 minutes for storage to be reencrypted.
  * Mailboxes deletions requests are in pending state, deletions actually occur after 48 hours (via a crontask).
  * Supports a web frontend admin server seperated from you Dovecot mail server.

### Requirements

System:

  * A Debian-based system (tested on Debian 13 "trixie" only).
  * A fully functional mail server running Dovecot 2.4.1+ for auth and mail management.
  * A fully functional Dovecot installation, talking to a MySQL/MariaDB database.
  * A fully functional Dovecot ``mail_crypt`` plugin setup for mail storage encryption.
  * An acceptable hash algorithm for mail passwords. pymailadmin supports the following algorithms ONLY:
    * ``argon2id``
    * ``argon2i``
    * ``bcrypt``
    * ``sha512-crypt``
    * ``sha256-crypt``
    * ``pbkdf2``

Dovecot database:

  * A special field in your users' table for enabled/disabled mailboxes (values: 0|1).

And a bit of patience and easy-going on the Python code quality.

### Installation

#### Edit schema.sql to adapt foreign keys to your tables/fields names

Change 2 foreign keys references in schema.sql. Replace "users(id)" with
your own table and field names, those storing the actual users IDs:

``FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,``

``FOREIGN KEY (`user_id`) REFERENCES users(id) ON DELETE CASCADE``

#### Import tables schema into you mail database
``mysql -udbuser -p dbname < schema.sql``

#### Install Python and pip
``apt update``

``apt install python3 python3-pip python3-venv python3-dev``

#### Create unprivileged user
``adduser --system --group --no-create-home --disabled-login pymailadmin``

#### Create "venv" virtual environment
Copy/clone repository somewhere, e.g. /var/www/pymailadmin, then:

``python3 -m venv /var/www/pymailadmin/venv``

``source /var/www/pymailadmin/venv/bin/activate``

#### Install dependencies
``cd /var/www/pymailadmin && pip3 install -r requirements.txt``

#### Install systemd service
``cp pymailadmin.service /etc/systemd/system/``

### Configuration

#### Customize .env environment file, READ IT AND EDIT IT CAREFULLY
You will mostly have to pay attention when customizing the tables and fields names for Dovecot.

``cd /var/www/pymailadmin && cp .env.example .env``

``vim .env``

#### Create log directory and fix permissions:
``mkdir /var/log/pymailadmin``

``chown -R pymailadmin: /var/log/pymailadmin``

``chmod -R 755 /var/log/pymailadmin``

``chown -R pymailadmin:pymailadmin /var/www/pymailadmin``

``chmod -R 750 /var/www/pymailadmin``

Allow your web server user (www-data, httpd, etc.) to reach static dir:

``setfacl -R -m u:www-data:rx /var/www/pymailadmin/static``

``setfacl -m u:www-data:rx /var/www/pymailadmin``

#### Create log dir and fix permissions:
``mkdir /var/log/pymailadmin``

``chown -R pymailadmin: /var/log/pymailadmin``

``chmod -R 755 /var/log/pymailadmin``

``chown -R pymailadmin:pymailadmin /var/www/pymailadmin``

``chmod -R 750 /var/www/pymailadmin``

#### Customize systemd service file``
``vim /etc/systemd/system/pymailadmin.service``

``systemctl daemon-reload``

#### Copy nginx config file , enable and edit
``cp pymailadmin.nginx.conf /etc/nginx/sites-available/pymailadmin.conf``

``ln -s /etc/nginx/sites-available/pymailadmin.conf /etc/nginx/sites-enabled/``

``vim /etc/nginx/sites-enabled/pymailadmin.conf``

``systemctl reload nginx``

Make sure you have a TLS certificate (with ``certbot`` or another tool).

#### Install the Dovecot connector ON YOUR DOVECOT HOST
Run the commands in the chapter below **on your Dovecot host**:

Copy the connector:

``cp scripts/pymailadmin-cron.py /opt/pymailadmin/pymailadmin-cron.py``

Edit it. Put your database connection settings again at the top.
Customize the table name and columns names to match yours (4 variables).

You'll need those packages:

``apt install python3 python3-pip python3-venv python3-dev``

Create the virtual environment:

``python3 -m venv /opt/pymailadmin/venv``

Enter the venv by activating it:

``source /opt/pymailadmin/venv/bin/activate``

Install the MySQL connector:

``python3 -m pip install mysql-connector-python``

Create the log file:

``touch /var/log/pymailadmin-cron.log``

Create a cron task, e.g.:

``*/2 * * * * root /opt/pymailadmin/venv/bin/python /opt/pymailadmin/pymailadmin-cron.py``

That's all for your Dovecot host.

### Start the service
``systemctl enable --now pymailadmin.service``

#### Create a superadmin
  * Create a salted hash of your password, here's an example for an Argon2ID hash:
    * ``echo -n 'My@Pass*word!' | argon2 "$(pwgen -Ans 16 1)" -id -t 3 -p 2 -m 16 -e``
  * Create a superadmin in your database:
  * ``INSERT INTO pymailadmin_admin_users (email, password_hash, role, active) VALUES ('email@example.org', '$argon2id$v=19$m=65536,t=3,p=2$XXXXXXXXXXXXIXX', 'super_admin', '1');``
  
#### Access the web admin
  * Go to ``https://mydopemailadmin.domain.tld``
  * Enjoy new incoming bugs and problems.

## French / Français

Ce dépôt est un travail en cours pour pymailadmin, une interface web d'admin de serveur mail Dovecot pour les utilisateur⋅ices et admins.
Application Python3/gunicorn compatible systemd, écoutant sur 127.0.0.1:8686 par défaut.

Le but est d'être compatible avec toute installation de serveur mail, basée sur Dovecot interfacé à MySQL et avec le plugin mail_crypt fonctionnel.

A NE PAS UTILISER EN PRODUCTION

### Fonctionnalités

  * Administrez votre serveur de mail chiffré basé sur Dovecot.
  * Utilise votre base de données Dovecot sans l'altérer.
  * Prend en charge l'inscription utilisateur⋅ice.
  * Les utilisateur⋅ices gèrent leurs boites et leur alias en autonomie.
  * Fournit une interface de modération pour les admins.
  * Les utilisateur⋅ices gèrent leurs boites mails et leur alias.
  * Prend en charge un nombre maximum de boites mail et d'alias par boite.
  * Quand le mot de passe de la boite mail change, un rechiffrement en attente est créé et la boite est désactivée 15 minutes pour le rechiffrement.
  * Les demande de suppression de boites mail sont placées en attente et la suppression se fait après 48 hours (via cron).
  * Prend en charge un serveur web frontal séparé de votre serveur mail Dovecot.

### Pré-requis

Système :

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

Base de données pour Dovecot:

  * Un champ spécial dans la tables des boites mail pour les boites actives/inactives (valeurs: 0|1).

Et un peu de patience et d'indulgence sur la qualité du code Python.

### Installation

#### Éditez schema.sql pour l'adapter à votre table et noms de champs

Changez les 2 références des clefs étrangères dans schema.sql. Remplacez
"users(id)" avec vos propres noms de table et de champ, ceux qui stockent
les ID des utilisateurs :

``FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,``

``FOREIGN KEY (`user_id`) REFERENCES users(id) ON DELETE CASCADE``

#### Importez le schéma des tables dans votre base
``mysql -udbuser -p dbname < schema.sql``

#### Installez Python and pip
``apt update``

``apt install python3 python3-pip python3-venv python3-dev``

#### Créez un utilisateur non-privilégié
``adduser --system --group --no-create-home --disabled-login pymailadmin``

#### Créez l'environnement virtuel "venv"
Copier/clonez le dépôt quelque part, par ex. : /var/www/pymailadmin, puis :

``python3 -m venv /var/www/pymailadmin/venv``

``source /var/www/pymailadmin/venv/bin/activate``

#### Installez les dépendances
``cd /var/www/pymailadmin && pip3 install -r requirements.txt``

#### Installez le service systemd
``cp pymailadmin.service /etc/systemd/system/``

### Configuration

#### Personnalisez le fichier .env, LISEZ-LE ET ÉDITEZ-LE MINUTIEUSEMENT
Vous aurez notamment à bien faire attention en personnalisant les noms des tables et des champs pour Dovecot.

``cd /var/www/pymailadmin && cp .env.example .env``

``vim .env``

#### Créez le répertoire pour les logs et corrigez les permissions :
``mkdir /var/log/pymailadmin``

``chown -R pymailadmin: /var/log/pymailadmin``

``chmod -R 755 /var/log/pymailadmin``

``chown -R pymailadmin:pymailadmin /var/www/pymailadmin``

``chmod -R 750 /var/www/pymailadmin``

Autorisez votre serveur HTTP (www-data, httpd, etc.) à atteindre le répertoire static :

``setfacl -R -m u:www-data:rx /var/www/pymailadmin/static``

``setfacl -m u:www-data:rx /var/www/pymailadmin``

#### Personnalisez le fichier du service systemd``
``vim /etc/systemd/system/pymailadmin.service``

``systemctl daemon-reload``

#### Copiez le fichier de configuration pour nginx, activez-le et éditez-le
``cp pymailadmin.nginx.conf /etc/nginx/sites-available/pymailadmin.conf``

``ln -s /etc/nginx/sites-available/pymailadmin.conf /etc/nginx/sites-enabled/``

``vim /etc/nginx/sites-enabled/pymailadmin.conf``

``systemctl reload nginx``

Assurez-vous d'avoir un certificat TLS (via ``certbot`` ou autre).

#### Installez le connecteur Dovecot SUR VOTRE SERVEUR DOVECOT
Exécutez les commandes de ce chapitre **sur votre serveur Dovecot** :

Copiez le connecteur :

``cp scripts/pymailadmin-cron.py /opt/pymailadmin/pymailadmin-cron.py``

Éditez-le. Mettez en haut vos paramètres de connexion à la base de données.
Adaptez le nom de la table ainsi que les noms des colonnes (4 variables).

Vous aurez besoin de ces paquets :

``apt install python3 python3-pip python3-venv python3-dev``

Créez l'environnement virtuel :

``python3 -m venv /opt/pymailadmin/venv``

Entrez dans le venv en l'activant :

``source /opt/pymailadmin/venv/bin/activate``

Installez le connecteur MySQL :

``python3 -m pip install mysql-connector-python``

Créez le fichier pour les logs :

``touch /var/log/pymailadmin-cron.log``

Créez une tâche planifiée pour cron, par ex. :

``*/2 * * * * root /opt/pymailadmin/venv/bin/python /opt/pymailadmin/pymailadmin-cron.py``

C'est tout pour votre serveur Dovecot.

### Démarrez le service
``systemctl enable --now pymailadmin.service``

#### Créez un⋅e superadmin
  * Créez un hash salé de votre mot de passe, ici par exemple pour Argon2ID :
    * ``echo -n 'My@Pass*word!' | argon2 "$(pwgen -Ans 16 1)" -id -t 3 -p 2 -m 16 -e``
  * Créez un⋅e superadmin dans la base de données :
  * ``INSERT INTO pymailadmin_admin_users (email, password_hash, role, active) VALUES ('email@example.org', '$argon2id$v=19$m=65536,t=3,p=2$XXXXXXXXXXXXIXX', 'super_admin', '1');``
  
#### Accédez à l'interface web
  * Allez sur ``https://mydopemailadmin.domain.tld``
  * Appréciez les nouveaux bogues et problèmes qui s'annoncent.
