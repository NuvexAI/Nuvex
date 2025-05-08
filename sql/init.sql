-- Core Tables
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `username` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Username',
  `email` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Email address',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Hashed password',
  `wallet_address` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Ethereum wallet address',
  `chain_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'ethereum' COMMENT 'Blockchain type, e.g., ethereum or solana',
  `nonce` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Nonce for wallet signature',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `create_time` datetime DEFAULT (now()) COMMENT 'Registration time',
  `update_time` datetime DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  UNIQUE KEY `uk_wallet_address` (`wallet_address`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Application Related Tables
CREATE TABLE `app` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the app',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Description of the app',
  `mode` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'ReAct' COMMENT 'Mode of the app: ReAct (complex tasks), Prompt (simple conversation), call (legacy)',
  `icon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Icon URL of the app',
  `status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Status of the app: draft, active, inactive',
  `role_settings` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Role settings for the agent',
  `welcome_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Welcome message for the agent',
  `twitter_link` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Twitter link for the agent',
  `telegram_bot_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Telegram bot ID for the agent',
  `telegram_bot_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Telegram bot name',
  `telegram_bot_token` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Encrypted Telegram bot token',
  `token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Token symbol for the agent',
  `symbol` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Symbol for the agent token',
  `photos` JSON COMMENT 'Photos for the agent',
  `demo_video` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Demo video URL for the agent',
  `tool_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Tool prompt for the agent',
  `max_loops` int DEFAULT 3 COMMENT 'Maximum number of loops the agent can perform',
  `model_json` JSON COMMENT 'Additional fields merged into a JSON column',
  `custom_config` JSON COMMENT 'Custom configuration for the agent stored as JSON',
  `is_public` BOOLEAN DEFAULT FALSE COMMENT 'Whether the agent is public',
  `is_official` BOOLEAN DEFAULT FALSE COMMENT 'Whether the agent is official preset',
  `is_hot` BOOLEAN DEFAULT FALSE COMMENT 'Whether the agent is hot',
  `suggested_questions` JSON COMMENT 'List of suggested questions for the agent',
  `model_id` bigint DEFAULT NULL COMMENT 'ID of the associated model',
  `category_id` bigint DEFAULT NULL COMMENT 'ID of the category',
  `create_fee` DECIMAL(20,9) DEFAULT 0.000000000 COMMENT 'Fee for creating the agent (tips for creator)',
  `price` DECIMAL(20,9) DEFAULT 0.000000000 COMMENT 'Fee for using the agent',
  `vip_level` int DEFAULT 0 COMMENT 'Required VIP level to access this agent (0 for normal users, 1 for VIP users)',
  `sensitive_data_config` json DEFAULT NULL COMMENT 'Configuration for sensitive data handling',
  `dev` varchar(255) DEFAULT NULL COMMENT 'Developer wallet address',
  `enable_mcp` tinyint(1) DEFAULT '0' COMMENT 'Whether MCP is enabled for this agent',
  `is_deleted` tinyint(1) DEFAULT NULL COMMENT 'Logical deletion flag',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `update_time` datetime DEFAULT (now()) COMMENT 'Last update time',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  PRIMARY KEY (`id`),
  KEY `idx_tenant` (`tenant_id`),
  KEY `idx_model` (`model_id`),
  KEY `idx_category` (`category_id`),
  KEY `idx_public_official` (`is_public`, `is_official`),
  KEY `idx_hot` (`is_hot`),
  KEY `idx_vip_level` (`vip_level`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tool Related Tables
CREATE TABLE `tools` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the tool',
  `description` varchar(800) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Description of the tool',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Type of the tool: function or openAPI',
  `origin` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'API origin',
  `path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'API path',
  `method` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HTTP method',
  `parameters` JSON COMMENT 'API parameters including header, query, path, and body',
  `is_deleted` tinyint(1) DEFAULT NULL COMMENT 'Logical deletion flag',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `update_time` datetime DEFAULT (now()) COMMENT 'Last update time',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `is_public` BOOLEAN DEFAULT FALSE COMMENT 'Whether the tool is public',
  `is_official` BOOLEAN DEFAULT FALSE COMMENT 'Whether the tool is official preset',
  `auth_config` JSON COMMENT 'Authentication configuration in JSON format',
  `icon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Icon URL of the tool',
  `is_stream` BOOLEAN DEFAULT FALSE COMMENT 'Whether the API returns a stream response',
  `output_format` JSON COMMENT 'JSON configuration for formatting API output',
  `category_id` bigint DEFAULT NULL COMMENT 'ID of the category',
  `sensitive_data_config` JSON DEFAULT NULL COMMENT 'Configuration for sensitive data handling',
  PRIMARY KEY (`id`),
  KEY `idx_tenant` (`tenant_id`),
  KEY `idx_public_official` (`is_public`, `is_official`),
  KEY `idx_type` (`type`),
  KEY `idx_category` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `agent_tools` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `agent_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID of the agent',
  `tool_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID of the tool',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  PRIMARY KEY (`id`),
  KEY `idx_agent_tool` (`agent_id`, `tool_id`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Model Related Tables
CREATE TABLE `models` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the model',
  `model_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the underlying model (e.g. gpt-4, claude-3)',
  `endpoint` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'API endpoint of the model',
  `api_key` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'API key for the model',
  `is_official` BOOLEAN DEFAULT FALSE COMMENT 'Whether the model is official preset',
  `is_public` BOOLEAN DEFAULT FALSE COMMENT 'Whether the model is public',
  `icon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Icon URL of the model',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `update_time` datetime DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  KEY `idx_tenant` (`tenant_id`),
  KEY `idx_public_official` (`is_public`, `is_official`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Category Related Tables
CREATE TABLE `categories` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the category',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Type of the category: agent or tool',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Description of the category',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `sort_order` int DEFAULT 0 COMMENT 'Sort order for display',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `update_time` datetime DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  KEY `idx_tenant` (`tenant_id`),
  KEY `idx_type` (`type`),
  KEY `idx_sort` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- File Storage Related Tables
CREATE TABLE `file_storage` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the file',
  `file_uuid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'File UUID',
  `file_content` LONGBLOB NULL COMMENT 'Content of the file (null for S3 storage)',
  `size` bigint NOT NULL COMMENT 'Size of the file',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `storage_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'database' COMMENT 'Storage type: database or s3',
  `storage_location` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT 'Storage location for external storage',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_file_uuid` (`file_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- API Key Related Tables
CREATE TABLE `open_platform_keys` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the API key',
  `access_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Access key for API authentication',
  `secret_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Secret key for API authentication',
  `token` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Encrypted permanent token for API authentication',
  `token_created_at` datetime DEFAULT NULL COMMENT 'Token creation time',
  `user_id` bigint NOT NULL COMMENT 'ID of the associated user',
  `created_at` datetime DEFAULT (now()) COMMENT 'Creation time',
  `is_deleted` tinyint(1) DEFAULT 0 COMMENT 'Logical deletion flag',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_access_key` (`access_key`),
  UNIQUE KEY `uk_token` (`token`),
  UNIQUE KEY `uk_user_id` (`user_id`),
  KEY `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- MCP Related Tables
CREATE TABLE `mcp_server` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the MCP server',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Description of the MCP server',
  `version` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '1.0.0' COMMENT 'Version of the MCP server',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT 'Whether the MCP server is active',
  `tenant_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Tenant ID',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `update_time` datetime DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mcp_server_name` (`name`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `mcp_tool` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `mcp_server_id` int NOT NULL COMMENT 'ID of the MCP server',
  `tool_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'ID of the tool',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_mcp_tool` (`mcp_server_id`, `tool_id`),
  KEY `idx_tool` (`tool_id`),
  KEY `idx_mcp_server` (`mcp_server_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `mcp_prompt` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `mcp_server_id` int NOT NULL COMMENT 'ID of the MCP server',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the prompt template',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Description of the prompt template',
  `arguments` JSON COMMENT 'Arguments for the prompt template in JSON format',
  `template` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Prompt template text',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `update_time` datetime DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_mcp_prompt_name` (`mcp_server_id`, `name`),
  KEY `idx_mcp_server` (`mcp_server_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `mcp_resource` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `mcp_server_id` int NOT NULL COMMENT 'ID of the MCP server',
  `uri` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'URI of the resource',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Content of the resource',
  `mime_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'text/plain' COMMENT 'MIME type of the resource',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `update_time` datetime DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_mcp_resource_uri` (`mcp_server_id`, `uri`),
  KEY `idx_mcp_server` (`mcp_server_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `mcp_stores` (
  `id` SERIAL PRIMARY KEY COMMENT 'Auto-incrementing ID',
  `name` VARCHAR(255) NOT NULL COMMENT 'Name of the store',
  `icon` VARCHAR(255) COMMENT 'Store icon URL',
  `description` TEXT COMMENT 'Description of the store',
  `store_type` VARCHAR(50) NOT NULL COMMENT 'Type of the store',
  `tags` JSON COMMENT 'Store tags as JSON list',
  `content` TEXT COMMENT 'Store content',
  `creator_id` INTEGER NOT NULL COMMENT 'ID of the creator',
  `author` VARCHAR(255) COMMENT 'Name of the author',
  `github_url` VARCHAR(255) COMMENT 'GitHub repository URL',
  `tenant_id` VARCHAR(255) NOT NULL COMMENT 'Tenant ID',
  `is_public` BOOLEAN DEFAULT FALSE COMMENT 'Whether the store is public',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  `agent_id` VARCHAR(36) COMMENT 'ID of the associated agent',
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_tenant_id` (`tenant_id`),
  KEY `idx_creator` (`creator_id`),
  KEY `idx_store_type` (`store_type`),
  KEY `idx_agent_id` (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- VIP Membership Related Tables
CREATE TABLE `vip_memberships` (
  `id` INTEGER PRIMARY KEY AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `user_id` INTEGER NOT NULL COMMENT 'ID of the user',
  `level` INTEGER DEFAULT 1 COMMENT 'Membership level',
  `start_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Start time',
  `expire_time` TIMESTAMP NOT NULL COMMENT 'Expiration time',
  `status` VARCHAR(20) DEFAULT 'active' COMMENT 'Status',
  `create_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
  `update_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  KEY `idx_vip_memberships_user_status` (`user_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `vip_packages` (
  `id` INTEGER PRIMARY KEY AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `name` VARCHAR(100) NOT NULL COMMENT 'Name of the package',
  `level` INTEGER NOT NULL COMMENT 'Membership level',
  `duration` INTEGER NOT NULL COMMENT 'Duration in days',
  `price` DECIMAL(18,9) NOT NULL COMMENT 'Price',
  `description` TEXT COMMENT 'Description',
  `features` JSON COMMENT 'Features of the package',
  `is_active` tinyint(1) DEFAULT 1 COMMENT 'Whether the package is active',
  `create_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
  `update_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  KEY `idx_vip_packages_level_duration` (`level`, `duration`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- AI Image Related Tables
CREATE TABLE `ai_image_templates` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Template name',
  `preview_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Preview image URL',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Template description',
  `template_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Template image URL',
  `prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Generation prompt',
  `type` int NOT NULL DEFAULT '1' COMMENT 'Template type: 1-Custom mode, 2-X Link mode',
  `status` int NOT NULL DEFAULT '0' COMMENT 'Template status: 0-draft, 1-active, 2-inactive',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT 'Create time',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_type` (`type`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;