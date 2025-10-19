# schema.sql

-- Gestion des sessions et cookies --
CREATE TABLE `sessions` (
    `id` varchar(128) NOT NULL,        -- ID de session signé
    `data` text NOT NULL,              -- Données de session (sérialisées en JSON)
    `expires_at` datetime NOT NULL,    -- Date d'expiration
    PRIMARY KEY (`id`),
    INDEX `idx_expires` (`expires_at`) -- Pour nettoyer les sessions expirées
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Gestion du rate limiting --
CREATE TABLE `rate_limits` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `key` varchar(64) NOT NULL,
    `attempts` int(11) NOT NULL DEFAULT 0,
    `last_attempt` datetime NOT NULL,
    `blocked_until` datetime DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_key` (`key`),
    INDEX `idx_blocked` (`blocked_until`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les utilisateurs de l'interface d'administration (accès web)
CREATE TABLE `admin_registrations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(128) NOT NULL UNIQUE,
  `password_hash` varchar(255) NOT NULL,
  `reason` text NOT NULL,
  `confirmation_hash` varchar(64) NOT NULL UNIQUE,
  `expires_at` datetime NOT NULL,
  `confirmed` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE `admin_users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(128) NOT NULL UNIQUE,
  `password_hash` varchar(255) NOT NULL,
  `role` ENUM('user', 'admin', 'super_admin') DEFAULT 'user' NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Table de liaison propriétaires - boites mails
CREATE TABLE ownerships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_user_id INT NOT NULL,
    user_id INT NOT NULL,
    is_primary TINYINT(1) DEFAULT 0,  -- Ex: boîte principale pour notifications
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_ownership (admin_user_id, user_id),
    FOREIGN KEY (admin_user_id) REFERENCES admin_users(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_admin_user (admin_user_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les clés de récupération de mot de passe boîte mail
CREATE TABLE `recovery_keys` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `recovery_key` varchar(255) NOT NULL UNIQUE,
  `expiry` datetime NOT NULL,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Table pour le rechiffrement si changement de mot de passe boîte mail
CREATE TABLE rekey_pending (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    token VARCHAR(64) NOT NULL
);

-- Table pour la demande de suppression de boîte mail
CREATE TABLE deletion_pending (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    token VARCHAR(64) NOT NULL,
    confirmed TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
