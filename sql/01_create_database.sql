-- CareerScope: create the database. Safe to run more than once.
USE master;
GO

IF DB_ID(N'CareerScope') IS NULL
BEGIN
    CREATE DATABASE CareerScope;
END
GO

-- Simple recovery keeps the transaction log small during large loads.
ALTER DATABASE CareerScope SET RECOVERY SIMPLE;
GO

USE CareerScope;
GO

SELECT DB_NAME() AS current_database,
       CAST(SERVERPROPERTY('ProductVersion') AS varchar(50)) AS sql_server_version;
GO