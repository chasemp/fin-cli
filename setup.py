from setuptools import setup, find_packages

setup(
    name="fin",
    version="0.1.0",
    description="A lightweight, macOS-first local task-tracking system",
    author="Fin Team",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "fin=fin.cli.main:main",
            "fin-legacy=fin.cli.legacy:legacy_main",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
) 