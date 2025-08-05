"""
Setup configuration for FinCLI package.
"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fincli",
    version="0.1.0",
    author="FinCLI Team",
    author_email="team@fincli.dev",
    description="A lightweight task tracking system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fincli/fincli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "fin=fincli.cli:cli",
            "fins=fincli.cli:list_tasks",
            "fine=fincli.cli:open_editor",
            "fin-labels=fincli.cli:list_labels",
            "fin-import=fincli.cli:import_tasks",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
