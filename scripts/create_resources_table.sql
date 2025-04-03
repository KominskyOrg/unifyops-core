-- Script to create resources table directly in PostgreSQL
-- Can be executed with: psql -U postgres -d unifyops -f scripts/create_resources_table.sql

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS app_schema;

-- Check if the table already exists to avoid errors
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'app_schema' AND table_name = 'resources') THEN
        -- Create resources table
        CREATE TABLE app_schema.resources (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            module_path VARCHAR(255) NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            variables JSONB NULL,
            error_message TEXT NULL,
            correlation_id VARCHAR(100) NULL,
            auto_apply VARCHAR(5) NOT NULL,
            environment_id VARCHAR(36) NOT NULL REFERENCES app_schema.environments(id),
            created_at TIMESTAMP NULL,
            updated_at TIMESTAMP NULL,
            init_execution_id VARCHAR(36) NULL,
            plan_execution_id VARCHAR(36) NULL,
            apply_execution_id VARCHAR(36) NULL
        );

        -- Create indexes
        CREATE INDEX ix_resources_name ON app_schema.resources(name);
        CREATE INDEX ix_resources_resource_type ON app_schema.resources(resource_type);
        CREATE INDEX ix_resources_environment_id ON app_schema.resources(environment_id);
        
        RAISE NOTICE 'Resources table created successfully';
    ELSE
        RAISE NOTICE 'Resources table already exists';
    END IF;
END
$$; 