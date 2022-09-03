from setuptools import setup

setup(
    name="silvera-csharp-gen",
    version="0.0.1",
    description="C# code generator for Silvera tool",
    packages=['csharpgen'],
    entry_points={
        "silvera_generators": ["csharp = csharpgen.generator:csharp"]
    },
    install_requires=["silvera", "Jinja2"]
)
