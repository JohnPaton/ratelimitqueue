from setuptools import setup


with open("README.md", "r") as h:
    README = h.read()


setup(
    name="ratelimitqueue",
    version="0.1.0",
    description="A thread safe, rate limited queue.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://www.github.com/JohnPaton/ratelimitqueue",
    author="John Paton",
    author_email="john@johnpaton.net",
    python_requires=">=3.4",
    packages=["ratelimitqueue"],
)
