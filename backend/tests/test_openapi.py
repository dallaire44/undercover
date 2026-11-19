from fastapi import FastAPI

from backend.main import app


def assert_every_operation_follows_the_rules(api: FastAPI) -> None:
    """Every operation has an id, a one-line docstring and no optional inputs."""
    schema = api.openapi()
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            where = f"{method} {path}"
            assert operation.get("operationId"), where
            assert operation.get("summary"), where
            assert "\n" not in operation.get("description", ""), where
            assert all(p["required"] for p in operation.get("parameters", [])), where
            body = operation.get("requestBody")
            if body:
                assert body["required"], where
                ref = body["content"]["application/json"]["schema"]["$ref"]
                model = schema["components"]["schemas"][ref.split("/")[-1]]
                assert set(model["properties"]) == set(model["required"]), where


def test_every_operation_follows_the_rules():
    assert_every_operation_follows_the_rules(app)
