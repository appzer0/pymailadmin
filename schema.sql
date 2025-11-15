-- schema.sql
-- pymailadmin tables structure

-- Sessions and cookies --
CREATE TABLE `pymailadmin_sessions` (
    `id` varchar(128) NOT NULL,
    `data` text NOT NULL,
    `expires_at` datetime NOT NULL,
    PRIMARY KEY (`id`),
    INDEX `idx_expires` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Rate limiting --
CREATE TABLE `pymailadmin_rate_limits` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `key` varchar(64) NOT NULL,
    `attempts` int(11) NOT NULL DEFAULT 0,
    `last_attempt` datetime NOT NULL,
    `blocked_until` datetime DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_key` (`key`(64)),
    INDEX `idx_blocked` (`blocked_until`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Web admin registration --
CREATE TABLE `pymailadmin_admin_registrations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(191) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `reason` text NOT NULL,
  `confirmation_hash` varchar(191) NOT NULL,
  `expires_at` datetime NOT NULL,
  `confirmed` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_email` (`email`(191)),
  UNIQUE KEY `uniq_confirmation_hash` (`confirmation_hash`(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Web admin users --
CREATE TABLE `pymailadmin_admin_users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(191) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` ENUM('user', 'admin', 'super_admin') DEFAULT 'user' NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_email` (`email`(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Domains ownerships --
CREATE TABLE `pymailadmin_domains_ownerships` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `admin_user_id` INT NOT NULL,
  `domain_id` INT NOT NULL,
  FOREIGN KEY (`admin_user_id`) REFERENCES `pymailadmin_admin_users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`domain_id`) REFERENCES `domain`(`id`) ON DELETE CASCADE,
  UNIQUE KEY `unique_admin_domain` (`admin_user_id`, `domain_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Mailboxes ownerships --
CREATE TABLE `pymailadmin_ownerships` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `admin_user_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `is_primary` TINYINT(1) DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `unique_ownership` (`admin_user_id`, `user_id`),
    FOREIGN KEY (`admin_user_id`) REFERENCES `pymailadmin_admin_users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_admin_user` (`admin_user_id`),
    INDEX `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Recovery keys --
CREATE TABLE `pymailadmin_recovery_keys` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `recovery_key` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`),
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Mailboxes creation pendings
CREATE TABLE IF NOT EXISTS `pymailadmin_creation_pending` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(191) NOT NULL,
    `token` VARCHAR(64) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uniq_email` (`email`(191)),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Rekey pendings for when passwords change --
CREATE TABLE `pymailadmin_rekey_pending` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(191) NOT NULL UNIQUE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `token` VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Mailboxes deletion pendings --
CREATE TABLE `pymailadmin_deletion_pending` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(191) NOT NULL UNIQUE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `token` VARCHAR(64) NOT NULL,
    `confirmed` TINYINT(1) NOT NULL DEFAULT 0,
    INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
