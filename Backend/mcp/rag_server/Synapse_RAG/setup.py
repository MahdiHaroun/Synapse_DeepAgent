from setuptools import setup, find_packages

setup(
    name="Synapse_RAG",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain",
        "langgraph",
        "langchain-community",
        "langchain-aws",
        "langchain-mongodb",
        "pymongo",
    ],
)
