from setuptools import setup, find_packages


setup(
      name="SwiftBot",
      version="0.0.1",
      description=" A lightweight and user-friendly Python package for building powerful Telegram bots effortlessly .",
      author="Arjun-M",      
      url="https://github.com/Arjun-M/SwiftBot",
      packages = ['SwiftBot'] ,
      license='MIT',      
      install_requires=['requests','aiohttp','urllib3'],
)
