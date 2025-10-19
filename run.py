#!/usr/bin/env python3
"""
SwiftBot Launcher Script
Copyright (c) 2025 Arjun-M/SwiftBot

Quick launcher for SwiftBot with various modes and configurations.
"""

import sys
import os
import asyncio
import argparse


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import httpx
    except ImportError:
        print("❌ httpx not installed. Install with: pip install httpx httpx[http2]")
        sys.exit(1)

    print("✅ Core dependencies installed")


def run_basic_example():
    """Run the basic example bot"""
    print("\n" + "="*60)
    print("Running Basic Example Bot")
    print("="*60 + "\n")

    os.system(f"{sys.executable} example_basic.py")


def run_advanced_example():
    """Run the advanced example bot"""
    print("\n" + "="*60)
    print("Running Advanced Example Bot")
    print("="*60 + "\n")

    # Check if Redis is available
    try:
        import redis
        redis_conn = redis.Redis(host='localhost', port=6379, db=0)
        redis_conn.ping()
        print("✅ Redis connected")
    except:
        print("⚠️  Redis not available. Using file storage.")

    os.system(f"{sys.executable} example_advanced.py")


def run_webhook_example():
    """Run the webhook example bot"""
    print("\n" + "="*60)
    print("Running Webhook Example Bot")
    print("="*60 + "\n")

    try:
        import aiohttp
        print("✅ aiohttp installed")
    except ImportError:
        print("❌ aiohttp not installed. Install with: pip install aiohttp")
        sys.exit(1)

    os.system(f"{sys.executable} example_webhook.py")


def setup_database():
    """Run database setup script"""
    print("\n" + "="*60)
    print("Database Setup")
    print("="*60 + "\n")

    os.system(f"{sys.executable} setup_database.py")


def show_info():
    """Show bot information"""
    print("\n" + "="*60)
    print("SwiftBot Information")
    print("="*60)
    print("\nVersion: 1.0.0")
    print("Copyright: (c) 2025 Arjun-M/SwiftBot")
    print("License: MIT")
    print("\nPython:", sys.version)
    print("\nInstalled packages:")

    packages = {
        "httpx": "Core dependency",
        "redis": "Redis storage (optional)",
        "asyncpg": "PostgreSQL storage (optional)",
        "motor": "MongoDB storage (optional)",
        "aiohttp": "Webhook server (optional)",
    }

    for package, description in packages.items():
        try:
            __import__(package)
            print(f"  ✅ {package}: {description}")
        except ImportError:
            print(f"  ❌ {package}: {description}")

    print("\nDocumentation:")
    print("  • README.md - Project overview")
    print("  • QUICKSTART.md - 5-minute guide")
    print("  • USAGE.md - Complete guide")
    print("  • INSTALL.md - Installation guide")
    print("  • DOCUMENTATION.md - Technical reference")

    print("\nExamples:")
    print("  • example_basic.py - Basic bot")
    print("  • example_advanced.py - Advanced features")
    print("  • example_webhook.py - Webhook mode")


def main():
    """Main launcher function"""
    parser = argparse.ArgumentParser(
        description="SwiftBot Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --basic          Run basic example
  python run.py --advanced       Run advanced example
  python run.py --webhook        Run webhook example
  python run.py --setup-db       Setup database
  python run.py --info           Show information
        """
    )

    parser.add_argument(
        "--basic",
        action="store_true",
        help="Run basic example bot"
    )

    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Run advanced example bot"
    )

    parser.add_argument(
        "--webhook",
        action="store_true",
        help="Run webhook example bot"
    )

    parser.add_argument(
        "--setup-db",
        action="store_true",
        help="Setup database"
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="Show bot information"
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check dependencies"
    )

    args = parser.parse_args()

    # If no arguments, show menu
    if not any(vars(args).values()):
        print("=" * 60)
        print("SwiftBot Launcher")
        print("Copyright (c) 2025 Arjun-M/SwiftBot")
        print("=" * 60)
        print("\nWhat would you like to do?")
        print("\n1. Run basic example")
        print("2. Run advanced example")
        print("3. Run webhook example")
        print("4. Setup database")
        print("5. Show information")
        print("6. Check dependencies")
        print("0. Exit")

        choice = input("\nEnter choice (0-6): ")

        if choice == "1":
            run_basic_example()
        elif choice == "2":
            run_advanced_example()
        elif choice == "3":
            run_webhook_example()
        elif choice == "4":
            setup_database()
        elif choice == "5":
            show_info()
        elif choice == "6":
            check_dependencies()
        elif choice == "0":
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid choice")
            sys.exit(1)
    else:
        # Handle command line arguments
        if args.check:
            check_dependencies()
        elif args.basic:
            run_basic_example()
        elif args.advanced:
            run_advanced_example()
        elif args.webhook:
            run_webhook_example()
        elif args.setup_db:
            setup_database()
        elif args.info:
            show_info()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(0)
