
from setuptools import setup, find_packages

setup(
    name="xaip_tools",
    version="0.1.0",
    packages=find_packages(),  # Automatically finds all Python packages
    install_requires=[
        "shapely",
        "networkx",
    ],
)

