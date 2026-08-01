import asyncio
import logging
from database.connection import get_conn, init_db

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("database.migrate")


async def run_migrations() -> None:
    """
    Runs DDL schema migrations to convert VARCHAR date columns to native TIMESTAMP.
    This runs out-of-band (manually or via CI/CD startup hooks) to avoid blocking 
    and locking tables on application runtime startup.
    """
    logger.info("Starting database migrations...")
    
    # Ensure tables exist first
    await init_db()
    
    async with get_conn() as conn:
        # Users migration
        logger.info("Migrating table 'users' joined_at column...")
        try:
            await conn.execute("ALTER TABLE users ALTER COLUMN joined_at DROP DEFAULT")
            await conn.execute("ALTER TABLE users ALTER COLUMN joined_at TYPE TIMESTAMP USING joined_at::timestamp")
            await conn.execute("ALTER TABLE users ALTER COLUMN joined_at SET DEFAULT CURRENT_TIMESTAMP")
            logger.info("Table 'users' migration completed.")
        except Exception as e:
            logger.exception("Failed to migrate table 'users': %s", e)

        # Votes migration
        logger.info("Migrating table 'votes' datetime columns...")
        try:
            await conn.execute("ALTER TABLE votes ALTER COLUMN voted_at DROP DEFAULT")
            await conn.execute("ALTER TABLE votes ALTER COLUMN voted_at TYPE TIMESTAMP USING voted_at::timestamp")
            await conn.execute("ALTER TABLE votes ALTER COLUMN voted_at SET DEFAULT CURRENT_TIMESTAMP")
            await conn.execute("ALTER TABLE votes ALTER COLUMN confirmed_at TYPE TIMESTAMP USING confirmed_at::timestamp")
            logger.info("Table 'votes' migration completed.")
        except Exception as e:
            logger.exception("Failed to migrate table 'votes': %s", e)

        # Referrals migration
        logger.info("Migrating table 'referrals' joined_at column...")
        try:
            await conn.execute("ALTER TABLE referrals ALTER COLUMN joined_at DROP DEFAULT")
            await conn.execute("ALTER TABLE referrals ALTER COLUMN joined_at TYPE TIMESTAMP USING joined_at::timestamp")
            await conn.execute("ALTER TABLE referrals ALTER COLUMN joined_at SET DEFAULT CURRENT_TIMESTAMP")
            logger.info("Table 'referrals' migration completed.")
        except Exception as e:
            logger.exception("Failed to migrate table 'referrals': %s", e)

        # Payment Requests migration
        logger.info("Migrating table 'payment_requests' datetime columns...")
        try:
            await conn.execute("ALTER TABLE payment_requests ALTER COLUMN requested_at DROP DEFAULT")
            await conn.execute("ALTER TABLE payment_requests ALTER COLUMN requested_at TYPE TIMESTAMP USING requested_at::timestamp")
            await conn.execute("ALTER TABLE payment_requests ALTER COLUMN requested_at SET DEFAULT CURRENT_TIMESTAMP")
            await conn.execute("ALTER TABLE payment_requests ALTER COLUMN processed_at TYPE TIMESTAMP USING processed_at::timestamp")
            logger.info("Table 'payment_requests' migration completed.")
        except Exception as e:
            logger.exception("Failed to migrate table 'payment_requests': %s", e)

        # Audit Logs migration
        logger.info("Migrating table 'audit_logs' timestamp column...")
        try:
            await conn.execute("ALTER TABLE audit_logs ALTER COLUMN timestamp DROP DEFAULT")
            await conn.execute("ALTER TABLE audit_logs ALTER COLUMN timestamp TYPE TIMESTAMP USING timestamp::timestamp")
            await conn.execute("ALTER TABLE audit_logs ALTER COLUMN timestamp SET DEFAULT CURRENT_TIMESTAMP")
            logger.info("Table 'audit_logs' migration completed.")
        except Exception as e:
            logger.exception("Failed to migrate table 'audit_logs': %s", e)

    logger.info("Database migrations completed successfully.")


if __name__ == "__main__":
    asyncio.run(run_migrations())
