from setuptools import setup, find_packages

setup(
    name="browser_use",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "playwright",  # Assuming this is needed based on the directory structure
        "langchain",
        "langchain_openai",
        "python-dotenv",
        # Add other dependencies as needed
    ],
    description="Browser automation agent for performing goal-oriented tasks online",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/browser_use",
    python_requires=">=3.8",
)
