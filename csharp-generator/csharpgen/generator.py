import os
import sys
import warnings
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader

from silvera.generator.registration import GeneratorDesc
from silvera.core import ServiceDecl, FunctionParameter, MessageGroup, ConsumerAnnotation, \
    TypeDef, TypedList, TypedSet, TypedDict

from csharpgen.type_converter import convert_type, get_default_for_cb_pattern, DEP_NS
from csharpgen.utils import get_templates_path, create_backup_file
from csharpgen.project_struct import create_if_missing, csharp_struct
from csharpgen.validators import check_messaging, check_fields, check_duplicates_in_api
from csharpgen.formatters import *


class ServiceGenerator:
    def __init__(self, service: ServiceDecl, output_dir):
        self.service = service
        self.env = self._init_env()
        self.main_path = csharp_struct(output_dir, service.name)

    def _init_env(self):
        env = Environment(loader=FileSystemLoader(get_templates_path()))

        env.filters["first_upper"] = first_upper
        env.filters["first_lower"] = first_lower
        env.filters["first_upper_fqn"] = first_upper_fqn
        env.filters["convert_type_in_model"] = lambda t: convert_type(t, "")
        env.filters["convert_type"] = convert_type
        env.filters["convert_dep_type"] = lambda t: convert_type(t, DEP_NS)
        env.filters["unfold_function_params"] = \
            lambda f: ', '.join([f"{convert_type(p.type)} {p.name}" for p in f.params])
        env.filters["unfold_dep_function_params"] = \
            lambda f: ', '.join([f"{convert_type(p.type, DEP_NS)} {p.name}" for p in f.params])
        env.filters["unfold_record_params"] = \
            lambda f: ', '.join([f"{convert_type(p.type, DEP_NS)} {first_upper(p.name)}" for p in f.params])
        env.filters["unfold_controller_function_params"] = self.unfold_controller_function_params
        env.filters["param_names_controller"] = param_names_controller
        env.filters["param_names"] = lambda f: ", ".join([p.name for p in f.params])
        env.filters["get_default_ret_val"] = get_default_for_cb_pattern

        env.globals["request_uri_and_body"] = request_uri_and_body
        env.globals["as_type"] = lambda t: "Models."+t
        env.globals["service_name"] = self.service.name
        env.globals["header_comment"] = get_comment

        return env

    def generate(self):
        check_messaging(self.service)
        check_duplicates_in_api(self.service)
        self.generate_model()
        self.generate_repositories()
        if self.service.produces:
            self.generate_message_producer()
        if self.service.consumes:
            self.generate_message_consumer()
        self.generate_messages()
        self.generate_other_files()
        self.generate_controller()
        if self.service.dependencies:
            self.generate_dependency_services()
        self.generate_service()
        self.generate_startup()
        self.generate_csproj()
        self.generate_settings()

    def generate_model(self):
        models_path = create_if_missing(os.path.join(self.main_path, "Models"))
        class_template = self.env.get_template("models/model_class.template")

        for typedef in self.service.api.typedefs:
            typedef.name = first_upper(typedef.name)
            id_attr = [a for a in typedef.fields if a.isid]
            if len(id_attr) > 1:
                raise Exception(f"{self.service.name}: Duplicate @id in {typedef.name}!")
            if id_attr and id_attr[0].type != "str":
                raise Exception(f"{self.service.name}: {typedef.name}: Only string ids are supported for now.")

            class_template.stream({
                "name": typedef.name,
                "attributes": typedef.fields,
                "id_attr": id_attr[0] if id_attr else None,
            }).dump(os.path.join(models_path, typedef.name + ".cs"))

            if typedef.inherits:
                warnings.warn("Inheritance is not supported yet.")

        def recurse_typedef(_type, visited=None):
            """Find all types that the current service will depend upon"""
            if visited is None:
                visited = set()
            if _type in visited:
                return visited
            if isinstance(_type, TypeDef):
                visited.add(_type)
                for field in _type.fields:
                    recurse_typedef(field.type, visited)
            elif isinstance(_type, (TypedList, TypedSet)):
                recurse_typedef(_type.type, visited)
            elif isinstance(_type, TypedDict):
                recurse_typedef(_type.key_type, visited)
                recurse_typedef(_type.value_type, visited)
            return visited

        dep_typedefs = self.service.dep_typedefs
        for df in self.service.dep_functions:
            for p in df.params:
                dep_typedefs.extend(recurse_typedef(p.type))

        if not dep_typedefs:
            return
        dependencies_path = create_if_missing(os.path.join(models_path, "Dependencies"))
        class_template = self.env.get_template("models/dep_class.template")

        for typedef in dep_typedefs:
            check_fields(typedef)
            typedef.name = first_upper(typedef.name)
            class_template.stream({
                "name": typedef.name,
                "attributes": typedef.fields,
            }).dump(os.path.join(dependencies_path, typedef.name + ".cs"))

    def generate_repositories(self):
        repo_path = create_if_missing(os.path.join(self.main_path, "Repository"))
        base_path = create_if_missing(os.path.join(repo_path, "Contracts"))
        impl_path = create_if_missing(os.path.join(repo_path, "Impl"))
        self.env.get_template("repository/i_repository.template").stream().dump(
            os.path.join(base_path, "IRepository.cs"))
        self.env.get_template("repository/repository.template").stream().dump(
            os.path.join(impl_path, "Repository.cs"))
        for typedef in self.service.api.typedefs:
            id_datatype = "string"
            if not typedef.crud_dict:
                continue
            d = {"typedef": typedef.name, "id_datatype": id_datatype}
            self.env.get_template("repository/iX_repository.template").stream(d).dump(
                os.path.join(base_path, f"I{typedef.name}Repository.cs"))
            self.env.get_template("repository/X_repository.template").stream(d).dump(
                os.path.join(impl_path, f"{typedef.name}Repository.cs"))

    def generate_message_producer(self):
        msg_path = create_if_missing(os.path.join(self.main_path, "Messaging"))
        messages_path = create_if_missing(os.path.join(msg_path, "Messages"))
        self.env.get_template("messaging/i_message.template").stream().dump(
            os.path.join(messages_path, "IMessage.cs"))
        self.env.get_template("messaging/producer.template").stream().dump(
            os.path.join(msg_path, "KafkaProducer.cs"))

    def generate_message_consumer(self):
        msg_path = create_if_missing(os.path.join(self.main_path, "Messaging"))
        messages_path = create_if_missing(os.path.join(msg_path, "Messages"))
        self.env.get_template("messaging/i_message.template").stream().dump(
            os.path.join(messages_path, "IMessage.cs"))
        self.env.get_template("messaging/consumer.template").stream().dump(
            os.path.join(msg_path, "KafkaConsumer.cs"))

    def generate_other_files(self):
        self.env.get_template("others/exceptions.template").stream().dump(
            os.path.join(create_if_missing(os.path.join(self.main_path, "Exceptions")), "CustomExceptions.cs"))
        self.env.get_template("others/error_middleware.template").stream().dump(
            os.path.join(create_if_missing(os.path.join(self.main_path, "Middleware")), "ErrorHandlerMiddleware.cs"))
        self.env.get_template("others/validate_model_attribute.template").stream().dump(
            os.path.join(create_if_missing(os.path.join(self.main_path, "Filters")), "ValidateModelAttribute.cs"))

    def unfold_controller_function_params(self, func: Function):
        params, from_body = [], []
        for p in func.params:
            if p.url_placeholder:
                params.append(f"[FromRoute] {convert_type(p.type)} {p.name}")
            elif p.query_param:
                params.append(f"[FromQuery] {convert_type(p.type)} {p.name}")
            elif func.http_verb in {HTTP_POST, HTTP_PUT}:
                from_body.append(p)
            else:
                params.append(f"[FromQuery] {convert_type(p.type)} {p.name}")
                p.query_param = True
        if len(from_body) > 1:
            dto = self.generate_dto(first_upper(func.name)+"Request", from_body)
            params.append(f"[FromBody] DTO.{dto} request")
        elif from_body:
            params.append(f"[FromBody] {convert_type(from_body[0].type)} {from_body[0].name}")
        return ", ".join(params)

    def generate_dto(self, name: str, params: list[FunctionParameter]):
        dto_path = create_if_missing(os.path.join(self.main_path, "DTO"))
        self.env.get_template("controllers/dto.template").stream({
            "name": name,
            "fields": [(p.type, p.name) for p in params]
        }).dump(os.path.join(dto_path, name+".cs"))
        return name

    def generate_dependency_services(self):
        services_path = create_if_missing(os.path.join(self.main_path, "Services"))
        dep_path = create_if_missing(os.path.join(services_path, "Dependencies"))

        fns_by_service = defaultdict(list)
        use_circuit_breaker = False
        for fn in self.service.dep_functions:
            if fn.cb_pattern not in {None, "fail_fast"}:
                use_circuit_breaker = True
            fns_by_service[fn.service_name].append(fn)

        self.env.get_template("utils/url_helpers.template").stream().dump(
            os.path.join(create_if_missing(os.path.join(self.main_path, "Utils")), "UrlHelpers.cs"))
        dep_template = self.env.get_template("services/dependency_service.template")
        for s in self.service.dependencies:
            dep_template.stream({
                "dependency_service_name": s.name,
                "functions": fns_by_service[s.name],
                "has_domain_dependencies": len(self.service.dep_typedefs) > 0,
                "use_circuit_breaker": use_circuit_breaker,
                "uses_registry": bool(s.service_registry),
                "service_url": f"{s.url}:{s.port}/"
            }).dump(os.path.join(dep_path, s.name + "Client.cs"))

    def generate_service(self):
        services_path = create_if_missing(os.path.join(self.main_path, "Services"))
        base_path = create_if_missing(os.path.join(services_path, "Base"))
        impl_path = create_if_missing(os.path.join(services_path, "Impl"))

        to_inject = [(f"I{t.name}Repository", f"{first_lower(t.name)}Repository") for t in self.service.api.typedefs
                     if t.crud_dict]
        to_inject.extend([(f"I{d.name}Client", f"{first_lower(d.name)}Client") for d in self.service.dependencies])
        if self.service.produces:
            to_inject.append(("IKafkaProducer", "kafkaProducer"))
        msg_per_function, function_per_channel = consumer_f(self.service)

        self.env.get_template("services/i_service.template").stream({
            "service": self.service, "msg_per_function": msg_per_function
        }).dump(os.path.join(base_path, f"I{self.service.name}Service.cs"))

        impl_file = os.path.join(impl_path, f"{self.service.name}Service.cs")
        if os.path.exists(impl_file):
            create_backup_file(impl_file)
        self.env.get_template("services/service.template").stream({
            "service": self.service,
            "to_inject": to_inject,
            "constructor_params": ', '.join([f"{t} {name}" for t, name in to_inject]),
            "function_per_channel": function_per_channel,
            "msg_per_function": msg_per_function
        }).dump(impl_file)

    def generate_controller(self):
        controller_path = create_if_missing(os.path.join(self.main_path, "Controllers"))
        self.env.get_template("controllers/controller.template").stream({
            "api": self.service.api,
        }).dump(os.path.join(controller_path, self.service.name + "Controller.cs"))

    def generate_startup(self):
        self.env.get_template("startup.template").stream({
            "producer_needed": bool(self.service.produces),
            "repositories": [t.name for t in self.service.api.typedefs if t.crud_dict],
            "clients": [c.name for c in self.service.dependencies]
        }).dump(os.path.join(self.main_path, "Startup.cs"))
        self.env.get_template("program.template").stream({
            "port": self.service.port
        }).dump(os.path.join(self.main_path, "Program.cs"))

    def generate_csproj(self):
        self.env.get_template("csproj.template").stream({
            "producer_needed": bool(self.service.produces),
            "consumer_needed": bool(self.service.consumes),
            "httpclient_needed": bool(self.service.dependencies)
        }).dump(os.path.join(self.main_path, self.service.name+".csproj"))

    def generate_settings(self):
        self.env.get_template("settings/mongo_db_settings.template").stream().dump(
            os.path.join(create_if_missing(os.path.join(self.main_path, "Settings")), "MongoDbSettings.cs"))
        should_register = bool(self.service.service_registry)
        self.env.get_template("appsettings.template").stream({
            "database_name": "test",
            "port": self.service.port,
            "registry_url": self.service.service_registry.url if should_register else '',
            "registry_port": self.service.service_registry.port if should_register else '',
            "should_register": should_register
        }).dump(os.path.join(self.main_path, "appsettings.json"))
        self.env.get_template("launchSettings.template").stream({
            "port": self.service.port
        }).dump(os.path.join(create_if_missing(os.path.join(self.main_path, "Properties")), "launchSettings.json"))

    def generate_messages(self):
        messages = set(self.service.produces.keys())
        messages.update(self.service.consumes.keys())
        if not messages:
            return
        msg_template = self.env.get_template("messaging/message.template")

        def create_package(msg_group: MessageGroup, path: str, parent_ns="Messages"):
            ns = first_upper(msg_group.name)
            curr_path = create_if_missing(os.path.join(path, ns))
            curr_ns = f"{parent_ns}.{ns}"
            for msg in msg_group.messages:
                if msg in messages:
                    check_fields(msg)
                    msg_template.stream({
                        "namespace": curr_ns, "message": msg
                    }).dump(os.path.join(curr_path, first_upper(msg.name)+".cs"))
            for gr in msg_group.groups:
                create_package(gr, curr_path, curr_ns)

        messages_path = create_if_missing(os.path.join(
            create_if_missing(os.path.join(self.main_path, "Messaging")), "Messages"))
        for mg in self.service.parent.model.msg_pool.groups:
            create_package(mg, messages_path)


def generate(service: ServiceDecl, output_dir, debug):
    print("Called C#!")
    print(service, output_dir, debug)
    sg = ServiceGenerator(service, output_dir)
    try:
        sg.generate()
    except Exception as e:
        sys.exit(e)


def consumer_f(service: ServiceDecl):
    mpf, fpc = defaultdict(set), defaultdict(set)
    internal = service.api.internal
    if not internal:
        return mpf, fpc
    for f in internal.functions:
        for ann in f.msg_annotations:
            if isinstance(ann, ConsumerAnnotation):
                for sub in ann.subscriptions:
                    mpf[f.name].add(sub.channel.msg_type.fqn)
                    fpc[sub.channel].add(f.name)
    return mpf, fpc


# Create C# generator.
csharp = GeneratorDesc(
    language_name="csharp",
    language_ver="10",
    description="C# 10 code generator",
    gen_func=generate
)
