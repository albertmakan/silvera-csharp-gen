import os
from jinja2 import Environment, FileSystemLoader
from silvera.generator.registration import GeneratorDesc
from csharpgen.utils import get_templates_path


def generate_service(service, output_dir):
    templates_path = get_templates_path()
    env = Environment(loader=FileSystemLoader(templates_path))

    main_path = os.path.join(output_dir, service.name)
    if not os.path.exists(main_path):
        os.mkdir(main_path)

    main_template = env.get_template("main.template")
    main_template.stream({}).dump(os.path.join(main_path, "Main.cs"))


def generate(decl, output_dir, debug):
    print("Called C#!")
    print(decl, output_dir)
    generate_service(decl, output_dir)


# Create Python generator.
csharp = GeneratorDesc(
    language_name="csharp",
    language_ver="10",
    description="C# 10 code generator",
    gen_func=generate
)
