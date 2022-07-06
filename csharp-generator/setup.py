from setuptools import setup

setup(
    name="csharpgen",
    version="0.0.1",
    description="C# code generator for Silvera tool",

    entry_points={
        "silvera_generators": [
            # Java generator is built-in
            "csharp = csharpgen.generator:csharp",
        ],

        "silvera_evaluators": [
            # Java generator is built-in
            "myeval = csharpgen.evaluator:myeval",
        ]
    },
)
