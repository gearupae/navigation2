"""
Setup script for Standalone Navigation Package
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="standalone-navigation",
    version="1.0.0",
    author="Navigation Assistant",
    author_email="",
    description="A portable navigation system with modular LLM and TTS components",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "googlemaps>=4.10.0",
        "geopy>=2.4.0",
    ],
    extras_require={
        "grok": [
            "requests>=2.31.0",
        ],
        "openai": [
            "openai>=1.0.0",
        ],
        "gtts": [
            "gtts>=2.3.0",
            "pygame>=2.0.0",
        ],
        "pyttsx3": [
            "pyttsx3>=2.90",
        ],
        "full": [
            "gtts>=2.3.0",
            "pygame>=2.0.0",
            "pyttsx3>=2.90",
            "openai>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "nav-demo=navigation.examples.demo:main",
        ],
    },
)
