from pathlib import Path

from setuptools import find_packages, setup

with Path.open("README.md") as readme_file:
    README = readme_file.read()


setup_args = {
    "name": "dequest",
    "version": "0.7.0",
    "description": "Declarative HTTP client",
    "long_description_content_type": "text/markdown",
    "long_description": README,
    "license": "GNU",
    "packages": find_packages(),
    "author": "Bird Developer",
    "keywords": [
        "request",
        "declarative",
        "api",
        "rest",
        "rest client",
        "http client",
        "httpx",
    ],
    "url": "https://github.com/birddevelper/dequest",
    "download_url": "https://github.com/birddevelper/dequest",
    "python_requires": ">=3.8",
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Framework :: AsyncIO",
    ],
}

install_requires = [
    "redis>=5.2.1",
    "defusedxml>=0.7.1",
    "httpx>=0.28.1",
]

if __name__ == "__main__":
    setup(**setup_args, install_requires=install_requires)
