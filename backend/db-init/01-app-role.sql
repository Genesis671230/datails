-- Local development only: provision the restricted application role.
-- In Azure this role is created by deployment tooling, not by the container.
-- The LD-3 migration grants this role INSERT+SELECT only on ledger tables.
CREATE ROLE datails_app LOGIN PASSWORD 'datails_app_local';
GRANT CONNECT ON DATABASE datails TO datails_app;
GRANT USAGE ON SCHEMA public TO datails_app;
