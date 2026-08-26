import { FormEvent, useEffect, useRef, useState } from "react";

interface Photo {
  id: string;
  original_filename: string;
  stored_filename: string;
  file_size: number;
  uploaded_at: string;
  width: number | null;
  height: number | null;
}

async function fetchPhotos(signal?: AbortSignal): Promise<Photo[]> {
  const response = await fetch("/photos", { signal });
  if (!response.ok) {
    throw new Error("Unable to load your photos.");
  }

  return (await response.json()) as Photo[];
}

function App() {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPhotos() {
      try {
        setPhotos(await fetchPhotos(controller.signal));
      } catch (requestError) {
        if (requestError instanceof DOMException && requestError.name === "AbortError") {
          return;
        }

        setError("Memora could not load your photos. Make sure the backend is running.");
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadPhotos();
    return () => controller.abort();
  }, []);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile || isUploading) {
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const uploadResponse = await fetch("/photos", {
        method: "POST",
        body: formData,
      });
      if (!uploadResponse.ok) {
        throw new Error("Upload failed.");
      }

      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      try {
        setPhotos(await fetchPhotos());
        setError(null);
      } catch {
        setUploadError(
          "Your photo was uploaded, but Memora could not refresh the gallery.",
        );
      }
    } catch {
      setUploadError(
        "Memora could not upload this photo. Choose a valid JPEG or PNG and try again.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <p className="eyebrow">Private by design</p>
        <h1>Memora</h1>
        <p className="subtitle">Your photos, stored and viewed locally.</p>
      </header>

      <form className="upload-form" onSubmit={handleUpload}>
        <label htmlFor="photo-upload">Choose one photo</label>
        <div className="upload-controls">
          <input
            ref={fileInputRef}
            id="photo-upload"
            type="file"
            accept=".jpg,.jpeg,.png,image/jpeg,image/png"
            disabled={isUploading}
            onChange={(event) => {
              setSelectedFile(event.target.files?.[0] ?? null);
              setUploadError(null);
            }}
          />
          <button type="submit" disabled={!selectedFile || isUploading}>
            {isUploading ? "Uploading…" : "Upload photo"}
          </button>
        </div>
        {uploadError && (
          <p className="upload-error" role="alert">
            {uploadError}
          </p>
        )}
      </form>

      {isLoading && <p className="status">Loading your photos…</p>}

      {!isLoading && error && (
        <p className="status status-error" role="alert">
          {error}
        </p>
      )}

      {!isLoading && !error && photos.length === 0 && (
        <p className="status">No photos yet.</p>
      )}

      {!isLoading && !error && photos.length > 0 && (
        <section className="photo-grid" aria-label="Photo gallery">
          {photos.map((photo) => (
            <figure className="photo-card" key={photo.id}>
              <img
                src={`/photos/${encodeURIComponent(photo.id)}/thumbnail`}
                alt={photo.original_filename}
                loading="lazy"
                onError={(event) => {
                  event.currentTarget.onerror = null;
                  event.currentTarget.src = `/photos/${encodeURIComponent(photo.id)}/file`;
                }}
              />
              <figcaption title={photo.original_filename}>
                {photo.original_filename}
              </figcaption>
            </figure>
          ))}
        </section>
      )}
    </main>
  );
}

export default App;
