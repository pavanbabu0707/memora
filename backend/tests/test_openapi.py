from app.main import app


def test_photo_response_models_describe_exact_public_fields() -> None:
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]

    upload_schema = schemas["PhotoUploadResponse"]
    assert set(upload_schema["properties"]) == {
        "id",
        "original_filename",
        "stored_filename",
    }
    assert upload_schema["additionalProperties"] is False

    metadata_schema = schemas["PhotoMetadataResponse"]
    assert set(metadata_schema["properties"]) == {
        "id",
        "original_filename",
        "stored_filename",
        "file_size",
        "uploaded_at",
        "width",
        "height",
    }
    assert metadata_schema["additionalProperties"] is False
    assert "stored_path" not in metadata_schema["properties"]


def test_photo_routes_reference_explicit_response_models() -> None:
    openapi = app.openapi()

    upload_response = openapi["paths"]["/photos"]["post"]["responses"]["200"]
    assert upload_response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PhotoUploadResponse"
    }

    list_response = openapi["paths"]["/photos"]["get"]["responses"]["200"]
    list_schema = list_response["content"]["application/json"]["schema"]
    assert list_schema["type"] == "array"
    assert list_schema["items"] == {
        "$ref": "#/components/schemas/PhotoMetadataResponse"
    }
