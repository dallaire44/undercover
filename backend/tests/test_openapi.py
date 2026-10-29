from backend.main import app


def test_every_operation_follows_the_rules():
    paths = app.openapi()["paths"]
    for path, methods in paths.items():
        for method, operation in methods.items():
            where = f"{method} {path}"
            assert operation.get("operationId"), where
            assert operation.get("summary"), where
            assert "\n" not in operation.get("description", ""), where
            assert all(p["required"] for p in operation.get("parameters", [])), where
            body = operation.get("requestBody")
            if body:
                assert body["required"], where
                schema = body["content"]["application/json"]["schema"]
                name = schema["$ref"].split("/")[-1]
                model = app.openapi()["components"]["schemas"][name]
                assert set(model["properties"]) == set(model["required"]), where
