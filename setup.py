from pathlib import Path

from setuptools import find_packages, setup

with Path.open("README.md") as readme_file:
    README = readme_file.read()


setup_args = {
    "name": "dequest",
    "version": "0.2.0",
    "description": "Declarative rest client",
    "long_description_content_type": "text/markdown",
    "long_description": README,
    "license": "GNU",
    "packages": find_packages(),
    "author": "M.Shaeri",
    "keywords": ["request", "declarative", "api", "rest", "rest client"],
    "url": "https://github.com/birddevelper/dequest",
    "download_url": "https://github.com/birddevelper/dequest",
}

install_requires = [
    "requests",
    "redis",
    "responses",
    "defusedxml",
    "httpx",
]

if __name__ == "__main__":
    setup(**setup_args, install_requires=install_requires)
