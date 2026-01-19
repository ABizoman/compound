from setuptools import setup, find_packages

setup(
    name="tradebot",
    version="0.1.0",
    description="Compound: An Autonomous Investing Framework",
    packages=find_packages(),
    install_requires=[
        "openai>=2.15.0",
        "pandas>=2.3.3",
        "python-dotenv>=1.2.1",
        "PyYAML>=6.0.3",
        "requests>=2.32.5",
    ],
    python_requires=">=3.8",
)
