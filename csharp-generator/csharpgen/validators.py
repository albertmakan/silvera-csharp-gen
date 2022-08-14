from typing import Union
import re

from silvera.const import *
from silvera.core import ServiceDecl, TypeDef, Message, ConsumerAnnotation

from csharpgen.formatters import first_upper, first_upper_fqn
from csharpgen.type_converter import convert_type


def check_messaging(service: ServiceDecl):
    messages = set(service.produces.keys())
    messages.update(service.consumes.keys())
    fqns = []
    for m in messages:
        if first_upper(m.name) in ["Message", "IMessage"]:
            raise Exception(f'Message name cannot be Message or IMessage')
        fqn = first_upper_fqn(m.fqn)
        if fqn in fqns:
            raise Exception(f"Duplicate message found: {fqn}")
        fqns.append(fqn)

    channels = {}
    brokers = service.parent.model.msg_brokers
    for mb in brokers:
        for ch in brokers[mb].channels:
            if ch in channels:
                raise Exception("Duplicate channel name found: ", ch)
        channels.update(brokers[mb].channels)

    for m in service.consumes:
        for ch in service.consumes[m]:
            if ch.msg_type.fqn != m.fqn:
                raise Exception(f"{service.name}: Cannot consume message of type {m.fqn} from channel "
                                f"{ch.name}({ch.msg_type.fqn})")
    for m in service.produces:
        for ch in service.produces[m]:
            if isinstance(ch, set):
                for ch1 in ch:
                    if ch1.msg_type.fqn != m.fqn:
                        raise Exception(f"{service.name}: Cannot produce message of type {m.fqn} to channel "
                                        f"{ch1.name}({ch1.msg_type.fqn})")
                continue
            if ch.msg_type.fqn != m.fqn:
                raise Exception(f"{service.name}: Cannot produce message of type {m.fqn} to channel "
                                f"{ch.name}({ch.msg_type.fqn})")


def check_fields(typedef: Union[TypeDef, Message]):
    fields = []
    for field in typedef.fields:
        field_name = first_upper(field.name)
        if field_name in fields:
            raise Exception(f"{typedef.name}: Duplicate field '{field.name}'.")
        fields.append(field_name)


def check_duplicates_in_api(service: ServiceDecl):
    typedefs, funcs, paths = [], [], []
    for typedef in service.api.typedefs:
        t_name = first_upper(typedef.name)
        if t_name in typedefs:
            raise Exception(f"{service.name}: Duplicate typedef {t_name}.")
        typedefs.append(t_name)
        check_fields(typedef)
        id_type = 'string'
        if "@create" in typedef.crud_dict:
            funcs.append(("Create"+t_name, ["Models."+t_name]))
            paths.append((t_name.lower(), HTTP_POST))
        if "@read" in typedef.crud_dict:
            funcs.append(("Read"+t_name, [id_type]))
            paths.append((t_name.lower() + "/{}", HTTP_GET))
        if "@update" in typedef.crud_dict:
            funcs.append(("Update"+t_name, [id_type, "Models."+t_name]))
            paths.append((t_name.lower() + "/{}", HTTP_PUT))
        if "@delete" in typedef.crud_dict:
            funcs.append(("Delete"+t_name, [id_type]))
            paths.append((t_name.lower() + "/{}", HTTP_DELETE))

    for func in service.api.functions:
        sign = (first_upper(func.name), [convert_type(p.type) for p in func.params])
        if sign in funcs:
            raise Exception(f"{service.name}: Duplicate function {sign}.")
        funcs.append(sign)
        path = (re.sub(r'{(.*?)}', '{}', str(func.rest_path.split("?")[0])), func.http_verb)
        if path in paths:
            raise Exception(f"{service.name}: Duplicate path {path}.")
        paths.append(path)

    internal = service.api.internal
    if not internal:
        return
    for func in internal.functions:
        for ann in func.msg_annotations:
            if isinstance(ann, ConsumerAnnotation):
                for sub in ann.subscriptions:
                    sign = (first_upper(func.name), [sub.channel.msg_type.fqn])
                    if sign in funcs:
                        raise Exception(f"{service.name}: Duplicate internal function {sign}.")
                    funcs.append(sign)
