"""VisionAudioForge Python SDK setup."""

from setuptools import find_packages, setup

setup(
    name="visionaudioforge",
    version="1.0.0",
    description="Python SDK for the VisionAudioForge REST API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="VisionAudioForge",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.25",
        "pydantic>=2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "respx>=0.20",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
