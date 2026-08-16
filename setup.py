"""
SwiftBot - Ultra-Fast Telegram Bot Framework
Copyright (c) 2026 Arjun-M/SwiftBot
"""

from setuptools import setup, find_packages, Command


class CleanSdist(Command):
    """Prevent egg-info from leaking into the sdist."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        pass


# Patch setuptools' sdist so egg-info is never copied in.
from setuptools.command import sdist as _sdist

_orig_make_release_tree = _sdist.sdist.make_release_tree


def _make_release_tree(self, base_dir, files):
    import shutil
    _orig_make_release_tree(self, base_dir, files)
    egg_dir = f"{base_dir}/swiftbot.egg-info"
    if __import__("os").path.isdir(egg_dir):
        shutil.rmtree(egg_dir)
        print(f"(removed swiftbot.egg-info from sdist)")


_sdist.sdist.make_release_tree = _make_release_tree

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="swiftbot",
    version="1.6.3",
    author="Arjun-M",
    author_email="arjunm@atomicmail.io",
    description="Async Telegram bot framework with typed decorators, composable filters, persistent FSM storage and a typed error hierarchy - Bot API 2026",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Arjun-M/SwiftBot",
    package_dir={'': '.'},
    packages=find_packages(where='.', exclude=['tests', 'tests.*']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: Communications :: Chat",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.10",
    install_requires=[
        "httpx[http2]>=0.27.0,<0.29.0",
    ],
    extras_require={
        "webhook": [
            "aiohttp>=3.10,<4.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "aiohttp>=3.10,<4.0",
        ],
    },
)
