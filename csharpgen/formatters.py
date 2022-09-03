from silvera.const import HTTP_POST, HTTP_PUT
from silvera.core import Function


def first_upper(s: str):
    return s[0].upper() + s[1:]


def first_lower(s: str):
    return s[0].lower() + s[1:]


def first_upper_fqn(fqn: str):
    return '.'.join([first_upper(s) for s in fqn.split('.')])


def param_names_controller(func: Function):
    is_dto = len([p for p in func.params if not (p.url_placeholder or p.query_param)]) > 1
    return ", ".join(
        [p.name if p.url_placeholder or p.query_param or not is_dto
         else "request."+first_upper(p.name) for p in func.params])


def request_uri_and_body(func: Function, var_name=""):
    query_params, from_body = [], []
    path = str(func.rest_path.split("?")[0])
    post_or_put = func.http_verb == HTTP_POST or func.http_verb == HTTP_PUT
    for p in func.params:
        if p.query_param:
            query_params.append(p.name)
        elif p.url_placeholder:
            if var_name:
                path = path.replace(f"{{{p.name}}}", f"{{{var_name}.{first_upper(p.name)}}}")
        elif post_or_put:
            from_body.append(f"{var_name}.{first_upper(p.name)}" if var_name else p.name)
        else:
            query_params.append(p.name)
    query_params_str = '?'+'&'.join([f'{{{f"{var_name}.{first_upper(n)}" if var_name else n}.ToQueryString("{n}")}}'
                                     for n in query_params])
    from_body_str = from_body[0] if len(from_body) == 1 else f'new {{ {", ".join(from_body)} }}'
    request_uri = f'$"{path}{query_params_str if query_params else ""}"'
    return f'{request_uri}, {from_body_str}' if post_or_put else request_uri
