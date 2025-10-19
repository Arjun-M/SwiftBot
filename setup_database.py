"""
Database Setup Script for SwiftBot
Copyright (c) 2025 Arjun-M/SwiftBot

This script helps you set up databases for SwiftBot storage.
"""

import asyncio
import sys


async def setup_postgres():
    """
    Setup PostgreSQL database for SwiftBot.

    Requirements:
    - PostgreSQL installed and running
    - asyncpg: pip install asyncpg
    """
    print("\n=== PostgreSQL Setup ===\n")

    try:
        import asyncpg
    except ImportError:
        print("❌ asyncpg not installed. Install with: pip install asyncpg")
        return

    # Get database credentials
    print("Enter PostgreSQL connection details:")
    host = input("Host (default: localhost): ") or "localhost"
    port = input("Port (default: 5432): ") or "5432"
    user = input("Username (default: postgres): ") or "postgres"
    password = input("Password: ")
    database = input("Database name (default: swiftbot): ") or "swiftbot"

    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    try:
        # Connect to PostgreSQL
        print("\nConnecting to PostgreSQL...")
        pool = await asyncpg.create_pool(connection_string)

        # Create table
        print("Creating tables...")
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS swiftbot_user_data (
                    user_id BIGINT NOT NULL,
                    key VARCHAR(255) NOT NULL,
                    value JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, key)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_swiftbot_user_data_user_id 
                ON swiftbot_user_data (user_id)
            """)

        await pool.close()

        print("✅ PostgreSQL setup complete!")
        print(f"\nUse this configuration in your bot:")
        print(f"""
import asyncpg
from swiftbot.storage import PostgresStore

pool = await asyncpg.create_pool("{connection_string}")
storage = PostgresStore(connection=pool)
        """)

    except Exception as e:
        print(f"❌ Error: {e}")


async def setup_mongodb():
    """
    Setup MongoDB for SwiftBot.

    Requirements:
    - MongoDB installed and running
    - motor: pip install motor
    """
    print("\n=== MongoDB Setup ===\n")

    try:
        import motor.motor_asyncio
    except ImportError:
        print("❌ motor not installed. Install with: pip install motor")
        return

    # Get MongoDB connection details
    print("Enter MongoDB connection details:")
    host = input("Host (default: localhost): ") or "localhost"
    port = input("Port (default: 27017): ") or "27017"
    database = input("Database name (default: swiftbot): ") or "swiftbot"
    username = input("Username (optional): ")
    password = input("Password (optional): ")

    # Build connection string
    if username and password:
        connection_string = f"mongodb://{username}:{password}@{host}:{port}"
    else:
        connection_string = f"mongodb://{host}:{port}"

    try:
        # Connect to MongoDB
        print("\nConnecting to MongoDB...")
        client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)

        # Test connection
        await client.admin.command('ping')

        # Create indexes
        print("Creating indexes...")
        db = client[database]
        collection = db["user_data"]

        await collection.create_index([("user_id", 1), ("key", 1)], unique=True)
        await collection.create_index("user_id")

        client.close()

        print("✅ MongoDB setup complete!")
        print(f"\nUse this configuration in your bot:")
        print(f"""
import motor.motor_asyncio
from swiftbot.storage import MongoStore

client = motor.motor_asyncio.AsyncIOMotorClient("{connection_string}")
storage = MongoStore(connection=client, database="{database}")
        """)

    except Exception as e:
        print(f"❌ Error: {e}")


def setup_redis():
    """
    Setup Redis for SwiftBot.

    Requirements:
    - Redis installed and running
    - redis: pip install redis
    """
    print("\n=== Redis Setup ===\n")

    try:
        import redis
    except ImportError:
        print("❌ redis not installed. Install with: pip install redis")
        return

    # Get Redis connection details
    print("Enter Redis connection details:")
    host = input("Host (default: localhost): ") or "localhost"
    port = input("Port (default: 6379): ") or "6379"
    db = input("Database number (default: 0): ") or "0"
    password = input("Password (optional): ")

    try:
        # Connect to Redis
        print("\nConnecting to Redis...")
        if password:
            r = redis.Redis(host=host, port=int(port), db=int(db), password=password)
        else:
            r = redis.Redis(host=host, port=int(port), db=int(db))

        # Test connection
        r.ping()

        print("✅ Redis setup complete!")
        print(f"\nUse this configuration in your bot:")
        if password:
            print(f"""
import redis
from swiftbot.storage import RedisStore

redis_conn = redis.Redis(host='{host}', port={port}, db={db}, password='{password}')
storage = RedisStore(connection=redis_conn)
            """)
        else:
            print(f"""
import redis
from swiftbot.storage import RedisStore

redis_conn = redis.Redis(host='{host}', port={port}, db={db})
storage = RedisStore(connection=redis_conn)
            """)

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main setup menu"""
    print("=" * 60)
    print("SwiftBot Database Setup")
    print("Copyright (c) 2025 Arjun-M/SwiftBot")
    print("=" * 60)

    print("\nChoose database to setup:")
    print("1. Redis (recommended)")
    print("2. PostgreSQL")
    print("3. MongoDB")
    print("4. File Storage (no setup needed)")
    print("0. Exit")

    choice = input("\nEnter choice (0-4): ")

    if choice == "1":
        setup_redis()
    elif choice == "2":
        asyncio.run(setup_postgres())
    elif choice == "3":
        asyncio.run(setup_mongodb())
    elif choice == "4":
        print("\n=== File Storage ===\n")
        print("File storage requires no setup!")
        print("\nUse this configuration in your bot:")
        print("""
from swiftbot.storage import FileStore

storage = FileStore(base_path="./data")
        """)
    elif choice == "0":
        print("Exiting...")
        sys.exit(0)
    else:
        print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled")
        sys.exit(0)
