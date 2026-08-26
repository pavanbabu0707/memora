from pydantic import BaseModel, ConfigDict


class PhotoUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    original_filename: str
    stored_filename: str


class PhotoMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    original_filename: str
    stored_filename: str
    file_size: int
    uploaded_at: str
    width: int | None
    height: int | None
