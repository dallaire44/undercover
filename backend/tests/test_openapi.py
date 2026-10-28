from backend.main import app


def test_every_operation_follows_the_rules():
    """Each operation has an id, a one-line docstring and only required inputs."""
    for path, methods in app.openapi()["paths"].items():
        for method, op in methods.items():
            where = f"{method.upper()} {path}"
            assert op.get("operationId"), where
            assert op.get("summary"), where
            description = op.get("description", "")
            assert description
            assert "\n" not in description, where
            for param in op.get("parameters", []):
                assert param["required"], where
            assert_body_required(app.openapi(), op, where)


def assert_body_required(spec, op, where):
    body = op.get("requestBody")
    if not body:
        return
    ref = body["content"]["application/json"]["schema"]["$ref"]
    schema = spec["components"]["schemas"][ref.split("/")[-1]]
    assert set(schema["properties"]) <= set(schema.get("required", [])), where
