from setuptools import setup

setup(
    name="csharpgen",
    version="0.0.1",
    description="C# code generator for Silvera tool",
    entry_points={
        "silvera_generators": ["csharp = csharpgen.generator:csharp"],
        "silvera_evaluators": ["myeval = csharpgen.evaluator:myeval"]
    },
    install_requires=["silvera", "Jinja2"]
)
