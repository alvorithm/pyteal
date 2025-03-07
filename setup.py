#!/usr/bin/env python3

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyteal",
    version="0.20.1",
    author="Algorand",
    author_email="pypiservice@algorand.com",
    description="Algorand Smart Contracts in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/algorand/pyteal",
    packages=setuptools.find_packages(
        include=(
            "pyteal",
            "pyteal.*",
        )
    ),
    install_requires=[
        # when changing this list, also update docs/requirements.txt
        "py-algorand-sdk>=1.9.0,<2.0.0",
        "semantic-version>=2.9.0,<3.0.0",
        "docstring-parser==0.14.1",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_data={"pyteal": ["*.pyi", "py.typed"]},
    python_requires=">=3.10",
)
