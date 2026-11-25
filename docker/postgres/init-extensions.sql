-- ==============================================================================
-- PostgreSQL 16 + TimescaleDB + pgvector Initialization Script
-- ==============================================================================
-- Executed automatically when the TimescaleDB-HA container initializes.

-- Enable TimescaleDB for high-performance financial time-series data
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable pgvector for semantic document embeddings and RAG retrieval
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation and trigram text similarity search
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
