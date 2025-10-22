"""
SwiftBot - Ultra-Fast Telegram Bot Framework
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="SwiftBot",
    version="1.0.0",
    author="Arjun-M",
    author_email="",
    description="Ultra-fast Telegram bot framework with 30× faster routing & consume 20-30% less memory",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Arjun-M/SwiftBot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "redis": ["redis>=4.0.0"],
        "postgres": ["asyncpg>=0.27.0"],
        "mongo": ["motor>=3.0.0"],
        "full": [
            "redis>=4.0.0",
            "asyncpg>=0.27.0",
            "motor>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "swiftbot=swiftbot.cli:main",
        ],
    },
)
