import ast
import re
import setuptools
from pathlib import Path

with open("requirements.txt") as stream:
    raw = stream.read().splitlines()
    requirements = [x for x in raw if not x.startswith("git+")]

long_description = (Path(__file__).parent / "README.md").read_text(encoding="UTF-8")

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('discord/ext/cluster/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode('UTF-8')).group(1)))

setuptools.setup(
    name="better-cluster",
    version=version,
    description="A high-performance inter-process communication library designed to handle communication between multiple shards",
    long_description=long_description,
    author="DaPandaOfficial",
    author_email="miroslav.rosenov39@gmail.com",
    url="https://github.com/MiroslavRosenov/better-cluster",
    packages=[
        "discord.ext.cluster"
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Communications",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    license="MIT License",
    keywords=[
        "better-cluster",
        "better-ipc",
        "cluster", 
        "python", 
        "discord.py"
    ],
    long_description_content_type="text/markdown",
    install_requires=requirements,
    python_requires=">=3.8.0",
    project_urls={
        "Source": "https://github.com/MiroslavRosenov/better-cluster",
        "Issue Tracker": "https://github.com/MiroslavRosenov/better-cluster/issues",
    },
)
