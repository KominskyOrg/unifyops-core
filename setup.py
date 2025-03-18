from setuptools import setup, find_packages

setup(
    name="unifyops-backend",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    description="UnifyOps Backend API",
    author="UnifyOps Team",
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.23.2",
        "pydantic>=2.4.2",
        "pydantic-settings>=2.0.3",
        "python-dotenv>=1.0.0",
    ],
) 