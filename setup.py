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
    name="swiftbot",
    version="1.1.0",
    author="Arjun-M",
    author_email="",
    description="Async Telegram bot framework with typed decorators, composable filters, persistent FSM storage and a typed error hierarchy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Arjun-M/SwiftBot",
    package_dir={'': '.'},
    packages=find_packages(where='.'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Chat",
        "Framework :: AsyncIO"
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "aiohttp>=3.10",
        ]
    },
)
