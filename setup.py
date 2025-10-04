"""Setup configuration for VisionGlove project."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#') and not line.startswith('-')
        ]
else:
    requirements = []

setup(
    name="vision-glove",
    version="1.0.0",
    author="VisionGlove Development Team",
    author_email="contact@visionglove.dev",
    description="A cybernetic glove project for enhanced safety and capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rmadatt/VisionGlove",
    project_urls={
        "Bug Reports": "https://github.com/rmadatt/VisionGlove/issues",
        "Source": "https://github.com/rmadatt/VisionGlove",
        "Documentation": "https://github.com/rmadatt/VisionGlove/wiki",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware",
        "Topic :: Security",
        "Topic :: Multimedia :: Video :: Capture",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.19.0", 
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
        "hardware": [
            "RPi.GPIO>=0.7.1",
            "adafruit-circuitpython-busdevice>=5.2.0",
        ],
        "streaming": [
            "streamlink>=4.0.0",
            "ffmpeg-python>=0.2.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "vision-glove=vision_glove.cli:main",
            "vg-calibrate=vision_glove.scripts.calibrate:main",
            "vg-test=vision_glove.scripts.test_systems:main",
        ],
    },
    include_package_data=True,
    package_data={
        "vision_glove": [
            "config/*.json",
            "config/*.yaml", 
            "data/*",
            "models/*",
        ],
    },
    keywords=[
        "cybernetic", "glove", "computer-vision", "safety", "security",
        "IoT", "wearable", "sensors", "haptics", "emergency-response"
    ],
    zip_safe=False,
)
